#!/usr/bin/env python3
"""Tab Nap end-to-end harness (Chrome 157, CDP over --remote-debugging-pipe, Extensions.loadUnpacked).
Run from anywhere:  python3 tests/e2e/harness.py [--headed]      ONLY=2,5 python3 tests/e2e/harness.py   (select groups)
Test tabs are real https pages (example.com/.org/.net, duckduckgo, wikipedia, bing) created with chrome.tabs.create.
The minute check is run on demand through the worker's debug hook (globalThis.__tabNapTest, reachable only through CDP
attached to the worker). Real context-menu UI and the real permission prompt cannot be driven headless: the menu
handlers are invoked directly and chrome.permissions.request is stubbed on a build that already holds <all_urls>."""
import fcntl, re, os, sys, json, time, base64, shutil, subprocess, threading, queue, traceback, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.dirname(os.path.dirname(HERE))
SHOTS = os.path.join(HERE, "shots"); os.makedirs(SHOTS, exist_ok=True)
WORK = tempfile.mkdtemp(prefix="tn-e2e-")            # throwaway: profile + patched extension copies
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HEADED = "--headed" in sys.argv
ONLY = [int(x) for x in os.environ.get("ONLY", "").split(",") if x.strip()]
THANKS = "<!doctype html><html><head><title>Thanks</title></head><body><h1>Thank you</h1></body></html>"
GOOD_SESSION = "cs_test_" + "aB3dE5fG7hJ9kL1mN3pQ5rS7"
HOLD_HOST = "https://hold.tabnap-test.example/"

def fixture(url):
    if url.startswith("https://overcrasher.github.io/"): return THANKS
    return None

class CDP:
    def __init__(self):
        r1, w1 = os.pipe(); r2, w2 = os.pipe()
        r1, w1, r2, w2 = [fcntl.fcntl(f, fcntl.F_DUPFD_CLOEXEC, 20) for f in (r1, w1, r2, w2)]
        def pre():
            os.dup2(r1, 3, inheritable=True); os.dup2(w2, 4, inheritable=True)
        self.profile = tempfile.mkdtemp(prefix="tn-profile-")
        args = [CHROME, "--enable-unsafe-extension-debugging", "--remote-debugging-pipe", "--user-data-dir=" + self.profile,
                "--no-first-run", "--no-default-browser-check", "--window-size=1100,900", "--autoplay-policy=no-user-gesture-required", "about:blank"]
        if not HEADED: args.insert(1, "--headless=new")
        self.proc = subprocess.Popen(args, preexec_fn=pre, close_fds=False, stdout=subprocess.DEVNULL, stderr=open(os.path.join(WORK, "chrome.err"), "w"))
        os.close(r1); os.close(w2)
        self.wfd, self.rfd = w1, r2
        self.id = 0; self.lock = threading.Lock(); self.waiters = {}
        self.events = queue.Queue(); self.listeners = []
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._dispatch, daemon=True).start()
    def _read(self):
        buf = b""
        while True:
            try: d = os.read(self.rfd, 65536)
            except OSError: return
            if not d: return
            buf += d
            while b"\0" in buf:
                m, buf = buf.split(b"\0", 1)
                try: msg = json.loads(m)
                except Exception: continue
                if "id" in msg:
                    w = self.waiters.pop(msg["id"], None)
                    if w: w[1].update(msg); w[0].set()
                else: self.events.put(msg)
    def _dispatch(self):
        while True:
            e = self.events.get()
            for l in self.listeners:
                try: l(e)
                except Exception: traceback.print_exc()
    def send(self, method, params=None, sid=None, timeout=30):
        with self.lock:
            self.id += 1; i = self.id
        ev_ = threading.Event(); res = {}
        self.waiters[i] = (ev_, res)
        m = {"id": i, "method": method, "params": params or {}}
        if sid: m["sessionId"] = sid
        os.write(self.wfd, json.dumps(m).encode() + b"\0")
        if not ev_.wait(timeout): raise TimeoutError(method)
        if "error" in res: raise RuntimeError(method + ": " + json.dumps(res["error"]))
        return res.get("result", {})
    def close(self):
        try: self.proc.kill()
        except Exception: pass
        subprocess.run(["pkill", "-f", "user-data-dir=" + self.profile], capture_output=True)
        time.sleep(0.5); shutil.rmtree(self.profile, ignore_errors=True)

cdp = None; EXT_ID = None
LOGS = []; TABS_SEEN = []; labels = {}; ISO = {}
sw = {"sid": None, "tid": None}
RESULTS = {}; CUR = [0]

def check(name, ok, ev_=""):
    RESULTS.setdefault(CUR[0], []).append((name, bool(ok), str(ev_)))
    print(("  PASS " if ok else "  FAIL ") + name + ("  | " + str(ev_)[:300] if ev_ != "" else ""), flush=True)

def on_event(e):
    m, p, sid = e.get("method"), e.get("params", {}), e.get("sessionId")
    lab = labels.get(sid, sid)
    if m == "Fetch.requestPaused":
        url = p["request"]["url"]; body = fixture(url)
        try:
            if url.startswith(HOLD_HOST): pass          # held forever: the tab stays in "loading"
            elif body is not None:
                cdp.send("Fetch.fulfillRequest", {"requestId": p["requestId"], "responseCode": 200,
                    "responseHeaders": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}],
                    "body": base64.b64encode(body.encode()).decode()}, sid)
            else:
                cdp.send("Fetch.continueRequest", {"requestId": p["requestId"]}, sid)
        except Exception as ex: print("fetch err", ex)
    elif m in ("Target.targetCreated", "Target.targetInfoChanged"):
        TABS_SEEN.append(p["targetInfo"].get("url", ""))
    elif m == "Runtime.executionContextCreated":
        c = p["context"]
        if c.get("auxData", {}).get("type") == "isolated":
            ISO.setdefault(sid, []).append((c["id"], c.get("origin", ""), c.get("name", "")))
    elif m == "Runtime.executionContextsCleared": ISO[sid] = []
    elif m == "Runtime.exceptionThrown":
        d = p["exceptionDetails"]
        LOGS.append((lab, "exception", d.get("text", "") + " " + json.dumps(d.get("exception", {}).get("description", ""))[:300] + " " + d.get("url", "")))
    elif m == "Runtime.consoleAPICalled" and p["type"] in ("error", "warning", "assert"):
        LOGS.append((lab, "console." + p["type"], " ".join(str(a.get("value", a.get("description", ""))) for a in p["args"])))
    elif m == "Log.entryAdded" and p["entry"]["level"] in ("error", "warning"):
        LOGS.append((lab, "log." + p["entry"]["level"], p["entry"]["text"] + " " + p["entry"].get("url", "")))
    elif m == "Target.attachedToTarget":
        ti = p["targetInfo"]
        if ti["type"] == "service_worker":
            s = p["sessionId"]; labels[s] = "SW"; sw["sid"] = s; sw["tid"] = ti["targetId"]
            for meth in ("Runtime.enable", "Log.enable"):
                try: cdp.send(meth, {}, s)
                except Exception as ex: print("sw enable", ex)
            try: cdp.send("Runtime.runIfWaitingForDebugger", {}, s)
            except Exception: pass

def start(ext_path):
    global cdp, EXT_ID
    cdp = CDP(); cdp.listeners.append(on_event)
    time.sleep(2)
    cdp.send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True, "filter": [{"type": "service_worker"}, {"exclude": True}]})
    cdp.send("Target.setDiscoverTargets", {"discover": True})
    r = cdp.send("Extensions.loadUnpacked", {"path": ext_path}); EXT_ID = r["id"]
    return r

def get_sw():
    for _ in range(30):
        ts = cdp.send("Target.getTargets")["targetInfos"]
        s = [t for t in ts if t["type"] == "service_worker" and EXT_ID in t["url"]]
        if s:
            if sw["tid"] != s[0]["targetId"] or not sw["sid"]:
                sid = cdp.send("Target.attachToTarget", {"targetId": s[0]["targetId"], "flatten": True})["sessionId"]
                labels[sid] = "SW"; sw["sid"] = sid; sw["tid"] = s[0]["targetId"]
                cdp.send("Runtime.enable", {}, sid); cdp.send("Log.enable", {}, sid)
            return sw["sid"]
        time.sleep(0.5)
    raise RuntimeError("no service worker target")

