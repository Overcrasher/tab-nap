#!/usr/bin/env python3
"""Generates store/images/* for the Chrome Web Store (1280x800 screenshots, promo tiles, store icon).
Real UI is captured from the unpacked extension in headless Chrome (CDP, same plumbing as tests/e2e), then composed on
branded backgrounds by tools/store_common.py layouts. Usage:  python3 tools/store_images.py [capture] [compose]   (default: both)
Raw captures go to tools/store_raw/ (gitignored); final PNGs to store/images/. Throwaway Chrome profiles live in /tmp.
Illustrations drawn in HTML (not captured): the browser tab strip in screenshot 2 and the context menu in screenshot 4
(headless Chrome cannot render native menus). Options screenshot 3 stubs chrome.permissions.contains so the typing switch shows ON."""
import os, sys, json, time, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from store_common import *

RAW = os.path.join(HERE, "store_raw"); OUT = os.path.join(ROOT, "store", "images")
os.makedirs(RAW, exist_ok=True); os.makedirs(OUT, exist_ok=True)
ICON = os.path.join(ROOT, "icons", "icon128.png")
P = dict(bg="#F5F3FF", ink="#1E1B4B", muted="#5B5896", bar="#F2B93B", accent="#312E81", dark="#312E81", hi="#FDE68A", soft="#E0E4FF",
         rowb="#DDD8F3", d1="#4B46B0", d2="#211F5C", glow="rgba(165,180,252,.35)", glow2="rgba(165,180,252,.32)")
NAME = "Tab Nap"

SITES = [  # host, title, favicon colour, letter
    ("docs.acme-notes.example", "Quarterly planning notes", "#6366F1", "D"),
    ("mail.brightbox.example", "Inbox (3) - Brightbox Mail", "#0EA5E9", "M"),
    ("trails.wanderly.example", "Trail running routes near you", "#10B981", "T"),
    ("recipes.tastebook.example", "Creamy pasta, ready in 20 minutes", "#F97316", "R"),
    ("fares.skyroute.example", "Flights to Lisbon - compare prices", "#EC4899", "F"),
    ("design.pixelkit.example", "Design system - Buttons", "#8B5CF6", "P"),
    ("metrics.chartly.example", "Weekly metrics dashboard", "#14B8A6", "C"),
    ("news.daybreak.example", "Morning headlines - Daybreak", "#EF4444", "N"),
]
def fav(c, l):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="%s"/><text x="16" y="22.5" font-family="Arial" font-weight="700" font-size="19" text-anchor="middle" fill="#fff">%s</text></svg>' % (c, l)
    return "data:image/svg+xml," + urllib.parse.quote(svg)
def page(host, title, c, l):
    return """<!doctype html><html><head><meta charset="utf-8"><title>%s</title><link rel="icon" href="%s"></head><body style="margin:0;font-family:-apple-system,Arial,sans-serif;background:#F6F7F9;color:#1D2430">
<div style="height:58px;background:#fff;border-bottom:1px solid #E2E6EB;display:flex;align-items:center;padding:0 32px;gap:12px"><div style="width:30px;height:30px;border-radius:8px;background:%s"></div><b style="font-size:18px">%s</b></div>
<div style="padding:34px 32px;max-width:760px"><h1 style="margin:0 0 14px;font-size:34px;letter-spacing:-.02em">%s</h1>%s</div></body></html>""" % (
        title, fav(c, l), c, host.split(".")[1].title(), title, "".join('<div style="height:12px;border-radius:6px;background:#DDE1E7;margin:12px 0;width:%d%%"></div>' % w for w in (96, 90, 98, 72, 94, 88, 60)))
