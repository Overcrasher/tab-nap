// Pure validators and sanitizers. Classic script on globalThis (extension pages, service worker, jsc tests).
(function (root) {
  "use strict";

  const THANKS_PAGE = "https://overcrasher.github.io/tab-nap/thanks.html";
  const SESSION_RE = /^cs_(live|test)_[A-Za-z0-9]{20,}$/;
  const THRESHOLDS = [5, 15, 30, 60, 120];
  const MIN_MB = 50, MAX_MB = 500;
  const MAX_WHITELIST = 200;
  const DEFAULT_SETTINGS = { thresholdMin: 30, protectPinned: true, avgMb: 150, whitelist: [], protectTyping: false };

  const isObj = (v) => !!v && typeof v === "object" && !Array.isArray(v);
  const isNum = (n) => typeof n === "number" && isFinite(n);

  // Minimal URL parser (jsc has no URL class; also keeps behaviour identical in every context).
  // Returns { protocol, hostname, origin, pathname } for scheme://host[:port]/path URLs, else null.
  function parseUrl(u) {
    if (typeof u !== "string" || u.length > 4096) return null;
    const m = /^([a-zA-Z][a-zA-Z0-9+.-]*):\/\/([^\/?#\s]*)([^?#]*)/.exec(u.trim());
    if (!m) return null;
    let auth = m[2];
    if (auth.indexOf("@") !== -1) return null; // userinfo: never trust
    const protocol = m[1].toLowerCase() + ":";
    const pm = /^(.*?)(?::(\d{1,5}))?$/.exec(auth);
    const hostname = pm[1].toLowerCase();
    const port = pm[2] || "";
    const origin = protocol + "//" + hostname + (port ? ":" + port : "");
    return { protocol, hostname, origin, pathname: m[3] || "/" };
  }
  // Hostname of an http(s) URL, else null.
  function hostOf(u) {
    const x = parseUrl(u);
    return x && (x.protocol === "http:" || x.protocol === "https:") && x.hostname ? x.hostname : null;
  }
  // Tab Nap only ever works on ordinary web pages.
  function isNappableUrl(u) {
    return hostOf(u) !== null;
  }
  function isThanksUrl(u) {
    const x = parseUrl(u);
    return !!x && x.origin + x.pathname === THANKS_PAGE;
  }
  const validSession = (s) => typeof s === "string" && SESSION_RE.test(s);

  const LABEL = "[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?";
  const DOMAIN_RE = new RegExp("^(?:" + LABEL + "\\.)+[a-z0-9-]{2,63}$");
  const IPV4_RE = /^\d{1,3}(?:\.\d{1,3}){3}$/;
  // A domain the user may whitelist: lowercase, no scheme/path/port, "www." stripped. Returns null if invalid.
  function normalizeDomain(input) {
    if (typeof input !== "string") return null;
    let s = input.trim().toLowerCase();
    if (!s || s.length > 300) return null;
    if (/[/:?#@\s]/.test(s)) {
      const h = hostOf(/^[a-z][a-z0-9+.-]*:\/\//.test(s) ? s : "https://" + s);
      if (!h) return null;
      s = h;
    }
    s = s.replace(/^www\./, "").replace(/\.$/, "");
    if (s.length < 3 || s.length > 253) return null;
    if (s === "localhost") return s;
    if (IPV4_RE.test(s)) return s.split(".").every((p) => Number(p) <= 255) ? s : null;
    return DOMAIN_RE.test(s) ? s : null;
  }
  const matchesDomain = (host, d) => host === d || host.endsWith("." + d);
  // Is `url` on a whitelisted domain (or a subdomain of one)?
  function isWhitelisted(url, whitelist) {
    const h = hostOf(url);
    if (!h || !Array.isArray(whitelist)) return false;
    const bare = h.replace(/^www\./, "");
    return whitelist.some((d) => typeof d === "string" && matchesDomain(bare, d));
  }
  // New whitelist with `input` added (deduplicated, capped). Returns the same list if invalid.
  function addDomain(list, input) {
    const d = normalizeDomain(input);
    const cur = Array.isArray(list) ? list : [];
    if (!d || cur.includes(d) || cur.length >= MAX_WHITELIST) return cur.slice();
    return cur.concat(d);
  }
  const removeDomain = (list, d) => (Array.isArray(list) ? list : []).filter((x) => x !== d);

  function sanitizeWhitelist(list) {
    const out = [];
    if (!Array.isArray(list)) return out;
    for (const v of list) {
      const d = typeof v === "string" ? normalizeDomain(v) : null;
      if (d && !out.includes(d)) out.push(d);
      if (out.length >= MAX_WHITELIST) break;
    }
    return out;
  }
  function sanitizeSettings(s) {
    const d = DEFAULT_SETTINGS;
    s = isObj(s) ? s : {};
    return {
      thresholdMin: THRESHOLDS.includes(s.thresholdMin) ? s.thresholdMin : d.thresholdMin,
      protectPinned: typeof s.protectPinned === "boolean" ? s.protectPinned : d.protectPinned,
      avgMb: isNum(s.avgMb) ? Math.min(MAX_MB, Math.max(MIN_MB, Math.round(s.avgMb))) : d.avgMb,
      whitelist: sanitizeWhitelist(s.whitelist),
      protectTyping: s.protectTyping === true,
    };
  }
  // pausedUntil: 0 = not paused, -1 = paused until turned back on, otherwise a timestamp in ms.
  function sanitizePausedUntil(v) {
    return v === -1 ? -1 : isNum(v) && v > 0 ? v : 0;
  }
  const isPaused = (pausedUntil, now) => pausedUntil === -1 || (isNum(pausedUntil) && pausedUntil > now);
  const sanitizeCount = (n) => (isNum(n) && n > 0 ? n : 0);
  // List of tab ids (positive integers), deduplicated.
  function sanitizeIds(list) {
    const out = [];
    if (!Array.isArray(list)) return out;
    for (const v of list) if (Number.isInteger(v) && v >= 0 && !out.includes(v)) out.push(v);
    return out;
  }
  // { "<tabId>": number } with valid ids only.
  function sanitizeTimes(m) {
    const out = {};
    if (!isObj(m)) return out;
    for (const k of Object.keys(m)) if (/^\d{1,10}$/.test(k) && isNum(m[k]) && m[k] >= 0) out[k] = m[k];
    return out;
  }
  function sanitizeFlags(m) {
    const out = {};
    if (!isObj(m)) return out;
    for (const k of Object.keys(m)) if (/^\d{1,10}$/.test(k) && m[k] === true) out[k] = true;
    return out;
  }
  // The only message a typing detector may send.
  const isDirtyMessage = (m) => isObj(m) && m.type === "dirty" && m.dirty === true;

  root.TabNapValidate = {
    THANKS_PAGE, THRESHOLDS, MIN_MB, MAX_MB, MAX_WHITELIST, DEFAULT_SETTINGS,
    parseUrl, hostOf, isNappableUrl, isThanksUrl, validSession, normalizeDomain, matchesDomain, isWhitelisted,
    addDomain, removeDomain, sanitizeWhitelist, sanitizeSettings, sanitizePausedUntil, isPaused,
    sanitizeCount, sanitizeIds, sanitizeTimes, sanitizeFlags, isDirtyMessage,
  };
})(globalThis);