def ev(sid, expr, await_=True, **kw):
    p = {"expression": expr, "awaitPromise": await_, "returnByValue": True}; p.update(kw)
    r = cdp.send("Runtime.evaluate", p, sid, timeout=60)
    if "exceptionDetails" in r: raise RuntimeError("eval: " + json.dumps(r["exceptionDetails"])[:400])
    return r["result"].get("value")
def sw_eval(expr):
    try: return ev(get_sw(), expr)
    except Exception as e:
        if "Session" in str(e) or "not found" in str(e) or "closed" in str(e):
            sw["sid"] = None; return ev(get_sw(), expr)
        raise
def px(sid, expr): return ev(sid, expr, False)

# ---------------- helpers ----------------
def storage(): return sw_eval("chrome.storage.local.get(null)")
def session(): return sw_eval("chrome.storage.session.get(null)")
DEFAULT_SETTINGS = {"thresholdMin": 30, "protectPinned": True, "avgMb": 150, "whitelist": [], "protectTyping": False}
def reset(settings=None, extra=None):
    sw_eval("chrome.storage.local.clear()"); sw_eval("chrome.storage.session.clear()")
    d = {"settings": dict(DEFAULT_SETTINGS)}
    if settings: d["settings"].update(settings)
    if extra: d.update(extra)
    sw_eval("chrome.storage.local.set(%s)" % json.dumps(d)); time.sleep(0.3)
def set_settings(**kw):
    sw_eval("(async()=>{const {settings}=await chrome.storage.local.get('settings');await chrome.storage.local.set({settings:Object.assign({},settings,%s)})})()" % json.dumps(kw))
def targets(): return cdp.send("Target.getTargets")["targetInfos"]
def close_tab(tid):
    try: cdp.send("Target.closeTarget", {"targetId": tid})
    except Exception: pass
    time.sleep(0.6)
def wait_for(fn, t=8):
    end = time.time() + t
    while time.time() < end:
        try:
            v = fn()
            if v: return v
        except Exception: pass
        time.sleep(0.3)
    return False
def shot(sid, name, clip=None, full=False):
    p = {"format": "png"}
    if clip: p["clip"] = dict(clip, scale=1)
    if full: p["captureBeyondViewport"] = True
    d = cdp.send("Page.captureScreenshot", p, sid)["data"]
    path = os.path.join(SHOTS, name + ".png"); open(path, "wb").write(base64.b64decode(d)); return path
def tabs(): return sw_eval("chrome.tabs.query({})")
def tab(tid): return sw_eval("chrome.tabs.get(%d).catch(()=>null)" % tid)
def mk(url, active=False, pinned=False, wait=True):
    t = sw_eval("chrome.tabs.create({url:%s,active:%s,pinned:%s})" % (json.dumps(url), json.dumps(active), json.dumps(pinned)))
    if wait: wait_for(lambda: (tab(t["id"]) or {}).get("status") == "complete", 25)
    return t["id"]
def rm(*ids):
    for i in ids: sw_eval("chrome.tabs.remove(%d).catch(()=>0)" % i)
    time.sleep(0.4)
def run_check(minutes_ahead=31): return sw_eval("globalThis.__tabNapTest.runCheck(Date.now()+%d*60000)" % minutes_ahead)
def discarded(tid): return bool((tab(tid) or {}).get("discarded"))
def activate(tid):
    t = sw_eval("chrome.tabs.update(%d,{active:true})" % tid)
    if t: sw_eval("chrome.windows.update(%d,{focused:true}).catch(()=>0)" % t["windowId"])
    time.sleep(0.5)
def by_url(sub): return [t for t in tabs() if sub in (t.get("url") or "") or sub in (t.get("pendingUrl") or "")]
def one(sub):
    r = by_url(sub); return r[0] if r else None
def clean():
    """Close every tab except one blank tab and keep it active."""
    keep = None
    for t in tabs():
        if keep is None and t["url"] in ("about:blank", "chrome://newtab/"): keep = t["id"]
    if keep is None: keep = sw_eval("chrome.tabs.create({url:'about:blank',active:true})")["id"]
    for w in sw_eval("chrome.windows.getAll()"): pass
    for t in tabs():
        if t["id"] != keep: sw_eval("chrome.tabs.remove(%d).catch(()=>0)" % t["id"])
    time.sleep(0.8); sw_eval("chrome.tabs.update(%d,{active:true})" % keep); return keep
def new_page(url, fetch=True, w=1000, h=800):
    tid = cdp.send("Target.createTarget", {"url": "about:blank"})["targetId"]
    sid = cdp.send("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
    labels[sid] = "page:" + url[:60]
    for m in ("Runtime.enable", "Log.enable", "Page.enable", "DOM.enable"): cdp.send(m, {}, sid)
    if fetch: cdp.send("Fetch.enable", {"patterns": [{"urlPattern": "https://overcrasher.github.io/*"}, {"urlPattern": HOLD_HOST + "*"}]}, sid)
    cdp.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False}, sid)
    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]}, sid)
    try: cdp.send("Emulation.setFocusEmulationEnabled", {"enabled": True}, sid)
    except Exception: pass
    if url != "about:blank":
        try: cdp.send("Page.navigate", {"url": url}, sid, timeout=6 if url.startswith(HOLD_HOST) else 30)
        except TimeoutError: pass
        time.sleep(2.0)
    return tid, sid
