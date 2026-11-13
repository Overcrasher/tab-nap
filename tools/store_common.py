"""Shared plumbing for the Chrome Web Store image generators (identical copy in reclaim/, tab-nap/, quiet-web/ tools/).
- CDP over --remote-debugging-pipe (copied from the E2E harness), Extensions.loadUnpacked, Fetch fixtures, screenshots
- compose(): renders an HTML string in a clean headless Chrome (no extension) to an exact-size PNG
- PNG helpers (stdlib only): to_rgb24() strips alpha so screenshots/tiles are 24-bit, png_size() reads the header."""
import fcntl, os, sys, json, time, base64, shutil, subprocess, threading, queue, traceback, tempfile, zlib, struct

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

class CDP:
    def __init__(self, tag="store"):
        r1, w1 = os.pipe(); r2, w2 = os.pipe()
        r1, w1, r2, w2 = [fcntl.fcntl(f, fcntl.F_DUPFD_CLOEXEC, 20) for f in (r1, w1, r2, w2)]
        def pre():
            os.dup2(r1, 3, inheritable=True); os.dup2(w2, 4, inheritable=True)
        self.profile = tempfile.mkdtemp(prefix=tag + "-profile-")   # throwaway, lives in /tmp
        args = [CHROME, "--headless=new", "--enable-unsafe-extension-debugging", "--remote-debugging-pipe", "--user-data-dir=" + self.profile,
                "--no-first-run", "--no-default-browser-check", "--window-size=1400,900", "--hide-scrollbars", "--force-color-profile=srgb",
                "--autoplay-policy=no-user-gesture-required", "about:blank"]
        self.proc = subprocess.Popen(args, preexec_fn=pre, close_fds=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    def send(self, method, params=None, sid=None, timeout=60):
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

class Ext:
    """A headless Chrome with one unpacked extension loaded. Fixture pages are served on neutral hostnames via Fetch."""
    def __init__(self, ext_path, tag, fixture=lambda url: None, fetch_hosts=()):
        self.cdp = CDP(tag); self.fixture = fixture; self.fetch_hosts = list(fetch_hosts)
        self.sw = {"sid": None, "tid": None}; self.labels = {}; self.iso = {}
        self.cdp.listeners.append(self._on_event); time.sleep(2)
        self.cdp.send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True, "filter": [{"type": "service_worker"}, {"exclude": True}]})
        self.cdp.send("Target.setDiscoverTargets", {"discover": True})
        self.id = self.cdp.send("Extensions.loadUnpacked", {"path": ext_path})["id"]
    def _on_event(self, e):
        cdp = self.cdp; m, p, sid = e.get("method"), e.get("params", {}), e.get("sessionId")
        if m == "Fetch.requestPaused":
            url = p["request"]["url"]; r = self.fixture(url)
            try:
                if r is None:
                    cdp.send("Fetch.fulfillRequest", {"requestId": p["requestId"], "responseCode": 404, "responseHeaders": [{"name": "Content-Type", "value": "text/plain"}], "body": base64.b64encode(b"nf").decode()}, sid)
                else:
                    body, ctype = r if isinstance(r, tuple) else (r, "text/html; charset=utf-8")
                    if isinstance(body, str): body = body.encode()
                    cdp.send("Fetch.fulfillRequest", {"requestId": p["requestId"], "responseCode": 200, "responseHeaders": [{"name": "Content-Type", "value": ctype}], "body": base64.b64encode(body).decode()}, sid)
            except Exception as ex: print("fetch err", ex)
        elif m == "Runtime.executionContextCreated":
            c = p["context"]
            if c.get("auxData", {}).get("type") == "isolated": self.iso.setdefault(sid, []).append((c["id"], c.get("origin", "")))
        elif m == "Runtime.executionContextsCleared": self.iso[sid] = []
        elif m == "Target.attachedToTarget" and p["targetInfo"]["type"] == "service_worker":
            s = p["sessionId"]; self.labels[s] = "SW"; self.sw["sid"] = s; self.sw["tid"] = p["targetInfo"]["targetId"]
            for meth in ("Runtime.enable", "Log.enable"):
                try: cdp.send(meth, {}, s)
                except Exception: pass
            try: cdp.send("Runtime.runIfWaitingForDebugger", {}, s)
            except Exception: pass
    def get_sw(self):
        cdp = self.cdp
        for _ in range(30):
            s = [t for t in cdp.send("Target.getTargets")["targetInfos"] if t["type"] == "service_worker" and self.id in t["url"]]
            if s:
                if self.sw["tid"] != s[0]["targetId"] or not self.sw["sid"]:
                    sid = cdp.send("Target.attachToTarget", {"targetId": s[0]["targetId"], "flatten": True})["sessionId"]
                    self.sw["sid"] = sid; self.sw["tid"] = s[0]["targetId"]
                    cdp.send("Runtime.enable", {}, sid)
                return self.sw["sid"]
            time.sleep(0.5)
        raise RuntimeError("no service worker")
    def ev(self, sid, expr, await_=True):
        r = self.cdp.send("Runtime.evaluate", {"expression": expr, "awaitPromise": await_, "returnByValue": True}, sid)
        if "exceptionDetails" in r: raise RuntimeError("eval: " + json.dumps(r["exceptionDetails"])[:400])
        return r["result"].get("value")
    def sw_eval(self, expr):
        for i in range(6):
            try: return self.ev(self.get_sw(), expr)
            except Exception as e:
                if i < 5 and any(k in str(e) for k in ("Session", "not found", "closed", "Cannot find context")): self.sw["sid"] = None; time.sleep(1.2); continue
                raise
    def new_tab(self, url, w=1100, h=800, dpr=1, fetch=True, dark=False, wait=1.5, pre_script=None):
        cdp = self.cdp
        tid = cdp.send("Target.createTarget", {"url": "about:blank"})["targetId"]
        sid = cdp.send("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
        for m in ("Runtime.enable", "Page.enable", "DOM.enable"): cdp.send(m, {}, sid)
        if fetch: cdp.send("Fetch.enable", {"patterns": [{"urlPattern": "https://%s/*" % x} for x in self.fetch_hosts]}, sid)
        cdp.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": dpr, "mobile": False}, sid)
        cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark" if dark else "light"}]}, sid)
        try: cdp.send("Emulation.setFocusEmulationEnabled", {"enabled": True}, sid)
        except Exception: pass
        if pre_script: cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": pre_script}, sid)
        if url != "about:blank": cdp.send("Page.navigate", {"url": url}, sid); time.sleep(wait)
        return tid, sid
    def close_tab(self, tid):
        try: self.cdp.send("Target.closeTarget", {"targetId": tid})
        except Exception: pass
        time.sleep(0.4)
    def shot(self, sid, path, clip=None):
        p = {"format": "png"}
        if clip: p["clip"] = dict(clip, scale=1)
        open(path, "wb").write(base64.b64decode(self.cdp.send("Page.captureScreenshot", p, sid)["data"])); return path
    def mouse_click(self, sid, x, y):
        c = self.cdp
        c.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "button": "none", "buttons": 0}, sid)
        c.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "buttons": 1, "clickCount": 1}, sid)
        c.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "buttons": 0, "clickCount": 1}, sid); time.sleep(0.6)
    def close(self): self.cdp.close()

