// Pure napping logic: which tabs may be put to sleep, and the numbers shown to the user.
// Classic script on globalThis (service worker, popup, options, jsc tests). Needs lib/validate.js first.
(function (root) {
  "use strict";
  const V = root.TabNapValidate;
  const MIN_MS = 60 * 1000;

  // Last known activity of a tab: the newest of our own record and Chrome's lastAccessed. 0 = unknown.
  function lastActivity(tab, lastActive) {
    const own = lastActive && typeof lastActive[tab.id] === "number" ? lastActive[tab.id] : 0;
    const acc = typeof tab.lastAccessed === "number" ? tab.lastAccessed : 0;
    return Math.max(own, acc);
  }

  // Why a tab must NOT be napped, or null if it may. ctx:
  //   now, thresholdMin, protectPinned, whitelist[], dirty{id:true}, lastActive{id:ms}, ignoreThreshold (explicit user action)
  // Order matters only for the reported reason; every rule is a hard NEVER.
  function whyNot(tab, ctx) {
    if (!tab || typeof tab.id !== "number" || tab.id < 0) return "no-id";
    if (tab.active) return "active";
    if (tab.discarded) return "discarded";
    if (tab.audible) return "audible";
    if (tab.autoDiscardable === false) return "not-discardable";
    if (tab.pinned && ctx.protectPinned) return "pinned";
    if (tab.status === "loading") return "loading";
    const url = tab.url || tab.pendingUrl || "";
    if (!V.isNappableUrl(url)) return "unsupported-url";
    if (V.isWhitelisted(url, ctx.whitelist)) return "whitelisted";
    if (ctx.dirty && ctx.dirty[tab.id]) return "unsaved-typing";
    if (!ctx.ignoreThreshold) {
      const last = lastActivity(tab, ctx.lastActive);
      if (!last) return "unknown-activity";
      if (ctx.now - last < ctx.thresholdMin * MIN_MS) return "recent";
    }
    return null;
  }
  const eligibleTabs = (tabs, ctx) => (tabs || []).filter((t) => whyNot(t, ctx) === null);

  // ---- numbers ----
  const estimateMb = (count, avgMb) => Math.max(0, count) * avgMb;
  const group = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  // 2250 -> "2.3 GB", 450 -> "450 MB", 0 -> "0 MB"
  function formatMemory(mb) {
    if (!(mb > 0)) return "0 MB";
    if (mb < 1000) return Math.round(mb) + " MB";
    return (mb / 1000).toFixed(1) + " GB";
  }
  // Tab-hours: one decimal below 10, whole numbers with thousands separators above.
  function formatHours(h) {
    if (!(h > 0)) return "0";
    if (h < 10) return (Math.floor(h * 10 + 1e-9) / 10).toFixed(1);
    return group(Math.floor(h));
  }
  const formatCount = (n) => group(Math.max(0, Math.floor(n) || 0));
  // Each minute check adds (tabs napped now) / 60 tab-hours.
  const addTabHours = (total, nappedNow) => total + Math.max(0, nappedNow) / 60;
  const wholeHours = (h) => Math.floor((h > 0 ? h : 0) + 1e-9);

  // Clamp helper for the "average MB per tab" setting.
  const clampMb = (n) => (typeof n === "number" && isFinite(n) ? Math.min(V.MAX_MB, Math.max(V.MIN_MB, Math.round(n))) : V.DEFAULT_SETTINGS.avgMb);

  function thresholdLabel(min) {
    return min < 60 ? min + " minutes" : min === 60 ? "1 hour" : (min / 60) + " hours";
  }

  root.TabNapLogic = {
    MIN_MS, lastActivity, whyNot, eligibleTabs, estimateMb, formatMemory, formatHours, formatCount,
    addTabHours, wholeHours, clampMb, thresholdLabel,
  };
})(globalThis);