def ext_page(name, w=420, h=760): return new_page("chrome-extension://%s/%s" % (EXT_ID, name), fetch=False, w=w, h=h)
def attach_url(sub, wait=10):
    def f():
        for t in targets():
            if t["type"] == "page" and sub in t["url"]: return t["targetId"]
    tid = wait_for(f, wait)
    sid = cdp.send("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
    labels[sid] = "page:" + sub
    for m in ("Runtime.enable", "Page.enable", "DOM.enable"): cdp.send(m, {}, sid)
    return tid, sid
def iso_ctx(sid):
    for _ in range(24):
        c = [x for x in ISO.get(sid, []) if EXT_ID in x[1]]
        if c: return c[-1][0]
        time.sleep(0.25)
    return None
def cs_eval(sid, expr):
    r = cdp.send("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True, "contextId": iso_ctx(sid)}, sid, timeout=60)
    if "exceptionDetails" in r: raise RuntimeError("cs eval: " + json.dumps(r["exceptionDetails"])[:300])
    return r["result"].get("value")
def cs_send(sid, msg): return cs_eval(sid, "chrome.runtime.sendMessage(%s).then(r=>r,e=>({threw:String(e)}))" % json.dumps(msg))

def copy_ext(name, config_links=None, host_perm=False):
    d = os.path.join(WORK, name); shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(EXT, d, ignore=shutil.ignore_patterns(".git", "tests", "docs", "tools", "store", "dist"))
    if config_links is not None:
        p = os.path.join(d, "config.js"); c = open(p).read()
        c2 = re.sub(r"export const DONATE_LINKS = \{[^}]*\};", "export const DONATE_LINKS = %s;" % config_links, c)
        assert c2 != c; open(p, "w").write(c2)
    if host_perm:
        p = os.path.join(d, "manifest.json"); m = json.load(open(p)); m["host_permissions"] = ["<all_urls>"]
        json.dump(m, open(p, "w"), indent=2)
    return d

# ================= group 1: install, manifest, welcome =================
def g1():
    m = sw_eval("chrome.runtime.getManifest()")
    check("permissions exactly as shipped", sorted(m["permissions"]) == sorted(["tabs", "storage", "alarms", "contextMenus", "scripting", "favicon"]), m["permissions"])
    check("optional_host_permissions is <all_urls>", m.get("optional_host_permissions") == ["<all_urls>"])
    check("no required host permissions", "host_permissions" not in m)
    check("only content script is the thanks page", [c["matches"] for c in m["content_scripts"]] == [["https://overcrasher.github.io/tab-nap/thanks.html?session_id=*"]])
    check("version 1.0.0, short_name Tab Nap, bare action title", m["version"] == "1.0.0" and m["short_name"] == "Tab Nap" and m["action"]["default_title"] == "Tab Nap")
    check("localized store name resolved", m["name"] == "Tab Nap – Tab Suspender & Memory Saver", m["name"])
    check("strict CSP", "script-src 'self'" in m["content_security_policy"]["extension_pages"] and "unsafe" not in m["content_security_policy"]["extension_pages"])
    welcomes = [u for u in TABS_SEEN if u.endswith("/welcome.html")]
    check("welcome page opened on install", len(welcomes) >= 1, welcomes[:1])
    al = sw_eval("chrome.alarms.getAll()")
    check("minute alarm registered", any(a["name"] == "tabnap-check" and a["periodInMinutes"] == 1 for a in al), al)
    for mid in ("nap-now", "never-site", "nap-others"):
        err = sw_eval("new Promise(r=>{chrome.contextMenus.create({id:%s,title:'x'},()=>r(chrome.runtime.lastError&&chrome.runtime.lastError.message))})" % json.dumps(mid))
        check("context menu item exists: " + mid, err and "duplicate" in err.lower(), err)
    reset()
    tid, sid = ext_page("welcome.html", w=900, h=900)
    try:
        time.sleep(1)
        txt = px(sid, "document.body.innerText")
        check("welcome: 3 steps + protect button + open settings", all(x in txt for x in ["Leave a few tabs idle", "Nap this tab now", "Protect tabs with unsaved typing", "Open settings"]), "")
        check("welcome: name shown", "Welcome to Tab Nap" in txt)
        shot(sid, "welcome")
    finally: close_tab(tid)

# ================= group 2: NEVER rules =================
def g2():
    reset(); keep = clean()
    A = mk("https://example.com/?nap=idle"); P = mk("https://example.com/?nap=pinned", pinned=True)
    mk("https://example.net/?nap=whitelisted"); D = mk("https://example.com/?nap=dirty"); F = mk("https://example.org/?nap=nodiscard")
    S = mk("https://example.org/?nap=sound"); PRE = mk("https://example.org/?nap=pre")
    sw_eval("chrome.tabs.update(%d,{autoDiscardable:false})" % F)
    set_settings(whitelist=["example.net"])
    sw_eval("chrome.storage.session.set({dirty:{%d:true}})" % D)
    sw_eval("chrome.tabs.discard(%d)" % PRE)
    mk("chrome://version"); mk("chrome-extension://%s/options.html" % EXT_ID); mk("about:blank")
    audible = False
    try:
        _, ssid = attach_url("nap=sound")
        ev(ssid, "(()=>{const c=new AudioContext();const o=c.createOscillator();const g=c.createGain();g.gain.value=0.2;o.connect(g);g.connect(c.destination);o.start();return c.state})()", True, userGesture=True)
        audible = bool(wait_for(lambda: (one("nap=sound") or {}).get("audible"), 8))
    except Exception as e: print("audible setup", e)
    check("precondition: sound tab reports audible=true", audible)
    LT, LS = new_page(HOLD_HOST + "slow"); time.sleep(1.5)
    check("precondition: held tab is status loading", (one("hold.tabnap-test") or {}).get("status") == "loading", (one("hold.tabnap-test") or {}).get("status"))
    w2 = sw_eval("chrome.windows.create({url:'https://example.com/?w2=active'})"); time.sleep(2.5)
    W2B = sw_eval("chrome.tabs.create({windowId:%d,url:'https://example.org/?w2=idle',active:false})" % w2["id"])["id"]
    wait_for(lambda: (tab(W2B) or {}).get("status") == "complete", 20)
    sw_eval("chrome.tabs.update(%d,{active:true})" % keep); time.sleep(0.5)
    # the held tab (CDP-created) is active in window 1 unless we re-activate the blank tab
    sw_eval("chrome.windows.update(%d,{focused:true})" % [t for t in tabs() if t["id"] == keep][0]["windowId"]); time.sleep(0.3)
    act = [t["id"] for t in tabs() if t["active"]]
    check("precondition: exactly one active tab per window", len(act) == 2, act)
    r = run_check(31); time.sleep(1.0)
    st = one
    check("idle ordinary tab is napped", st("nap=idle")["discarded"])
    check("napped tab keeps its URL", st("nap=idle")["url"] == "https://example.com/?nap=idle")
    check("NEVER: pinned tab", not st("nap=pinned")["discarded"])
    check("NEVER: whitelisted domain", not st("nap=whitelisted")["discarded"])
    check("NEVER: tab with unsaved typing (dirty)", not st("nap=dirty")["discarded"])
    check("NEVER: autoDiscardable=false", not st("nap=nodiscard")["discarded"])
    check("NEVER: audible tab", audible and not st("nap=sound")["discarded"])
    check("NEVER: still-loading tab", not st("hold.tabnap-test")["discarded"])
    check("NEVER: chrome:// page", not st("chrome://version")["discarded"])
    check("NEVER: extension page", not st("options.html")["discarded"])
    check("NEVER: about:blank", all(not t["discarded"] for t in tabs() if t["url"] == "about:blank"))
    check("NEVER: active tab of window 1", not [t for t in tabs() if t["id"] == keep][0]["discarded"])
    check("NEVER: active tab of window 2", not st("w2=active")["discarded"])
    check("idle tab in window 2 is napped", st("w2=idle")["discarded"])
    sess = session()
    check("tab already discarded by someone else is not claimed", st("nap=pre")["discarded"] and st("nap=pre")["id"] not in sess.get("napped", []))
    napped_urls = sorted(t["url"] for t in tabs() if t["id"] in sess.get("napped", []))
    check("napped set = exactly the 2 tabs Tab Nap slept", napped_urls == ["https://example.com/?nap=idle", "https://example.org/?w2=idle"], napped_urls)
    s = storage()
    check("napCount = 2, tabHours = 2/60", s["napCount"] == 2 and abs(s["tabHours"] - 2 / 60) < 1e-9, (s["napCount"], s["tabHours"]))
    check("discard changes the tab id; napped set holds the NEW id", st("nap=idle")["id"] != A, (A, st("nap=idle")["id"]))
    set_settings(protectPinned=False); run_check(31); time.sleep(0.8)
    check("pinned tab napped once 'protect pinned' is off", st("nap=pinned")["discarded"])
    close_tab(LT); sw_eval("chrome.windows.remove(%d).catch(()=>0)" % w2["id"]); time.sleep(1)
    nid = st("nap=idle")["id"]; activate(nid)
    ok = wait_for(lambda: not (tab(nid) or {}).get("discarded") and (tab(nid) or {}).get("status") == "complete", 25)
    check("activating a napped tab wakes it", ok)
    check("woken tab URL intact", (tab(nid) or {}).get("url") == "https://example.com/?nap=idle", (tab(nid) or {}).get("url"))
    time.sleep(1.0)
    check("woken tab leaves the napped set", nid not in session().get("napped", []), session().get("napped"))
    victim = st("nap=pinned")["id"]; rm(victim); time.sleep(0.8)
    check("closed napped tab removed from set", victim not in session().get("napped", []))
    clean()

# ================= group 3: minute check, threshold, pause, alarm =================
def wake_all(keep):
    for t in tabs():
        if t["discarded"]: activate(t["id"])
    wait_for(lambda: not any(t["discarded"] for t in tabs()), 25); activate(keep); time.sleep(1.5)
def g3():
    reset(); keep = clean()
    a = mk("https://example.com/?t=a"); b = mk("https://example.org/?t=b")
    r = run_check(0)
    check("real time: fresh tabs not napped", not discarded(a) and not discarded(b) and r["napped"] == [], r)
    run_check(10); check("30 min threshold: +10 min not napped", not one("t=a")["discarded"])
    run_check(29); check("30 min threshold: +29 min not napped", not one("t=a")["discarded"])
    run_check(31); time.sleep(0.6); check("30 min threshold: +31 min napped", one("t=a")["discarded"] and one("t=b")["discarded"])
    wake_all(keep)
    set_settings(thresholdMin=5)
    run_check(4); check("5 min threshold: +4 min not napped", not one("t=a")["discarded"])
    run_check(6); time.sleep(0.6); check("5 min threshold: +6 min napped", one("t=a")["discarded"])
    wake_all(keep); set_settings(thresholdMin=120)
    run_check(100); check("120 min threshold: +100 min not napped", not one("t=a")["discarded"])
    run_check(121); time.sleep(0.6); check("120 min threshold: +121 min napped", one("t=a")["discarded"])
    wake_all(keep); set_settings(thresholdMin=30)
    sw_eval("chrome.storage.local.set({pausedUntil:-1})"); run_check(31); time.sleep(0.5)
    check("paused until turned back on: nothing napped", not one("t=a")["discarded"])
    sw_eval("chrome.storage.local.set({pausedUntil:Date.now()+3600000})"); run_check(31); time.sleep(0.5)
    check("paused for 1 hour: nothing napped", not one("t=a")["discarded"])
    sw_eval("chrome.storage.local.set({pausedUntil:Date.now()+10000})"); run_check(31); time.sleep(0.5)
    check("pause that has expired: naps again and clears pausedUntil", one("t=a")["discarded"] and storage().get("pausedUntil") == 0, storage().get("pausedUntil"))
    n = len(session()["napped"]); h0 = storage()["tabHours"]
    check("precondition: 2 tabs napped", n == 2, n)
    ok = wait_for(lambda: storage()["tabHours"] > h0 + 1e-9, 90)
    h1 = storage()["tabHours"]
    check("real minute alarm fired and added tab-hours", ok, (h0, h1))
    check("alarm increment = napped tabs / 60 (per alarm)", ok and (h1 - h0) >= n / 60 - 1e-9 and (h1 - h0) < 2 * n / 60 + 1e-9, (h1 - h0, n / 60))
    wake_all(keep)
    r = run_check(0)
    check("after waking everything, nothing counts as napping", r["nappedTotal"] == 0, r)
    clean()

# ================= group 4: context menu handlers =================
def g4():
    reset(); keep = clean()
    a = mk("https://example.com/?m=a", active=True)
    mk("https://example.org/?m=b"); c = mk("https://example.net/?m=c"); p = mk("https://example.com/?m=pin", pinned=True)
    sw_eval("chrome.tabs.update(%d,{active:true})" % a); time.sleep(0.5)
    H = lambda mid, t: sw_eval("globalThis.__tabNapTest.handleMenu(%s, %s)" % (json.dumps(mid), json.dumps(t)))
    ok = H("nap-now", tab(a)); time.sleep(1.0)
    check("Nap this tab now: returns true", ok is True, ok)
    check("Nap this tab now: clicked tab asleep, URL kept", one("m=a")["discarded"] and one("m=a")["url"] == "https://example.com/?m=a")
    act = [t for t in tabs() if t["active"]]
    check("Nap this tab now: switched to another awake tab first", act and all("m=a" not in t["url"] and not t["discarded"] for t in act), [t["url"] for t in act])
    check("Nap this tab now: counted", storage()["napCount"] == 1 and one("m=a")["id"] in session()["napped"])
    ok = H("nap-now", tab(p)); check("Nap this tab now: refused for a pinned tab", ok is False and not one("m=pin")["discarded"], ok)
    w = sw_eval("chrome.windows.create({url:'https://example.com/?m=solo'})"); time.sleep(2.5)
    ok = H("nap-now", one("m=solo")); check("Nap this tab now: refused when no other awake tab in window", ok is False and not one("m=solo")["discarded"], ok)
    sw_eval("chrome.windows.remove(%d).catch(()=>0)" % w["id"])
    tc = tab(c); ok = H("never-site", tc)
    check("Never nap this site: domain whitelisted", ok is True and "example.net" in storage()["settings"]["whitelist"], storage()["settings"]["whitelist"])
    ok = H("never-site", {"id": 1, "url": "chrome://settings"})
    check("Never nap this site: refused on chrome:// page", ok is False and len(storage()["settings"]["whitelist"]) == 1)
    H("never-site", tc); check("Never nap this site: no duplicates", storage()["settings"]["whitelist"].count("example.net") == 1)
    mk("https://example.org/?m=d"); e = mk("https://example.com/?m=e")
    sw_eval("chrome.storage.session.get('dirty').then(d=>chrome.storage.session.set({dirty:Object.assign(d.dirty||{},{%d:true})}))" % e)
    focus = mk("https://example.com/?m=focus", active=True)
    H("nap-others", tab(focus)); time.sleep(1.5)
    check("Nap all other tabs: plain tabs napped (even though fresh)", one("m=b")["discarded"] and one("m=d")["discarded"])
    check("Nap all other tabs: clicked/active tab stays awake", not one("m=focus")["discarded"])
    check("Nap all other tabs: pinned stays", not one("m=pin")["discarded"])
    check("Nap all other tabs: whitelisted stays", not one("m=c")["discarded"])
    check("Nap all other tabs: tab with unsaved typing stays", not one("m=e")["discarded"])
    check("Nap all other tabs: URLs preserved", one("m=b")["url"] == "https://example.org/?m=b")
    check("unknown menu id ignored", H("nope", tab(focus)) is False)
    check("Object.prototype key ('constructor') ignored", H("constructor", tab(focus)) is False)
    clean()

# ================= group 5: popup =================
def nap_five():
    urls = ["https://example.com/?p=%d" % i for i in range(3)] + ["https://example.org/?p=3", "https://example.net/?p=4"]
    for u in urls: mk(u)
    run_check(31); time.sleep(1.0); return urls
def popup_state(sid):
    return json.loads(px(sid, """JSON.stringify({count:document.getElementById('count').textContent,memory:document.getElementById('memory').textContent,
      hours:document.getElementById('hours').textContent,naps:document.getElementById('naps').textContent,
      items:[...document.querySelectorAll('#list button.tab')].map(b=>({title:b.querySelector('.title').textContent,host:b.querySelector('.host').textContent,
        src:b.querySelector('img').src,loaded:b.querySelector('img').complete&&b.querySelector('img').naturalWidth>0})),
      emptyHidden:document.getElementById('empty').hidden,shareHidden:document.getElementById('share').hidden,
      banner:!document.getElementById('banner').hidden,rating:!document.getElementById('rating').hidden,
      supporter:!document.getElementById('supporter').hidden,pauseChecked:document.getElementById('pause').checked,pauseLeft:document.getElementById('pauseLeft').textContent})"""))
def open_popup():
    tid, sid = ext_page("popup.html"); time.sleep(1.2); return tid, sid
def page_url_of(item):
    from urllib.parse import urlparse, parse_qs
    return parse_qs(urlparse(item["src"]).query)["pageUrl"][0]
def g5():
    reset(settings={"avgMb": 450}); keep = clean()
    tid, sid = open_popup(); st = popup_state(sid)
    check("popup empty: 0 tabs, empty state, share hidden", st["count"] == "0 tabs" and st["emptyHidden"] is False and st["shareHidden"] is True and st["memory"] == "≈ 0 MB saved (estimated)", st)
    check("popup: no banner / rating / badge on fresh install", not st["banner"] and not st["rating"] and not st["supporter"])
    close_tab(tid)
    nap_five()
    tid, sid = open_popup(); time.sleep(0.5); st = popup_state(sid)
    check("popup: Currently napping 5 tabs", st["count"] == "5 tabs", st["count"])
    check("popup: memory 5 x 450 MB = 2.3 GB, labelled estimated", st["memory"] == "≈ 2.3 GB saved (estimated)", st["memory"])
    check("popup: naps counter 5", st["naps"] == "5", st["naps"])
    check("popup: lifetime tab-hours shown (5/60 -> 0.0)", st["hours"] == "0.0", st["hours"])
    check("popup: list has 5 entries with titles + hosts", len(st["items"]) == 5 and all(i["title"] and i["host"] for i in st["items"]), [i["title"] for i in st["items"]])
    check("popup: favicons use the _favicon URL (pageUrl + size=16)", all(i["src"].startswith("chrome-extension://%s/_favicon/?pageUrl=" % EXT_ID) and "size=16" in i["src"] for i in st["items"]), st["items"][0]["src"])
    check("popup: favicon images load", all(i["loaded"] for i in st["items"]), [i["loaded"] for i in st["items"]])
    check("popup: share visible after first nap", st["shareHidden"] is False)
    shot(sid, "popup-light")
    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark"}]}, sid); time.sleep(0.4)
    shot(sid, "popup-dark")
    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]}, sid)
    try: cdp.send("Browser.grantPermissions", {"origin": "chrome-extension://" + EXT_ID, "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
    except Exception as e: print("grant", e)
    px(sid, "document.getElementById('share').click()"); time.sleep(0.8)
    label = px(sid, "document.getElementById('share').textContent")
    try: clip = ev(sid, "navigator.clipboard.readText()")
    except Exception as e: clip = "ERR " + str(e)
    tail = "https://chromewebstore.google.com/detail/%s?utm_source=share" % EXT_ID
    check("share: button says Copied!", label == "Copied!", label)
    check("share: text format, ends with SHARE_URL", clip.startswith("Tab Nap has put my tabs to sleep for 0.0 tab-hours and saved ≈ 2.3 GB of memory right now. #TabNap ") and clip.endswith(tail), clip)
    px(sid, "document.getElementById('pause').click()"); time.sleep(0.5)
    check("pause toggle on -> pausedUntil -1", storage().get("pausedUntil") == -1, storage().get("pausedUntil"))
    check("pause message shown", "until you turn it back on" in px(sid, "document.getElementById('pauseLeft').textContent"))
    px(sid, "document.getElementById('pause').click()"); time.sleep(0.5)
    check("pause toggle off -> 0", storage().get("pausedUntil") == 0)
    px(sid, "document.getElementById('pause1h').click()"); time.sleep(0.5)
    left = storage().get("pausedUntil") - int(time.time() * 1000)
    check("pause 1 hour sets ~now+1h", 3500000 < left <= 3600000, left)
    check("pause 1h: switch on + 'min left' text", px(sid, "document.getElementById('pause').checked") is True and "min left" in px(sid, "document.getElementById('pauseLeft').textContent"))
    sw_eval("chrome.storage.local.set({pausedUntil:0})")
    first_url = page_url_of(st["items"][0])
    px(sid, "document.querySelector('#list button.tab').click()")
    woke = wait_for(lambda: any(t["active"] and not t["discarded"] and t["url"] == first_url for t in tabs()), 25)
    check("clicking a list entry activates + reloads that tab (URL intact)", woke, first_url)
    time.sleep(1); clean()

# ================= group 6: options page =================
def opt_state(sid):
    return json.loads(px(sid, """JSON.stringify({thr:[...document.querySelectorAll('input[name=threshold]')].find(r=>r.checked)?.value,
      pinned:document.getElementById('protectPinned').checked,audible:{checked:document.getElementById('audible').checked,disabled:document.getElementById('audible').disabled},
      avg:document.getElementById('avgMb').value,wl:[...document.querySelectorAll('#wl-list li')].map(l=>l.firstChild.textContent),err:document.getElementById('wl-err').textContent,
      typing:document.getElementById('protectTyping').checked,pause:document.getElementById('pause').checked,
      donateNote:document.getElementById('donate-note').textContent,donateBtns:[...document.querySelectorAll('#donate button, #donate a')].map(b=>b.textContent),
      sibs:[...document.querySelectorAll('#siblings a')].map(a=>a.textContent)})"""))
def g6():
    reset(); keep = clean()
    tid, sid = ext_page("options.html", w=900, h=1500); time.sleep(1.0)
    st = opt_state(sid)
    check("options defaults: 30 min, pinned on, 150 MB, empty list", st["thr"] == "30" and st["pinned"] and st["avg"] == "150" and st["wl"] == [], st)
    check("options: audible protection shown as always-on info", st["audible"] == {"checked": True, "disabled": True}, st["audible"])
    for v in ("60", "5"):
        px(sid, "document.querySelector('input[name=threshold][value=\"%s\"]').click()" % v); time.sleep(0.4)
        check("options: threshold %s saved" % v, storage()["settings"]["thresholdMin"] == int(v))
    px(sid, "document.getElementById('protectPinned').click()"); time.sleep(0.4)
    check("options: protect pinned off saved", storage()["settings"]["protectPinned"] is False)
    for typed, want in (("9999", 500), ("3", 50), ("220", 220)):
        px(sid, "(()=>{const e=document.getElementById('avgMb');e.value='%s';e.dispatchEvent(new Event('change'))})()" % typed); time.sleep(0.4)
        check("options: avg MB %s -> %d" % (typed, want), storage()["settings"]["avgMb"] == want and px(sid, "document.getElementById('avgMb').value") == str(want))
    def add(v):
        px(sid, "(()=>{document.getElementById('wl-input').value=%s;document.getElementById('wl-form').requestSubmit()})()" % json.dumps(v)); time.sleep(0.5)
    add("https://www.Example.com/some/path"); add("mail.test.org"); add("not a domain!"); add("example.com")
    st = opt_state(sid)
    check("whitelist: URL normalised, deduped, invalid rejected", st["wl"] == ["example.com", "mail.test.org"] and storage()["settings"]["whitelist"] == ["example.com", "mail.test.org"], (st["wl"], st["err"]))
    add("javascript:alert(1)")
    check("whitelist: javascript: rejected with message", "does not look like a domain" in opt_state(sid)["err"] and len(storage()["settings"]["whitelist"]) == 2)
    px(sid, "document.querySelector('#wl-list li button').click()"); time.sleep(0.5)
    check("whitelist: remove works", storage()["settings"]["whitelist"] == ["mail.test.org"], storage()["settings"]["whitelist"])
    sw_eval("(async()=>{const {settings}=await chrome.storage.local.get('settings');settings.whitelist.push('added.elsewhere.com');await chrome.storage.local.set({settings})})()")
    px(sid, "document.querySelector('input[name=threshold][value=\"15\"]').click()"); time.sleep(0.5)
    check("options save does not clobber a whitelist changed elsewhere", "added.elsewhere.com" in storage()["settings"]["whitelist"], storage()["settings"]["whitelist"])
    px(sid, "document.getElementById('pause').click()"); time.sleep(0.4)
    check("options: pause switch -> -1", storage().get("pausedUntil") == -1)
    px(sid, "document.getElementById('pause').click()"); time.sleep(0.4)
    check("options: pause off -> 0", storage().get("pausedUntil") == 0)
    px(sid, "window.__calls=[];chrome.permissions.request=async(a)=>{__calls.push(a);return false}")
    px(sid, "document.getElementById('protectTyping').click()"); time.sleep(0.8)
    st = opt_state(sid); calls = px(sid, "JSON.stringify(window.__calls)")
    check("typing protection: asks for optional <all_urls>", calls == '[{"origins":["<all_urls>"]}]', calls)
    check("typing protection: denied -> switch reverts, setting off", st["typing"] is False and storage()["settings"]["protectTyping"] is False)
    check("typing protection: denied -> no script registered", sw_eval("chrome.scripting.getRegisteredContentScripts()") == [])
    check("typing protection: explanation present", "never reads, stores or sends what you type" in px(sid, "document.body.innerText"))
    check("support: no links -> 'not configured', no buttons", "not configured" in st["donateNote"] and st["donateBtns"] == [], (st["donateNote"], st["donateBtns"]))
    check("support: siblings listed", st["sibs"] == ["Wait 24h", "Meeting Meter"], st["sibs"])
    px(sid, "document.getElementById('rate-link').click()"); time.sleep(1.5)
    px(sid, "document.querySelector('#siblings a').click()"); time.sleep(1.5)
    seen = [u for u in TABS_SEEN if "chromewebstore.google.com" in u]
    check("rate link opens reviews URL derived from the extension id", any(u.startswith("https://chromewebstore.google.com/detail/%s/reviews" % EXT_ID) for u in seen), seen[-3:])
    check("sibling link opens its store page", any("detail/wait-24h/pkgdjohoemjkejcbfbkfobbbjcpdabme" in u for u in seen), seen[-3:])
    shot(sid, "options-light", full=True)
    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark"}]}, sid); time.sleep(0.4)
    shot(sid, "options-dark", full=True)
    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]}, sid)
    cdp.send("Page.reload", {}, sid); time.sleep(1.5); st = opt_state(sid)
    check("options persist across reload", st["thr"] == "15" and st["pinned"] is False and st["avg"] == "220" and "mail.test.org" in st["wl"], st)
    cdp.send("Emulation.setDeviceMetricsOverride", {"width": 400, "height": 900, "deviceScaleFactor": 1, "mobile": False}, sid); time.sleep(0.4)
    check("options: no horizontal overflow at 400px", px(sid, "document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"))
    close_tab(tid)
    sw_eval("chrome.storage.local.set({settings:{thresholdMin:'x',whitelist:[1,{},'EVIL<script>'],avgMb:-5,protectTyping:'yes'},tabHours:'NaN',napCount:-1,pausedUntil:'no'})")
    tid, sid = open_popup(); st = popup_state(sid)
    check("junk storage: popup renders with defaults", st["count"] == "0 tabs" and st["naps"] == "0", st)
    r = run_check(31); check("junk storage: minute check still runs", "napped" in r, r)
    close_tab(tid); reset(); clean()