def wait_for(fn, t=8):
    end = time.time() + t
    while time.time() < end:
        try:
            v = fn()
            if v: return v
        except Exception: pass
        time.sleep(0.3)
    return False

# ---------------------------------------------------------------- PNG helpers
def _chunks(b):
    i = 8
    while i < len(b):
        n, t = struct.unpack(">I4s", b[i:i + 8]); yield t, b[i + 8:i + 8 + n]; i += 12 + n
def png_size(path):
    b = open(path, "rb").read(33); return struct.unpack(">II", b[16:24]), b[24], b[25]   # (w,h), bitdepth, colortype
def to_rgb24(src, dst, flatten=(255, 255, 255)):
    """Re-encode any 8-bit RGB/RGBA PNG as a 24-bit RGB PNG (alpha composited onto `flatten`)."""
    b = open(src, "rb").read(); w = h = ct = None; idat = b""
    for t, d in _chunks(b):
        if t == b"IHDR": w, h, bd, ct, _, _, il = struct.unpack(">IIBBBBB", d); assert bd == 8 and il == 0 and ct in (2, 6), (bd, ct, il)
        elif t == b"IDAT": idat += d
    bpp = 4 if ct == 6 else 3; raw = zlib.decompress(idat); stride = w * bpp; prev = bytearray(stride); out = bytearray()
    pos = 0
    for _ in range(h):
        f = raw[pos]; line = bytearray(raw[pos + 1:pos + 1 + stride]); pos += 1 + stride
        if f == 1:
            for i in range(bpp, stride): line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride): line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride): line[i] = (line[i] + ((line[i - bpp] if i >= bpp else 0) + prev[i]) // 2) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0; bb = prev[i]; c = prev[i - bpp] if i >= bpp else 0
                p = a + bb - c; pa, pb, pc = abs(p - a), abs(p - bb), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else bb if pb <= pc else c)) & 255
        prev = line
        if ct == 6:
            rgb = bytearray(w * 3)
            for x in range(w):
                a = line[x * 4 + 3]
                for k in range(3):
                    rgb[x * 3 + k] = line[x * 4 + k] if a == 255 else (line[x * 4 + k] * a + flatten[k] * (255 - a)) // 255
            out += b"\0" + rgb
        else: out += b"\0" + line
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(dst, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(bytes(out), 9)) + ch(b"IEND", b""))

