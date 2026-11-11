// Service worker (module). Puts idle tabs to sleep with chrome.tabs.discard() ONLY (never rewrites a tab's URL).
import { getAll, getSession, mutate } from "./lib/store.js";

const V = globalThis.TabNapValidate;
const L = globalThis.TabNapLogic;
const FAIL = { ok: false };
const ALARM = "tabnap-check";
const SCRIPT_ID = "tabnap-typing";
const ALL_URLS = { origins: ["<all_urls>"] };

// Content scripts must not read or write storage: only trusted extension pages and this worker.
async function lockStorage() {
  for (const area of [chrome.storage.local, chrome.storage.session]) {
    try { await area.setAccessLevel({ accessLevel: "TRUSTED_CONTEXTS" }); }
    catch (e) { console.warn("setAccessLevel failed", e); }
  }
}
lockStorage();

// ---- small helpers ----
let flashTimer;
function flash(text) {
  try {
    chrome.action.setBadgeBackgroundColor({ color: "#312E81" });
    chrome.action.setBadgeText({ text });
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => chrome.action.setBadgeText({ text: "" }), 2500);
  } catch (e) { /* ignore */ }
}

function ensureAlarm() {
  chrome.alarms.get(ALARM).then((a) => { if (!a) chrome.alarms.create(ALARM, { periodInMinutes: 1 }); }).catch(() => {});
}
ensureAlarm();

// ---- activity tracking (chrome.storage.session, survives worker restarts) ----
async function setSession(patch) { await chrome.storage.session.set(patch); }

function touch(tabId, now) {
  return mutate(async () => {
    const { lastActive } = await getSession();
    lastActive[tabId] = now;
    await setSession({ lastActive });
  });
}

chrome.tabs.onActivated.addListener(({ tabId, windowId }) => {
  const now = Date.now();
  mutate(async () => {
    const s = await getSession();
    const prev = s.activeByWindow[windowId];
    s.lastActive[tabId] = now;
    if (typeof prev === "number" && prev !== tabId) s.lastActive[prev] = now; // it was in use until just now
    s.activeByWindow[windowId] = tabId;
    await setSession({ lastActive: s.lastActive, activeByWindow: s.activeByWindow });
  });
});

chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;
  try {
    const [t] = await chrome.tabs.query({ active: true, windowId });
    if (t && t.id != null) touch(t.id, Date.now());
  } catch (e) { /* window gone */ }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  const now = Date.now();
  mutate(async () => {
    const s = await getSession();
    let dirtyChanged = false, nappedChanged = false, activeChanged = false;
    // A new page load starts clean: forget unsaved-typing flags.
    if (changeInfo.status === "loading" && s.dirty[tabId]) { delete s.dirty[tabId]; dirtyChanged = true; }
    // Woken up (activated or reloaded): no longer napping.
    if (changeInfo.discarded === false && s.napped.includes(tabId)) { s.napped = s.napped.filter((x) => x !== tabId); nappedChanged = true; }
    if (changeInfo.status === "complete" || changeInfo.discarded === false || changeInfo.audible !== undefined) { s.lastActive[tabId] = now; activeChanged = true; }
    const patch = {};
    if (dirtyChanged) patch.dirty = s.dirty;
    if (nappedChanged) patch.napped = s.napped;
    if (activeChanged) patch.lastActive = s.lastActive;
    if (Object.keys(patch).length) await setSession(patch);
  });
});

function forget(tabId, replacedBy) {
  mutate(async () => {
    const s = await getSession();
    const had = (m) => Object.prototype.hasOwnProperty.call(m, tabId);
    if (replacedBy != null) {
      if (had(s.lastActive)) s.lastActive[replacedBy] = s.lastActive[tabId];
      if (had(s.dirty)) s.dirty[replacedBy] = true;
      if (s.napped.includes(tabId)) s.napped.push(replacedBy);
    }
    delete s.lastActive[tabId]; delete s.dirty[tabId];
    s.napped = s.napped.filter((x) => x !== tabId);
    await setSession({ lastActive: s.lastActive, dirty: s.dirty, napped: s.napped });
  });
}
chrome.tabs.onRemoved.addListener((tabId) => forget(tabId));
chrome.tabs.onReplaced.addListener((added, removed) => forget(removed, added));