# ================= group 7: supporter flag, no-links build, rating =================
def g7():
    reset(); clean()
    tid, sid = new_page("https://overcrasher.github.io/tab-nap/thanks.html?session_id=" + GOOD_SESSION); time.sleep(2.0)
    check("thanks page: valid session id sets supporter", storage().get("supporter") is True, storage().get("supporter"))
    close_tab(tid); reset()
    for label, q in (("bad shape", "session_id=cs_test_short"), ("wrong prefix", "session_id=xx_live_" + "a" * 24), ("empty", "session_id=")):
        tid, sid = new_page("https://overcrasher.github.io/tab-nap/thanks.html?" + q); time.sleep(1.5)
        check("thanks page: %s session id rejected" % label, not storage().get("supporter")); close_tab(tid)
    tid, sid = new_page("https://overcrasher.github.io/tab-nap/thanks.html"); time.sleep(1.5)
    check("thanks page without session_id: no flag", not storage().get("supporter")); close_tab(tid)
    tid, sid = new_page("https://overcrasher.github.io/wait-24h/thanks.html?session_id=" + GOOD_SESSION); time.sleep(1.5)
    check("sibling's thanks page does not set the flag", not storage().get("supporter")); close_tab(tid)
    reset(extra={"tabHours": 100.5, "napCount": 60}); tid, sid = open_popup(); st = popup_state(sid)
    check("no links configured: banner never shown at 100 tab-hours", not st["banner"], st)
    check("no links configured: milestone not burned", not (storage().get("donation") or {}).get("asked"), storage().get("donation"))
    check("rating card shown after 60 naps", st["rating"] is True)
    check("rating stored as shown", storage().get("rating", {}).get("shown") is True)
    close_tab(tid); tid, sid = open_popup()
    check("rating card shown only once", not popup_state(sid)["rating"]); close_tab(tid)
    reset(extra={"tabHours": 5, "napCount": 49}); tid, sid = open_popup()
    check("rating threshold: 49 naps -> not shown", not popup_state(sid)["rating"]); close_tab(tid)
    reset(extra={"tabHours": 5, "napCount": 50}); tid, sid = open_popup()
    check("rating threshold: 50 naps -> shown", popup_state(sid)["rating"])
    px(sid, "document.getElementById('rating-rate').click()"); time.sleep(1.5)
    check("Rate it opens the reviews URL", any(u.startswith("https://chromewebstore.google.com/detail/%s/reviews" % EXT_ID) for u in TABS_SEEN))
    check("rating card hides after click", not popup_state(sid)["rating"]); close_tab(tid)
    reset(extra={"supporter": True}); tid, sid = open_popup()
    check("supporter badge shown", popup_state(sid)["supporter"]); close_tab(tid); clean()