FX = {h: page(h, t, c, l) for h, t, c, l in SITES}
ARTICLE = """<!doctype html><html><head><meta charset="utf-8"><title>Daybreak</title></head><body style="margin:0;font-family:Georgia,serif;background:#fff;color:#1D2430">
<div style="height:60px;border-bottom:1px solid #E5E7EB;display:flex;align-items:center;padding:0 40px;font:800 22px -apple-system,Arial,sans-serif">Daybreak <span style="margin-left:30px;font-weight:600;font-size:15px;color:#6B7280">World &nbsp; Science &nbsp; Culture &nbsp; Travel</span></div>
<div style="display:flex;gap:36px;padding:34px 40px"><div style="flex:1"><div style="font:700 13px -apple-system,Arial;color:#6366F1;letter-spacing:.08em">TRAVEL</div>
<h1 style="font-size:44px;line-height:1.1;margin:10px 0 18px;letter-spacing:-.02em">The quiet villages worth a detour this autumn</h1>%s</div>
<div style="width:330px;height:300px;border-radius:14px;background:linear-gradient(135deg,#A5B4FC,#FDE68A)"></div></div></body></html>""" % "".join('<div style="height:13px;border-radius:6px;background:#E5E7EB;margin:13px 0;width:%d%%"></div>' % w for w in (98, 94, 99, 70, 96, 90, 97, 64))
def fixture(url):
    if url.startswith("https://news.daybreak.example/article"): return ARTICLE
    for h in FX:
        if url.startswith("https://%s/" % h): return FX[h]
    return None

def capture():
    x = Ext(ROOT, "tabnap-store", fixture, [h for h, *_ in SITES]); sizes = {}
    try:
        time.sleep(1.5)
        for t in x.cdp.send("Target.getTargets")["targetInfos"]:
            if "/welcome.html" in t["url"]: x.close_tab(t["targetId"])
        x.sw_eval("chrome.storage.local.clear().then(()=>chrome.storage.session.clear())")
        x.sw_eval("chrome.storage.local.set(%s)" % json.dumps({"settings": {"thresholdMin": 30, "protectPinned": True, "avgMb": 150, "whitelist": ["docs.acme-notes.example", "mail.brightbox.example", "metrics.chartly.example"], "protectTyping": True},
            "napCount": 86, "tabHours": 1240, "rating": {"shown": True, "at": int(time.time() * 1000)}, "donation": {"asked": [], "lastAskAt": int(time.time() * 1000), "dontAskAgain": True}}))
        # real tabs on fixture pages; the first 7 are put to sleep with chrome.tabs.discard, like Tab Nap does
        order = SITES[2:] + SITES[:2]; keep = SITES[0]
        for h, *_ in order: x.new_tab("https://%s/" % h, 900, 600, wait=0.8)
        t_keep, s_keep = x.new_tab("https://%s/" % keep[0], 900, 600, wait=1.0)
        time.sleep(1.5)
        ids = x.sw_eval("""(async()=>{const ts=await chrome.tabs.query({});const hosts=%s;const out=[];
          for(const t of ts){let h='';try{h=new URL(t.url).hostname}catch(e){} if(hosts.includes(h)&&h!==%s){out.push(t.id);await chrome.tabs.discard(t.id)}}
          const k=ts.find(t=>t.url&&t.url.includes(%s));if(k)await chrome.tabs.update(k.id,{active:true});
          const dd=(await chrome.tabs.query({discarded:true})).map(t=>t.id);await chrome.storage.session.set({napped:dd});return dd})()""" % (json.dumps([h for h, *_ in order]), json.dumps(keep[0]), json.dumps(keep[0])))
        print("napped ids", ids); time.sleep(1.0)
        sleeping = x.sw_eval("chrome.tabs.query({discarded:true}).then(t=>t.map(x=>[x.title,x.url]))"); print(sleeping)
        # popup
        tid, sid = x.new_tab("chrome-extension://%s/popup.html" % x.id, 360, 800, dpr=2, fetch=False, wait=2.0)
        x.ev(sid, "document.querySelectorAll('.fav').forEach(i=>{})", False)
        h = x.ev(sid, "Math.ceil(document.body.getBoundingClientRect().height)", False)
        x.shot(sid, os.path.join(RAW, "popup.png"), clip={"x": 0, "y": 0, "width": 360, "height": h}); sizes["popup"] = [360, h]
        hh = x.ev(sid, "Math.ceil(document.querySelector('#listSection').getBoundingClientRect().top)-4", False)
        x.shot(sid, os.path.join(RAW, "popup-top.png"), clip={"x": 0, "y": 0, "width": 360, "height": hh}); sizes["popup-top"] = [360, hh]
        x.close_tab(tid)
        # options sections
        stub = "chrome.permissions.contains=()=>Promise.resolve(true);"
        tid, sid = x.new_tab("chrome-extension://%s/options.html" % x.id, 640, 2400, dpr=2, fetch=False, wait=2.0, pre_script=stub)
        r = json.loads(x.ev(sid, "JSON.stringify([...document.querySelectorAll('main > section')].map(c=>{const r=c.getBoundingClientRect();return [r.left,r.top+scrollY,r.width,r.height]}))", False))
        names = ["threshold", "never", "sites", "typing", "memory", "pause"]
        for n, c_ in zip(names, r):
            x.shot(sid, os.path.join(RAW, "opt-%s.png" % n), clip={"x": c_[0] - 4, "y": c_[1] - 4, "width": c_[2] + 8, "height": c_[3] + 8}); sizes["opt-" + n] = [c_[2] + 8, c_[3] + 8]
        x.close_tab(tid)
        # context-menu backdrop: generic article page
        tid, sid = x.new_tab("https://news.daybreak.example/article", 1120, 572, dpr=2, wait=1.5)
        x.shot(sid, os.path.join(RAW, "article.png")); x.close_tab(tid)
        json.dump(sizes, open(os.path.join(RAW, "sizes.json"), "w")); print(sizes)
    finally:
        x.close()