# ---------------------------------------------------------------- composing
def data_uri(path, mime="image/png"):
    return "data:%s;base64,%s" % (mime, base64.b64encode(open(path, "rb").read()).decode())
class Composer:
    """Clean headless Chrome (no extension) that renders HTML to exact-size PNGs."""
    def __init__(self):
        self.cdp = CDP("compose")
        tid = self.cdp.send("Target.createTarget", {"url": "about:blank"})["targetId"]
        self.sid = self.cdp.send("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
        for m in ("Runtime.enable", "Page.enable"): self.cdp.send(m, {}, self.sid)
    def render(self, html, w, h, out, transparent=False, rgb=True):
        c, sid = self.cdp, self.sid
        c.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False}, sid)
        c.send("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0 if transparent else 1}}, sid)
        tree = c.send("Page.getFrameTree", {}, sid)["frameTree"]["frame"]["id"]
        c.send("Page.setDocumentContent", {"frameId": tree, "html": html}, sid)
        r = c.send("Runtime.evaluate", {"expression": "Promise.all([document.fonts.ready,...[...document.images].map(i=>i.decode().catch(()=>0))]).then(()=>new Promise(r=>setTimeout(r,250))).then(()=>[document.documentElement.scrollWidth,document.documentElement.scrollHeight])", "awaitPromise": True, "returnByValue": True}, sid)
        tmp = out + ".tmp.png"
        open(tmp, "wb").write(base64.b64decode(c.send("Page.captureScreenshot", {"format": "png", "clip": {"x": 0, "y": 0, "width": w, "height": h, "scale": 1}}, sid)["data"]))
        if transparent or not rgb: os.replace(tmp, out)
        else: to_rgb24(tmp, out); os.remove(tmp)
        return r["result"].get("value")
    def close(self): self.cdp.close()

# ---------------------------------------------------------------- layouts (HTML strings; palette dict p)
FONT = '-apple-system,BlinkMacSystemFont,"SF Pro Display","Helvetica Neue",Helvetica,Arial,sans-serif'
def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def _page(p, body, css=""):
    return """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;width:100%%;height:100%%}body{font-family:%s;color:%s;background:%s;overflow:hidden;-webkit-font-smoothing:antialiased}
.abs{position:absolute}
h1{margin:0;font-weight:800;letter-spacing:-.03em;line-height:1.08}
.bar{height:7px;width:72px;border-radius:4px;background:%s}
img{display:block}
%s</style></head><body>%s</body></html>""" % (FONT, p["ink"], p["bg"], p["bar"], css, body)

def side(p, title, img, iw, ih, name, icon, sub=""):
    """1280x800: headline + brand left on the page colour, real UI on a dark brand panel right."""
    sc = min(540 / iw, 700 / ih, 1.5); w, h = round(iw * sc), round(ih * sc)
    css = """.left{position:absolute;left:84px;top:0;bottom:0;width:520px;display:flex;flex-direction:column;justify-content:center}
.brand{display:flex;align-items:center;gap:14px;font-weight:700;font-size:23px;margin-bottom:34px}.brand img{width:46px;height:46px;border-radius:11px}
h1{font-size:62px}.bar{margin-top:34px}.sub{margin-top:26px;font-size:24px;line-height:1.4;color:%(muted)s;max-width:470px}
.panel{position:absolute;left:660px;top:0;right:0;bottom:0;background:linear-gradient(160deg,%(d1)s,%(d2)s)}
.panel:before{content:"";position:absolute;inset:0;background:radial-gradient(520px 420px at 70%% 20%%,%(glow)s,transparent 70%%)}
.shot{position:absolute;left:%(x)dpx;top:%(y)dpx;width:%(w)dpx;height:%(h)dpx;border-radius:22px;box-shadow:0 30px 70px rgba(0,0,0,.38),0 0 0 1px rgba(0,0,0,.06);overflow:hidden}
.shot img{width:100%%;height:100%%}""" % dict(p, x=660 + (620 - w) // 2, y=(800 - h) // 2, w=w, h=h)
    body = '<div class="left"><div class="brand"><img src="%s"><span>%s</span></div><h1>%s</h1><div class="bar"></div>%s</div><div class="panel"></div><div class="shot"><img src="%s"></div>' % (
        icon, esc(name), esc(title), '<div class="sub">%s</div>' % esc(sub) if sub else "", img)
    return _page(p, body, css)

def browser(img, host, w=1120, h=610):
    """A neutral browser-window frame (drawn, no real browser UI) around a captured viewport image."""
    return """<div class="win" style="width:%dpx;height:%dpx"><div class="tb"><i></i><i></i><i></i><span class="url">%s</span></div><img src="%s" style="width:%dpx;height:%dpx"></div>""" % (w, h, esc(host), img, w, h - 38)
BROWSER_CSS = """.win{border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 26px 60px rgba(15,23,42,.28),0 0 0 1px rgba(15,23,42,.10);position:relative}
.tb{height:38px;background:#ECEEF1;display:flex;align-items:center;padding:0 14px;gap:7px;border-bottom:1px solid #D9DCE1}
.tb i{width:11px;height:11px;border-radius:50%;background:#C9CDD3}.tb i:nth-child(1){background:#F26B5E}.tb i:nth-child(2){background:#F5BD4F}.tb i:nth-child(3){background:#5DC769}
.url{margin-left:18px;flex:0 0 380px;height:24px;border-radius:12px;background:#fff;color:#5B6470;font-size:13px;display:flex;align-items:center;padding:0 14px}"""

def wide(p, title, card_html, icon, extra_css=""):
    """1280x800: headline on top, framed wide visual below (card_html is placed at 80,150, size 1120x610)."""
    css = BROWSER_CSS + """.hd{position:absolute;left:80px;top:34px;right:80px;height:100px;display:flex;align-items:center;justify-content:space-between}
h1{font-size:54px}.mk{width:60px;height:60px;border-radius:14px;box-shadow:0 8px 20px rgba(0,0,0,.18)}.card{position:absolute;left:80px;top:150px}
.bg2{position:absolute;inset:0;background:radial-gradient(900px 500px at 85%% 0%%,%(glow2)s,transparent 70%%)}""" % p + extra_css
    body = '<div class="bg2"></div><div class="hd"><h1>%s</h1><img class="mk" src="%s"></div><div class="card">%s</div>' % (esc(title), icon, card_html)
    return _page(p, body, css)

SVG = {
 "shield": '<path d="M12 3l7 3v5c0 4.500-3 8-7 10-4-2-7-5.500-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
 "ban": '<circle cx="12" cy="12" r="9"/><path d="M5.700 5.700l12.600 12.600"/>',
 "code": '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>',
 "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
 "wifi-off": '<path d="M3 3l18 18M8.500 16.500a5 5 0 0 1 7 0M5 12.500a10 10 0 0 1 3-2M19 12.500a10 10 0 0 0-6-3M12 20h.01"/>',
}
def icon_svg(name, color): return '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % (color, SVG[name])

def privacy(p, title, rows, img, iw, ih, icon, name):
    """1280x800 privacy slide: headline + three rows left, real UI card right. rows = [(svg_name, text)]."""
    sc = min(500 / iw, 600 / ih, 1.4); w, h = round(iw * sc), round(ih * sc)
    css = """.left{position:absolute;left:84px;top:0;width:580px;bottom:0;display:flex;flex-direction:column;justify-content:center}
.mk{width:76px;height:76px;border-radius:18px;box-shadow:0 10px 26px rgba(0,0,0,.2);margin-bottom:30px}
h1{font-size:50px}.rows{margin-top:36px;display:flex;flex-direction:column;gap:14px}
.row{display:flex;align-items:center;gap:18px;background:rgba(255,255,255,.88);border:1px solid %(rowb)s;border-radius:18px;padding:16px 20px;font-size:25px;font-weight:600;box-shadow:0 6px 18px rgba(15,23,42,.06)}
.ic{width:52px;height:52px;border-radius:14px;background:%(soft)s;display:flex;align-items:center;justify-content:center;flex:none}
.glow{position:absolute;inset:0;background:radial-gradient(520px 520px at 82%% 52%%,%(glow2)s,transparent 70%%)}
.shot{position:absolute;left:%(x)dpx;top:%(y)dpx;width:%(w)dpx;height:%(h)dpx;border-radius:22px;box-shadow:0 28px 64px rgba(15,23,42,.22),0 0 0 1px rgba(15,23,42,.08);overflow:hidden}.shot img{width:100%%;height:100%%}""" % dict(
        p, x=700 + (540 - w) // 2, y=(800 - h) // 2, w=w, h=h)
    rh = "".join('<div class="row"><div class="ic">%s</div><span>%s</span></div>' % (icon_svg(s, p["accent"]), esc(t)) for s, t in rows)
    body = '<div class="glow"></div><div class="left"><img class="mk" src="%s"><h1>%s</h1><div class="rows">%s</div></div><div class="shot"><img src="%s"></div>' % (icon, esc(title), rh, img)
    return _page(p, body, css)

def promo_small(p, name, tagline, line2, icon):
    css = """.c{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;background:radial-gradient(360px 220px at 50%% 0%%,%(glow2)s,transparent 70%%)}
.mk{width:76px;height:76px;border-radius:19px;box-shadow:0 10px 26px rgba(0,0,0,.22)}.n{font-size:38px;font-weight:800;letter-spacing:-.03em;color:%(dark)s;margin-top:12px;line-height:1.05}
.t{font-size:19px;font-weight:700;margin-top:7px;color:%(ink)s}.l{font-size:15px;margin-top:5px;color:%(muted)s}.bar{margin-top:12px;width:44px;height:5px}""" % p
    body = '<div class="c"><img class="mk" src="%s"><div class="n">%s</div><div class="t">%s</div><div class="l">%s</div><div class="bar"></div></div>' % (icon, esc(name), esc(tagline), esc(line2))
    return _page(p, body, css)

def promo_marquee(p, name, tagline, line2, icon, img, iw, ih):
    sc = min(500 / iw, 460 / ih, 1.5); w, h = round(iw * sc), round(ih * sc)
    css = """body{background:linear-gradient(120deg,%(d1)s,%(d2)s)}.glow{position:absolute;inset:0;background:radial-gradient(640px 500px at 85%% 40%%,%(glow)s,transparent 70%%)}
.left{position:absolute;left:100px;top:0;bottom:0;width:700px;display:flex;flex-direction:column;justify-content:center;color:#fff}
.mk{width:104px;height:104px;border-radius:26px;background:%(bg)s;padding:7px;box-shadow:0 12px 30px rgba(0,0,0,.28)}.mk img{width:90px;height:90px;border-radius:21px}
.n{font-size:86px;font-weight:800;letter-spacing:-.035em;margin-top:26px;line-height:1}.t{font-size:40px;font-weight:700;margin-top:14px;color:%(hi)s}.l{font-size:27px;margin-top:10px;color:rgba(255,255,255,.82)}
.shot{position:absolute;left:%(x)dpx;top:%(y)dpx;width:%(w)dpx;height:%(h)dpx;border-radius:20px;box-shadow:0 26px 60px rgba(0,0,0,.4);overflow:hidden}.shot img{width:100%%;height:100%%}""" % dict(p, x=1400 - 90 - w, y=(560 - h) // 2, w=w, h=h)
    body = '<div class="glow"></div><div class="left"><div class="mk"><img src="%s"></div><div class="n">%s</div><div class="t">%s</div><div class="l">%s</div></div><div class="shot"><img src="%s"></div>' % (icon, esc(name), esc(tagline), esc(line2), img)
    return _page(p, body, css)

def store_icon(icon_uri):
    return '<!doctype html><html><body style="margin:0;background:transparent"><img src="%s" style="position:absolute;left:16px;top:16px;width:96px;height:96px"></body></html>' % icon_uri

def finish_check(out_dir, shots=5):
    """Verify exact sizes/bit depths from the PNG headers; returns list of report lines."""
    exp = {"promo-small-440x280.png": (440, 280), "promo-marquee-1400x560.png": (1400, 560), "store-icon-128.png": (128, 128)}
    lines = []
    for f in sorted(os.listdir(out_dir)):
        if not f.endswith(".png"): continue
        (w, h), bd, ct = png_size(os.path.join(out_dir, f))
        e = exp.get(f, (1280, 800)); ok = (w, h) == e and bd == 8 and (ct == 2 or (f == "store-icon-128.png" and ct == 6))
        lines.append("%s %dx%d depth=%d colortype=%d %s" % (f, w, h, bd, ct, "OK" if ok else "BAD"))
    return lines