# ================= group 8: donation banner (copy with fake Stripe links) =================
LINKS = '{ small: "https://buy.stripe.com/eur-3", medium: "https://donate.stripe.com/eur-5", large: "https://buy.stripe.com/eur-10", custom: "https://buy.stripe.com/eur-custom", monthly: "https://donate.stripe.com/eur-monthly" }'
def banner_info(sid):
    return json.loads(px(sid, """JSON.stringify({hidden:document.getElementById('banner').hidden,text:document.getElementById('banner-text').textContent,
      btns:[...document.querySelectorAll('#banner-buttons button, #banner-buttons a')].map(b=>({t:b.textContent,c:b.className})),note:document.getElementById('banner-note').textContent,
      rating:!document.getElementById('rating').hidden})"""))
def g8():
    DAY = 86400000; now = int(time.time() * 1000)
    reset(extra={"tabHours": 99}); clean()
    tid, sid = open_popup(); check("banner: 99 tab-hours -> none", banner_info(sid)["hidden"]); close_tab(tid)
    reset(extra={"tabHours": 100}); tid, sid = open_popup(); b = banner_info(sid)
    check("banner: shown at 100 tab-hours", not b["hidden"], b)
    check("banner: copy includes the milestone number", "napped your tabs for 100 tab-hours." in b["text"] and "a coffee keeps it going" in b["text"], b["text"])
    check("banner: EUR 3 / 5 / 10 + pick your own", [x["t"] for x in b["btns"][:4]] == ["€3", "€5", "€10", "Pick your own amount"], b["btns"])
    check("banner: EUR 5 emphasized", "emphasized" in b["btns"][1]["c"])
    check("banner: monthly is a small text link", b["btns"][4] == {"t": "Or support monthly (€2/month)", "c": "monthly"}, b["btns"])
    d = storage()["donation"]; check("banner: ask persisted (asked=[100], lastAskAt)", d["asked"] == [100] and d["lastAskAt"] > 0, d)
    shot(sid, "popup-banner")
    def clickb(i):
        px(sid, "[...document.querySelectorAll('#banner-buttons button, #banner-buttons a')][%d].click()" % i); time.sleep(0.8)
    for i, want in ((0, "https://buy.stripe.com/eur-3"), (1, "https://donate.stripe.com/eur-5"), (2, "https://buy.stripe.com/eur-10")):
        clickb(i); check("banner: button %d opens %s" % (i, want), any(u.startswith(want) for u in TABS_SEEN))
    clickb(3); check("banner: custom opens link + quantity hint", any(u.startswith("https://buy.stripe.com/eur-custom") for u in TABS_SEEN) and "choose the quantity (€1 each)" in banner_info(sid)["note"], banner_info(sid)["note"])
    clickb(4); check("banner: monthly opens its link", any(u.startswith("https://donate.stripe.com/eur-monthly") for u in TABS_SEEN))
    close_tab(tid); tid, sid = open_popup(); check("banner: not shown again for the same milestone", banner_info(sid)["hidden"]); close_tab(tid)
    reset(extra={"tabHours": 1000, "donation": {"asked": [100], "lastAskAt": now - 5 * DAY, "dontAskAgain": False}}); tid, sid = open_popup()
    check("banner: 1000 reached but < 30 days since last ask -> none", banner_info(sid)["hidden"]); close_tab(tid)
    reset(extra={"tabHours": 1000, "donation": {"asked": [100], "lastAskAt": now - 31 * DAY, "dontAskAgain": False}}); tid, sid = open_popup(); b = banner_info(sid)
    check("banner: 1000 after 31 days -> shown with 1,000", not b["hidden"] and "1,000 tab-hours" in b["text"], b["text"])
    px(sid, "document.getElementById('banner-close').click()"); check("banner: dismiss hides it", banner_info(sid)["hidden"]); close_tab(tid)
    reset(extra={"tabHours": 10000, "donation": {"asked": [100, 1000], "lastAskAt": now - 40 * DAY, "dontAskAgain": False}}); tid, sid = open_popup(); b = banner_info(sid)
    check("banner: 10000 milestone copy", not b["hidden"] and "10,000 tab-hours" in b["text"], b["text"])
    px(sid, "document.getElementById('banner-never').click()"); time.sleep(0.5)
    check("Don't ask again stored", storage()["donation"]["dontAskAgain"] is True); close_tab(tid)
    sw_eval("chrome.storage.local.set({donation:{asked:[],lastAskAt:0,dontAskAgain:true},tabHours:20000})"); tid, sid = open_popup()
    check("Don't ask again is permanent", banner_info(sid)["hidden"]); close_tab(tid)
    reset(extra={"tabHours": 150, "supporter": True}); tid, sid = open_popup(); st = popup_state(sid)
    check("supporter: never asked, badge shown", not st["banner"] and st["supporter"]); close_tab(tid)
    reset(extra={"tabHours": 100, "napCount": 80}); tid, sid = open_popup(); b = banner_info(sid)
    check("banner wins over rating card in the same render", not b["hidden"] and not b["rating"] and not storage().get("rating", {}).get("shown"), (b["hidden"], b["rating"]))
    close_tab(tid); tid, sid = open_popup(); b = banner_info(sid)
    check("rating card appears on a later open once the banner is spent", b["hidden"] and b["rating"], b); close_tab(tid)
    reset(extra={"tabHours": 5}); tid, sid = ext_page("options.html", w=900, h=1500); time.sleep(1.0); st = opt_state(sid)
    check("options support: buttons + monthly link", st["donateBtns"] == ["€3", "€5", "€10", "Pick your own amount", "Or support monthly (€2/month)"], st["donateBtns"])
    shot(sid, "options-support", full=True); close_tab(tid)