def chrome_frame(popup_uri, pw, ph, icon):
    """Browser window drawn in HTML: tab strip with awake/asleep tabs, toolbar with the extension icon, generic page, real popup on top."""
    tabs = [("Quarterly planning notes", SITES[0], False), ("Inbox (3) - Brightbox Mail", SITES[1], False), ("Trail running routes", SITES[2], True), ("Creamy pasta, ready in 20 min", SITES[3], True),
            ("Flights to Lisbon", SITES[4], True), ("Design system - Buttons", SITES[5], True), ("Weekly metrics", SITES[6], True)]
    th = ""
    for i, (t, s, asleep) in enumerate(tabs):
        act = i == 0
        th += '<div class="tab%s%s"><img src="%s"><span>%s</span>%s</div>' % (" act" if act else "", " zz" if asleep else "", fav(s[2], s[3]), esc(t), '<b>z<small>z</small></b>' if asleep else "")
    k = 0.92; w, h = round(pw * k), round(ph * k)
    css = """.fw{position:relative;width:1120px;height:610px;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 26px 60px rgba(15,23,42,.30),0 0 0 1px rgba(15,23,42,.12)}
.ts{height:46px;background:#DFE1E8;display:flex;align-items:flex-end;gap:3px;padding:0 12px 0 74px;position:relative}
.ts:before{content:"";position:absolute;left:16px;top:17px;width:11px;height:11px;border-radius:50%;background:#F26B5E;box-shadow:19px 0 #F5BD4F,38px 0 #5DC769}
.tab{height:36px;width:150px;border-radius:10px 10px 0 0;display:flex;align-items:center;gap:7px;padding:0 10px;font-size:12px;color:#2B2F3A;position:relative;overflow:hidden;white-space:nowrap}
.tab img{width:16px;height:16px;flex:none}.tab span{overflow:hidden;text-overflow:ellipsis;flex:1}.tab.act{background:#fff;font-weight:600}
.tab.zz span{padding-right:16px}.tab.zz{opacity:.55;filter:grayscale(.85)}.tab.zz b{font-size:12px;color:#312E81;position:absolute;right:8px;top:4px}.tab b small{font-size:9px}
.tl{height:44px;background:#fff;border-bottom:1px solid #E3E5EA;display:flex;align-items:center;padding:0 14px;gap:12px}
.ad{flex:1;height:28px;border-radius:14px;background:#F0F1F5;font-size:13px;color:#5B6470;display:flex;align-items:center;padding:0 16px}
.ext{width:28px;height:28px;border-radius:7px;background:#E0E4FF;display:flex;align-items:center;justify-content:center}.ext img{width:20px;height:20px;border-radius:5px}
.pg{position:absolute;left:0;top:90px;right:0;bottom:0;background:#F6F7F9}.pg .bl{height:14px;border-radius:7px;background:#DDE1E7;margin:16px 0}
.pop{position:absolute;right:20px;top:98px;width:@Wpx;height:@Hpx;border-radius:14px;box-shadow:0 20px 50px rgba(15,23,42,.35),0 0 0 1px rgba(15,23,42,.1);overflow:hidden}.pop img{width:100%;height:100%}""".replace("@W", str(w)).replace("@H", str(h))
    pg = '<div style="padding:30px 44px;width:640px"><div style="font:800 34px -apple-system,Arial;letter-spacing:-.02em;color:#1D2430">Quarterly planning notes</div>%s</div>' % "".join('<div class="bl" style="width:%d%%"></div>' % v for v in (96, 90, 98, 70, 94, 88, 97, 60, 92))
    return CSS_WRAP % css + '<div class="fw"><div class="ts">%s</div><div class="tl"><div class="ad">docs.acme-notes.example</div><div class="ext"><img src="%s"></div></div><div class="pg">%s</div><div class="pop"><img src="%s"></div></div>' % (th, icon, pg, popup_uri)