// ---- napping ----
// Discards each tab natively; returns the ids that are now napping. The caller holds the mutate() lock.
async function discardTabs(ids) {
  const done = [];
  for (const id of ids) {
    try {
      const t = await chrome.tabs.discard(id);
      if (t && t.discarded) done.push(typeof t.id === "number" ? t.id : id);
    } catch (e) { /* cannot be discarded right now: skip quietly */ }
  }
  return done;
}

function ctxFrom(settings, session, now, extra) {
  return Object.assign({ now, thresholdMin: settings.thresholdMin, protectPinned: settings.protectPinned,
    whitelist: settings.whitelist, dirty: session.dirty, lastActive: session.lastActive }, extra || {});
}

// The minute check. `now` is a parameter so tests can fast-forward time.
async function runCheck(now) {
  now = typeof now === "number" ? now : Date.now();
  return mutate(async () => {
    const st = await getAll();
    const s = await getSession();
    const tabs = await chrome.tabs.query({});
    const alive = new Set(tabs.map((t) => t.id));
    const sleeping = new Set(tabs.filter((t) => t.discarded).map((t) => t.id));
    // Keep only tabs that are still alive; a napped tab that woke up or closed stops counting.
    let napped = s.napped.filter((id) => sleeping.has(id));
    for (const id of Object.keys(s.lastActive)) if (!alive.has(Number(id))) delete s.lastActive[id];
    for (const id of Object.keys(s.dirty)) if (!alive.has(Number(id))) delete s.dirty[id];
    for (const t of tabs) {
      if (t.active || (!s.lastActive[t.id] && !t.lastAccessed)) s.lastActive[t.id] = now;
    }
    let napCount = st.napCount, pausedUntil = st.pausedUntil;
    if (pausedUntil > 0 && pausedUntil <= now) { pausedUntil = 0; await chrome.storage.local.set({ pausedUntil: 0 }); }
    let napped_now = [];
    if (!V.isPaused(pausedUntil, now)) {
      const ids = L.eligibleTabs(tabs, ctxFrom(st.settings, s, now)).map((t) => t.id);
      napped_now = await discardTabs(ids);
      for (const id of napped_now) if (!napped.includes(id)) napped.push(id);
      napCount += napped_now.length;
    }
    const tabHours = L.addTabHours(st.tabHours, napped.length);
    await chrome.storage.local.set({ napCount, tabHours });
    await setSession({ napped, lastActive: s.lastActive, dirty: s.dirty });
    return { napped: napped_now, nappedTotal: napped.length };
  });
}

// Explicit nap of specific tabs (context menu). Records them like the minute check does.
async function napIds(ids) {
  return mutate(async () => {
    const st = await getAll();
    const s = await getSession();
    const done = await discardTabs(ids);
    for (const id of done) if (!s.napped.includes(id)) s.napped.push(id);
    await chrome.storage.local.set({ napCount: st.napCount + done.length });
    await setSession({ napped: s.napped });
    return done;
  });
}

// "Nap this tab now": ignores the idle threshold but keeps every NEVER rule. A tab you are looking at
// cannot be discarded, so we first switch to another awake tab in the same window; if there is none, we do nothing.
async function napThisTab(tab) {
  if (!tab || typeof tab.id !== "number") return false;
  const [st, s] = await Promise.all([getAll(), getSession()]);
  const fresh = await chrome.tabs.get(tab.id);
  const ctx = ctxFrom(st.settings, s, Date.now(), { ignoreThreshold: true });
  if (L.whyNot(Object.assign({}, fresh, { active: false }), ctx)) { flash("!"); return false; }
  if (fresh.active) {
    const others = (await chrome.tabs.query({ windowId: fresh.windowId }))
      .filter((t) => t.id !== fresh.id && !t.discarded)
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));
    if (!others.length) { flash("!"); return false; }
    await chrome.tabs.update(others[0].id, { active: true });
  }
  const done = await napIds([fresh.id]);
  if (!done.length) flash("!");
  return done.length > 0;
}