# ================= group 9: evil donation links refused =================
def g9():
    reset(extra={"tabHours": 100}); clean()
    tid, sid = open_popup(); b = banner_info(sid)
    check("evil links: banner shown (links non-empty)", not b["hidden"], b)
    n0 = len(TABS_SEEN)
    px(sid, "document.querySelectorAll('#banner-buttons button, #banner-buttons a').forEach(b=>b.click())"); time.sleep(1.5)
    bad = [u for u in TABS_SEEN[n0:] if "evil.example" in u or "stripe" in u]
    check("evil / look-alike / http links open nothing", not bad, bad)
    check("no quantity hint after refused open", banner_info(sid)["note"] == ""); close_tab(tid)

# ================= typing protection (copy that already holds <all_urls>) =================
def type_text(sid, text):
    for ch in text:
        cdp.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": ch, "text": ch, "unmodifiedText": ch}, sid)
        cdp.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": ch}, sid)
    time.sleep(0.4)
def dirty_ids(): return [int(k) for k in (session().get("dirty") or {}).keys()]
def enable_protection():
    """Drives the real options-page switch. chrome.permissions.request can't be answered headless (the prompt hangs), so it is
    stubbed to 'granted' on a copy that already holds <all_urls>; everything after the grant is the real code path."""
    tid, sid = ext_page("options.html", w=900, h=900); time.sleep(1.0)
    px(sid, "chrome.permissions.request=async()=>true")
    px(sid, "document.getElementById('protectTyping').click()"); time.sleep(1.5)
    on = px(sid, "document.getElementById('protectTyping').checked"); close_tab(tid); return on