CSS_WRAP = "<style>%s</style>"

def menu_frame(article_uri):
    ic = lambda d: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#5B6470" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % d
    css = BROWSER_CSS + """.m{position:absolute;background:rgba(250,250,252,.98);border-radius:12px;box-shadow:0 18px 44px rgba(15,23,42,.38),0 0 0 1px rgba(15,23,42,.14);padding:6px;font-size:15px;color:#1D2430;font-family:-apple-system,Arial,sans-serif}
.m div{height:34px;display:flex;align-items:center;padding:0 12px;border-radius:7px;gap:10px;white-space:nowrap}.m hr{border:0;border-top:1px solid #DDE0E6;margin:5px 4px}.m .dim{color:#9AA1AC}
.m .hl{background:#312E81;color:#fff}.m .hl .ar{margin-left:auto;color:#fff}.m .ar{margin-left:auto;color:#6B7280;padding-left:26px}
.sub .ex{background:#EEF0FF;color:#312E81;font-weight:700}.sub .ex2{background:#E0E4FF;font-weight:700;color:#1E1B4B}.sub img{width:18px;height:18px;border-radius:5px}
.cur{position:absolute;width:0;height:0;border-left:11px solid #111;border-top:3px solid transparent;border-bottom:13px solid transparent;transform:rotate(-20deg)}"""
    main = ('<div class="m" style="left:520px;top:214px;width:250px"><div class="dim">Back</div><div class="dim">Forward</div><div>Reload</div><hr><div>Save as...</div><div>Print...</div><hr>'
            '<div class="hl"><img src="%s" style="width:18px;height:18px;border-radius:5px">Tab Nap<span class="ar">&#9656;</span></div><hr><div>View page source</div><div>Inspect</div></div>') % ICON_URI[0]
    sub = ('<div class="m sub" style="left:776px;top:376px;width:236px"><div class="ex2">Nap this tab now</div><div>Never nap this site</div><div>Nap all other tabs</div></div>')
    return css, '<div class="win" style="width:1120px;height:610px"><div class="tb"><i></i><i></i><i></i><span class="url">news.daybreak.example</span></div><div style="position:relative;width:1120px;height:572px"><img src="%s" style="width:1120px;height:572px"><div style="position:absolute;inset:0;background:rgba(15,23,42,.06)"></div>%s%s<svg style="position:absolute;left:512px;top:204px" width="22" height="30" viewBox="0 0 22 30"><path d="M2 2v22l5.500-5 4 9 4-1.800-4-8.700H19z" fill="#111" stroke="#fff" stroke-width="1.800" stroke-linejoin="round"/></svg></div></div>' % (article_uri, main, sub)