// "Nap all other tabs" in the clicked tab's window, respecting all NEVER rules.
async function napOthers(tab) {
  if (!tab || typeof tab.windowId !== "number") return [];
  const [st, s] = await Promise.all([getAll(), getSession()]);
  const ctx = ctxFrom(st.settings, s, Date.now(), { ignoreThreshold: true });
  const tabs = await chrome.tabs.query({ windowId: tab.windowId });
  const ids = L.eligibleTabs(tabs.filter((t) => t.id !== tab.id), ctx).map((t) => t.id);
  const done = await napIds(ids);
  flash(done.length ? String(done.length) : "0");
  return done;
}

// "Never nap this site": adds the tab's domain to the whitelist.
async function neverNapSite(tab) {
  const host = tab && typeof tab.url === "string" ? V.hostOf(tab.url) : null;
  const domain = host ? V.normalizeDomain(host) : null;
  if (!domain) { flash("!"); return false; }
  await mutate(async () => {
    const { settings } = await getAll();
    settings.whitelist = V.addDomain(settings.whitelist, domain);
    await chrome.storage.local.set({ settings });
  });
  flash("✓");
  return true;
}

const MENU = { "nap-now": napThisTab, "nap-others": napOthers, "never-site": neverNapSite };
async function handleMenu(menuItemId, tab) {
  const fn = Object.prototype.hasOwnProperty.call(MENU, menuItemId) ? MENU[menuItemId] : null;
  if (!fn || !tab) return false;
  try { return await fn(tab); } catch (e) { console.warn("menu action failed", e); return false; }
}
chrome.contextMenus.onClicked.addListener((info, tab) => { handleMenu(info.menuItemId, tab); });

function createMenus() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: "nap-now", title: "Nap this tab now", contexts: ["page"] });
    chrome.contextMenus.create({ id: "never-site", title: "Never nap this site", contexts: ["page"] });
    chrome.contextMenus.create({ id: "nap-others", title: "Nap all other tabs", contexts: ["page"] });
  });
}

// ---- unsaved-typing protection (optional host permission + registered content script) ----
const hasHostPermission = () => chrome.permissions.contains(ALL_URLS).catch(() => false);

async function registerTyping() {
  const existing = await chrome.scripting.getRegisteredContentScripts({ ids: [SCRIPT_ID] }).catch(() => []);
  if (existing.length) return;
  await chrome.scripting.registerContentScripts([{
    id: SCRIPT_ID, matches: ["<all_urls>"], js: ["typing.js"], allFrames: true,
    runAt: "document_idle", persistAcrossSessions: true,
  }]);
}
async function unregisterTyping() {
  await chrome.scripting.unregisterContentScripts({ ids: [SCRIPT_ID] }).catch(() => {});
}
// Registered scripts only run on new navigations, so also inject into pages that are already open.
async function injectIntoOpenTabs() {
  const tabs = await chrome.tabs.query({});
  for (const t of tabs) {
    if (t.id == null || t.discarded || !V.isNappableUrl(t.url)) continue;
    chrome.scripting.executeScript({ target: { tabId: t.id, allFrames: true }, files: ["typing.js"] }).catch(() => {});
  }
}
async function setProtection(enabled) {
  if (enabled) {
    if (!(await hasHostPermission())) return false;
    await registerTyping();
    await mutate(async () => {
      const { settings } = await getAll();
      settings.protectTyping = true;
      await chrome.storage.local.set({ settings });
    });
    await injectIntoOpenTabs();
    return true;
  }
  await unregisterTyping();
  await mutate(async () => {
    const { settings } = await getAll();
    settings.protectTyping = false;
    await chrome.storage.local.set({ settings });
    await setSession({ dirty: {} });
  });
  await chrome.permissions.remove(ALL_URLS).catch(() => {});
  return true;
}
// Make the stored switch, the permission and the registered script agree (e.g. after the user revokes the permission).
async function reconcileProtection() {
  const { settings } = await getAll();
  const perm = await hasHostPermission();
  if (settings.protectTyping && perm) { await registerTyping(); return; }
  await unregisterTyping();
  if (settings.protectTyping && !perm) {
    await mutate(async () => {
      const cur = await getAll();
      cur.settings.protectTyping = false;
      await chrome.storage.local.set({ settings: cur.settings });
    });
  }
}
chrome.permissions.onRemoved.addListener(() => { reconcileProtection(); });