FORM = "document.body.insertAdjacentHTML('beforeend','<input id=t type=text><textarea id=ta></textarea><input id=pw type=password><div id=ce contenteditable=true style=\"min-height:20px;border:1px solid\"></div><input id=cb type=checkbox>');1"
def focus(sid, sel): ev(sid, "document.querySelector(%s).focus()" % json.dumps(sel), False)

def g10():
    reset(); keep = clean()
    mk("https://example.com/?k=pre")
    check("precondition: no typing script registered yet", sw_eval("chrome.scripting.getRegisteredContentScripts()") == [])
    check("options switch turns on after grant", enable_protection() is True)
    check("setting protectTyping stored true", storage()["settings"]["protectTyping"] is True)
    rs = sw_eval("chrome.scripting.getRegisteredContentScripts()")
    check("content script registered (all_frames, document_idle, persistent)", len(rs) == 1 and rs[0]["js"] == ["typing.js"] and rs[0]["allFrames"] is True and rs[0]["runAt"] == "document_idle" and rs[0]["persistAcrossSessions"] is True and rs[0]["matches"] == ["<all_urls>"], rs)
    kinds = ("text", "ta", "ce", "pw", "cb", "fake", "none", "nav")
    for k in kinds: mk("https://example.com/?k=" + k)
    S = {}
    for k in ("pre",) + kinds:
        _, S[k] = attach_url("?k=" + k); ev(S[k], FORM, False)
    for k, sel in (("pre", "#t"), ("text", "#t"), ("ta", "#ta"), ("ce", "#ce"), ("pw", "#pw")):
        focus(S[k], sel); type_text(S[k], "secret" if k == "pw" else "hello")
    ev(S["cb"], "document.querySelector('#cb').click()", False)
    ev(S["fake"], "(()=>{const e=document.querySelector('#t');e.value='x';e.dispatchEvent(new Event('input',{bubbles:true}))})()", False)
    time.sleep(1.0); d = set(dirty_ids()); idof = lambda k: one("?k=" + k)["id"]
    check("dirty: tab open BEFORE enabling (injected on enable)", idof("pre") in d, d)
    check("dirty: text input", idof("text") in d); check("dirty: textarea", idof("ta") in d); check("dirty: contenteditable", idof("ce") in d)
    check("not dirty: password typing ignored entirely", idof("pw") not in d)
    check("not dirty: checkbox click", idof("cb") not in d)
    check("not dirty: page-script synthetic (untrusted) input event", idof("fake") not in d)
    check("not dirty: tab nobody typed in", idof("none") not in d)
    run_check(31); time.sleep(1.0)
    for k in ("pre", "text", "ta", "ce"): check("dirty tab '%s' is NOT napped" % k, not one("?k=" + k)["discarded"])
    for k in ("pw", "cb", "fake", "none", "nav"): check("clean tab '%s' IS napped" % k, one("?k=" + k)["discarded"])
    check("dirty flags survive the check", {idof("text"), idof("ta")} <= set(dirty_ids()))
    cdp.send("Page.navigate", {"url": "https://example.com/?k=pre2"}, S["pre"]); time.sleep(2.5)
    check("navigation clears the dirty flag", one("?k=pre2")["id"] not in dirty_ids(), dirty_ids())
    run_check(31); time.sleep(0.8); check("after navigation the (clean) tab can nap", one("?k=pre2")["discarded"])
    cdp.send("Page.reload", {}, S["text"]); time.sleep(2.5)
    check("reload clears dirty for that tab", idof("text") not in dirty_ids(), dirty_ids())
    gone = idof("ta"); rm(gone); time.sleep(0.6)
    check("closing a tab removes its dirty flag", gone not in dirty_ids(), dirty_ids())
    tid, sid = ext_page("options.html", w=900, h=900); time.sleep(1.0)
    px(sid, "document.getElementById('protectTyping').click()"); time.sleep(1.5)
    check("switch off: setting false", storage()["settings"]["protectTyping"] is False)
    check("switch off: script unregistered", sw_eval("chrome.scripting.getRegisteredContentScripts()") == [])
    check("switch off: dirty set cleared", dirty_ids() == [], dirty_ids()); close_tab(tid)
    t2 = mk("https://example.com/?k=off"); _, s2 = attach_url("?k=off"); ev(s2, FORM, False)
    sw_eval("chrome.scripting.executeScript({target:{tabId:%d},files:['typing.js']})" % t2); time.sleep(0.5)
    focus(s2, "#t"); type_text(s2, "abc"); time.sleep(0.6)
    check("dirty message rejected while protection is off", one("?k=off")["id"] not in dirty_ids(), dirty_ids())
    clean()

# ================= group 11: security =================
def g11():
    reset(); clean()
    check("protection on for security tests", enable_protection() is True)
    mk("https://example.com/?s=a"); mk("https://example.org/?s=b")
    _, sa = attach_url("?s=a")
    check("content script world exists on the page", iso_ctx(sa) is not None)
    forged = {"supporter": {"type": "supporter", "sessionId": GOOD_SESSION}, "setProtection on": {"type": "setProtection", "enabled": True},
              "setProtection off": {"type": "setProtection", "enabled": False}, "unknown type": {"type": "napEverything"},
              "dirty wrong flag": {"type": "dirty", "dirty": "true"}, "dirty false": {"type": "dirty", "dirty": False}, "no type": {"hello": 1},
              "type not string": {"type": 5}, "proto": {"type": "__proto__"}}
    for k, m in forged.items():
        r = cs_send(sa, m); check("content script forging '%s' -> rejected" % k, r == {"ok": False}, r)
    idb = one("?s=b")["id"]
    r = cs_send(sa, {"type": "dirty", "dirty": True, "tabId": idb, "url": "https://example.org/"}); time.sleep(0.5); d = dirty_ids()
    check("valid dirty flags the sender tab only (tabId in message ignored)", r == {"ok": True} and one("?s=a")["id"] in d and idb not in d, (r, d))
    for area in ("local", "session"):
        res = cs_eval(sa, "(async()=>{try{const r=await chrome.storage.%s.get(null);return {leaked:JSON.stringify(r)}}catch(e){return {blocked:String(e).slice(0,120)}}})()" % area)
        check("content script cannot read chrome.storage.%s" % area, "blocked" in res, res)
    res = cs_eval(sa, "(async()=>{try{await chrome.storage.local.set({supporter:true});return 'wrote'}catch(e){return 'blocked'}})()")
    check("content script cannot write chrome.storage.local", res == "blocked" and not storage().get("supporter"), res)
    tid, sid = ext_page("options.html", w=600, h=500); time.sleep(0.8)
    send = lambda m: ev(sid, "chrome.runtime.sendMessage(%s)" % json.dumps(m))
    check("extension page: setProtection non-boolean rejected", send({"type": "setProtection", "enabled": "yes"}) == {"ok": False})
    check("extension page: supporter rejected (only the thanks page may)", send({"type": "supporter", "sessionId": GOOD_SESSION}) == {"ok": False} and not storage().get("supporter"))
    check("extension page: unknown type rejected", send({"type": "wipe"}) == {"ok": False})
    check("extension page: dirty (no tab sender) rejected", send({"type": "dirty", "dirty": True}) == {"ok": False})
    close_tab(tid)
    r = px(sa, "JSON.stringify({sendMessage:typeof (window.chrome&&chrome.runtime&&chrome.runtime.sendMessage),hook:typeof globalThis.__tabNapTest,storage:typeof (window.chrome&&chrome.storage)})")
    check("web page main world: no runtime.sendMessage, no debug hook, no storage", json.loads(r) == {"sendMessage": "undefined", "hook": "undefined", "storage": "undefined"}, r)
    tt, st_ = new_page("https://overcrasher.github.io/tab-nap/thanks.html?session_id=" + GOOD_SESSION); time.sleep(2)
    r = cs_send(st_, {"type": "setProtection", "enabled": False}); check("thanks-page content script: setProtection rejected", r == {"ok": False}, r)
    check("thanks-page script: protection still on afterwards", storage()["settings"]["protectTyping"] is True)
    close_tab(tt)
    r = cs_send(sa, {"type": "supporter", "sessionId": "cs_live_" + "a" * 24})
    check("supporter from a non-thanks tab rejected even with a valid-looking id", r == {"ok": False})
    clean()