ICON_URI = [None]

def compose():
    sizes = json.load(open(os.path.join(RAW, "sizes.json"))); icon = data_uri(ICON); ICON_URI[0] = icon
    U = lambda n: data_uri(os.path.join(RAW, n)); c = Composer()
    try:
        R = lambda html, w, h, name, **k: c.render(html, w, h, os.path.join(OUT, name), **k)
        pw, ph = sizes["popup"]
        R(side(P, "Idle tabs nap. Memory comes back.", U("popup.png"), pw, ph, NAME, icon), 1280, 800, "screenshot-1-popup.png")
        R(wide(P, "Chrome's own tab sleeping. No tabs lost.", chrome_frame(U("popup.png"), pw, ph, icon), icon), 1280, 800, "screenshot-2-sleeping-tabs.png")
        # options: two columns of real sections
        def col(names, k, x0):
            y = 0; parts = []
            for n in names:
                w_, h_ = sizes["opt-" + n]; parts.append('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:16px;overflow:hidden;box-shadow:0 18px 40px rgba(10,10,60,.4)"><img src="%s" style="width:100%%;height:100%%"></div>' % (x0, y, w_ * k, h_ * k, U("opt-%s.png" % n))); y += h_ * k + 18
            return "".join(parts), y - 18
        k = 0.83; ca, ha = col(["threshold", "typing", "memory"], k, 0); cb, hb = col(["sites", "never", "pause"], k, 0)
        wA = sizes["opt-threshold"][0] * k; mx = max(ha, hb); off = (610 - mx) / 2
        two = ('<div style="width:1120px;height:610px;border-radius:26px;background:linear-gradient(160deg,#4B46B0,#211F5C);position:relative"><div style="position:absolute;left:44px;top:%dpx;width:%dpx">%s</div><div style="position:absolute;left:%dpx;top:%dpx;width:%dpx">%s</div></div>') % (
            (610 - ha) / 2, wA, ca, 44 + wA + 40, (610 - hb) / 2, wA, cb)
        R(wide(P, "Never naps a tab you were typing in.", two, icon), 1280, 800, "screenshot-3-protection.png")
        css, body = menu_frame(U("article.png"))
        R(wide(P, "Nap a tab right now, or never nap a site.", body, icon, css), 1280, 800, "screenshot-4-menu.png")
        qw, qh = sizes["popup-top"]
        R(privacy(P, "No accounts. No tracking. Nothing leaves your browser.", [("shield", "Native Chrome tab discarding"), ("ban", "No ads, no tracking, no accounts"), ("lock", "Your tabs never leave your browser")], U("popup-top.png"), qw, qh, icon, NAME), 1280, 800, "screenshot-5-privacy.png")
        R(promo_small(P, NAME, "Tab suspender & memory saver", "Idle tabs sleep. Nothing is lost.", icon), 440, 280, "promo-small-440x280.png")
        R(promo_marquee(P, NAME, "Tab suspender & memory saver", "Idle tabs sleep. Nothing is lost.", icon, U("popup.png"), pw, ph), 1400, 560, "promo-marquee-1400x560.png")
        R(store_icon(icon), 128, 128, "store-icon-128.png", transparent=True)
    finally:
        c.close()
    print("\n".join(finish_check(OUT)))

if __name__ == "__main__":
    a = sys.argv[1:] or ["capture", "compose"]
    if "capture" in a: capture()
    if "compose" in a: compose()