// ---- lifecycle ----
chrome.runtime.onInstalled.addListener((details) => {
  lockStorage(); ensureAlarm(); createMenus(); reconcileProtection();
  // Welcome page: first install only, never on update or reload.
  if (details && details.reason === "install") chrome.tabs.create({ url: chrome.runtime.getURL("welcome.html") });
});
chrome.runtime.onStartup.addListener(() => { lockStorage(); ensureAlarm(); reconcileProtection(); });
chrome.alarms.onAlarm.addListener((alarm) => { if (alarm.name === ALARM) runCheck(Date.now()).catch((e) => console.warn("check failed", e)); });

// Debug hook for the end-to-end tests. Lives only in the worker's own global scope: web pages and content
// scripts cannot reach it, only a DevTools/CDP session attached to the worker.
globalThis.__tabNapTest = { runCheck, handleMenu, reconcileProtection, napThisTab, napOthers, neverNapSite };

// ---- messages ----
// Sender classes: "extension" (our own pages; the options page lives in a tab, so sender.tab may be set) and "content"
// (content scripts: sender.url is the web page, never our origin).
function classify(sender) {
  if (!sender || sender.id !== chrome.runtime.id) return null;
  if (typeof sender.url === "string" && sender.url.startsWith("chrome-extension://" + chrome.runtime.id + "/")) {
    return { kind: "extension" };
  }
  if (sender.tab && typeof sender.tab.url === "string") return { kind: "content", tabId: sender.tab.id, tabUrl: sender.tab.url };
  return null;
}

async function handleExtension(msg) {
  if (msg.type === "setProtection" && typeof msg.enabled === "boolean") return { ok: await setProtection(msg.enabled) };
  return FAIL;
}

async function handleContent(msg, ctx) {
  if (msg.type === "supporter") {
    // Cosmetic flag, honour system: only from the real thank-you page with a Stripe-shaped session id.
    if (!V.isThanksUrl(ctx.tabUrl) || !V.validSession(msg.sessionId)) return FAIL;
    await chrome.storage.local.set({ supporter: true });
    return { ok: true };
  }
  if (msg.type === "dirty") {
    // Only ordinary web pages, only for the sender's own tab (the id comes from the sender, never the message).
    if (!V.isDirtyMessage(msg) || !Number.isInteger(ctx.tabId) || !V.isNappableUrl(ctx.tabUrl)) return FAIL;
    if (!(await hasHostPermission())) return FAIL;
    const { settings } = await getAll();
    if (!settings.protectTyping) return FAIL;
    await mutate(async () => {
      const { dirty } = await getSession();
      dirty[ctx.tabId] = true;
      await setSession({ dirty });
    });
    return { ok: true };
  }
  return FAIL;
}

async function handle(msg, sender) {
  const ctx = classify(sender);
  if (!ctx || !msg || typeof msg !== "object" || typeof msg.type !== "string") return FAIL;
  return ctx.kind === "extension" ? handleExtension(msg) : handleContent(msg, ctx);
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  handle(msg, sender).then(sendResponse).catch(() => sendResponse(FAIL));
  return true;
});