# ================= group 12: REAL pages =================
def real_page_typing(url, selector, label, shotname):
    mk(url); time.sleep(2.0)
    _, sid = attach_url(url.split("//")[1][:22])
    found = wait_for(lambda: px(sid, "!!document.querySelector(%s)" % json.dumps(selector)), 15)
    check("%s: real page has the box %s" % (label, selector), found)
    if not found: return None
    focus(sid, selector); type_text(sid, "tab nap"); time.sleep(0.8)
    val = px(sid, "document.querySelector(%s).value" % json.dumps(selector))
    t = [x for x in tabs() if x["url"].startswith(url)][0]
    check("%s: text really typed ('%s')" % (label, val), val == "tab nap", val)
    check("%s: typing detector flagged the tab" % label, t["id"] in dirty_ids(), dirty_ids())
    shot(sid, shotname); return t["id"]
def g12():
    reset(); clean()
    check("protection on", enable_protection() is True)
    mk("https://en.wikipedia.org/wiki/Moon")
    ids = {}
    ids["ddg"] = real_page_typing("https://duckduckgo.com/", "textarea[name=q]", "duckduckgo.com", "real-duckduckgo-typed")
    ids["wiki"] = real_page_typing("https://en.wikipedia.org/wiki/Special:Search", "input#ooui-php-1", "wikipedia Special:Search", "real-wikipedia-typed")
    ids["bing"] = real_page_typing("https://www.bing.com/", "textarea[name=q], input[name=q]", "bing.com", "real-bing-typed")
    time.sleep(0.5); run_check(31); time.sleep(1.5)
    for k, u in (("ddg", "https://duckduckgo.com/"), ("wiki", "Special:Search"), ("bing", "bing.com")):
        if ids.get(k) is not None:
            t = [x for x in tabs() if u in x["url"]]
            check("real page %s with typed text is NOT napped" % k, t and not t[0]["discarded"], [(x["url"], x["discarded"]) for x in t])
    c = one("wiki/Moon")
    check("real page without typing IS napped", c["discarded"])
    check("napped real tab keeps https URL + title", c["url"] == "https://en.wikipedia.org/wiki/Moon" and "Moon" in (c.get("title") or ""), (c["url"], c.get("title")))
    activate(c["id"])
    ok = wait_for(lambda: not (tab(c["id"]) or {}).get("discarded") and (tab(c["id"]) or {}).get("status") == "complete", 30)
    check("real tab wakes on activation, URL intact", ok and (tab(c["id"]) or {}).get("url") == "https://en.wikipedia.org/wiki/Moon", (tab(c["id"]) or {}).get("url"))
    _, sc = attach_url("wiki/Moon"); title = px(sc, "document.title"); check("woken real page content loaded", "Moon" in title, title)
    shot(sc, "real-wikipedia-restored")
    for u in ("https://duckduckgo.com/?q=restore-test", "https://example.com/?real=1"): mk(u)
    run_check(31); time.sleep(1.0)
    for u in ("duckduckgo.com/?q=restore-test", "example.com/?real=1"):
        t = one(u); check("real %s napped" % u, t and t["discarded"])
        activate(t["id"]); ok = wait_for(lambda: (tab(t["id"]) or {}).get("status") == "complete" and not (tab(t["id"]) or {}).get("discarded"), 30)
        check("real %s restored with URL intact" % u, ok and (tab(t["id"]) or {}).get("url", "").endswith(u), (tab(t["id"]) or {}).get("url"))
    clean()

def g13():  # REAL build config (single EUR 3 link): banner + options show exactly one button
    reset(extra={"tabHours": 100}); clean()
    tid, sid = open_popup(); b = banner_info(sid)
    check("real build: banner shown at 100 tab-hours", not b["hidden"], b)
    check("real build: exactly one button '€3' (no pick-your-own, no monthly), no note", [x["t"] for x in b["btns"]] == ["€3"] and b["note"] == "", b)
    shot(sid, "popup-banner-single-link")
    TABS_SEEN.clear(); px(sid, "document.querySelector('#banner-buttons button, #banner-buttons a').click()"); time.sleep(1.0)
    check("real build: click opens the real donate.stripe.com link", any(u == "https://donate.stripe.com/aFa14o3tB3U00Fc70Gfbq0a" for u in TABS_SEEN), TABS_SEEN)
    close_tab(tid)
    reset(extra={"tabHours": 5}); tid, sid = ext_page("options.html", w=900, h=1500); time.sleep(1.0); st = opt_state(sid)
    check("real build options: only '€3', no monthly", st["donateBtns"] == ["€3"] and st["donateNote"] == "", (st["donateBtns"], st["donateNote"]))
    shot(sid, "options-single-link", full=True); close_tab(tid)

NAMES = {1: "Install / manifest / welcome", 2: "NEVER rules", 3: "Minute check / threshold / pause / alarm", 4: "Context menu handlers", 5: "Popup",
         6: "Options", 7: "Supporter / no-links / rating", 8: "Donation banner (links copy)", 9: "Evil donation links", 10: "Typing protection flow",
         11: "Security", 12: "Real pages", 13: "Real build: single EUR 3 link"}
TESTS = [(1, "main", g1), (2, "main", g2), (3, "main", g3), (4, "main", g4), (5, "main", g5), (6, "nolinks", g6), (7, "nolinks", g7),
         (8, "links", g8), (9, "evil", g9), (10, "hostperm", g10), (11, "hostperm", g11), (12, "hostperm", g12), (13, "main", g13)]

def run_phase(phase, ext_path):
    todo = [(n, f) for n, p, f in TESTS if p == phase and (not ONLY or n in ONLY)]
    if not todo: return
    sw["sid"] = None; sw["tid"] = None; TABS_SEEN.clear()
    start(ext_path)
    try:
        time.sleep(1.5)
        for n, f in todo:
            CUR[0] = n; t0 = time.time(); print("== Group %d: %s [%s]" % (n, NAMES[n], f.__name__), flush=True)
            try: f()
            except Exception as e:
                check("group crashed", False, "%s: %s" % (type(e).__name__, e)); traceback.print_exc()
            print("   (%.0fs)" % (time.time() - t0), flush=True)
        errs = [l for l in LOGS if l[1] == "exception" or (l[1].endswith("error") and "Failed to load resource" not in l[2])]
        print("\n== error-level logs/exceptions in phase %s (%d):" % (phase, len(errs)))
        for l in errs[:20]: print("  ", l)
    finally: cdp.close()

def main():
    T0 = time.time()
    need = lambda p: any(pp == p and (not ONLY or n in ONLY) for n, pp, _ in TESTS)
    try:
        run_phase("main", EXT)
        if need("nolinks"): run_phase("nolinks", copy_ext("ext-nolinks", '{ small: "", medium: "", large: "", custom: "", monthly: "" }'))
        if need("links"): run_phase("links", copy_ext("ext-links", LINKS))
        if need("evil"): run_phase("evil", copy_ext("ext-evil", '{ small: "https://evil.example/x", medium: "https://buy.stripe.com.evil.example/x", large: "http://donate.stripe.com/x", custom: "https://evil.example/custom", monthly: "https://evil.example/m" }'))
        if need("hostperm"): run_phase("hostperm", copy_ext("ext-hostperm", None, host_perm=True))
    finally: shutil.rmtree(WORK, ignore_errors=True)
    print("\n================ RESULTS ================")
    tp = tf = 0
    for n in sorted(RESULTS):
        r = RESULTS[n]; ok = sum(x[1] for x in r); tp += ok; tf += len(r) - ok
        print("%2d  %-4s %-42s (%d/%d)" % (n, "PASS" if ok == len(r) else "FAIL", NAMES[n], ok, len(r)))
        for c, o, e in r:
            if not o: print("      FAIL:", c, "|", e[:400])
    print("TOTAL: %d passed, %d failed, %.0f s" % (tp, tf, time.time() - T0))
if __name__ == "__main__": main()
