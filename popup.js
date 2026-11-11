import { getAll, getSession, PAUSE_MS, PAUSE_FOREVER } from "./lib/store.js";
import { renderDonateButtons, hasDonateLinks } from "./lib/support.js";

const G = globalThis.TabNapGrowth;
const L = globalThis.TabNapLogic;
const D = globalThis.TabNapDonation;
const $ = (id) => document.getElementById(id);
let state, napped = [];

function faviconUrl(pageUrl) {
  const u = new URL(chrome.runtime.getURL("/_favicon/"));
  u.searchParams.set("pageUrl", pageUrl);
  u.searchParams.set("size", "16");
  return u.toString();
}

// Tabs that Tab Nap put to sleep and that are still asleep.
async function loadNapped() {
  const [sess, sleeping] = await Promise.all([getSession(), chrome.tabs.query({ discarded: true })]);
  const ids = new Set(sess.napped);
  return sleeping.filter((t) => ids.has(t.id));
}

function renderHero() {
  const n = napped.length;
  $("count").textContent = n + (n === 1 ? " tab" : " tabs");
  $("memory").textContent = "≈ " + L.formatMemory(L.estimateMb(n, state.settings.avgMb)) + " saved (estimated)";
  $("hours").textContent = L.formatHours(state.tabHours);
  $("naps").textContent = L.formatCount(state.napCount);
  $("share").hidden = !(state.napCount > 0);
}

function hostOf(url) { return (globalThis.TabNapValidate.hostOf(url) || "").replace(/^www\./, ""); }

function renderList() {
  const list = $("list");
  list.textContent = "";
  $("empty").hidden = napped.length > 0;
  for (const t of napped) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "tab";
    btn.title = "Wake this tab";
    btn.dataset.tabId = String(t.id);
    const img = document.createElement("img");
    img.className = "fav"; img.width = 16; img.height = 16; img.alt = "";
    img.src = faviconUrl(t.url || t.pendingUrl || "");
    const text = document.createElement("span"); text.className = "tt";
    const title = document.createElement("span"); title.className = "title"; title.textContent = t.title || t.url || "Tab";
    const host = document.createElement("span"); host.className = "host"; host.textContent = hostOf(t.url || "");
    text.append(title, host);
    btn.append(img, text);
    btn.addEventListener("click", async () => {
      // Chrome reloads a discarded tab when it is activated.
      await chrome.tabs.update(t.id, { active: true });
      try { await chrome.windows.update(t.windowId, { focused: true }); } catch (e) { /* ignore */ }
      window.close();
    });
    li.appendChild(btn);
    list.appendChild(li);
  }
}

function renderPause() {
  const paused = state.pausedUntil === PAUSE_FOREVER || state.pausedUntil > Date.now();
  $("pause").checked = paused;
  let msg = "";
  if (state.pausedUntil === PAUSE_FOREVER) msg = "Paused until you turn it back on.";
  else if (paused) msg = "Paused, " + Math.ceil((state.pausedUntil - Date.now()) / 60000) + " min left.";
  $("pauseLeft").textContent = msg;
  $("pause1h").hidden = paused;
}

async function refresh() {
  state = await getAll();
  napped = await loadNapped();
  renderHero(); renderList(); renderPause();
  $("supporter").hidden = !state.supporter;
}

async function maybeShowBanner() {
  if (state.supporter) return false;
  const now = Date.now();
  const milestone = D.pickAsk(Object.assign({}, state.donation, { supporter: state.supporter }), state.tabHours, now);
  if (!milestone) return false;
  // Unconfigured build: don't show the banner and don't burn the milestone.
  if (!hasDonateLinks()) return false;
  // Persist right away: showing the banner is the ask (max one per milestone).
  const next = D.applyAsk(state.donation, milestone, now);
  state.donation = next;
  await chrome.storage.local.set({ donation: next });
  $("banner-text").textContent = D.bannerText(milestone, L.formatCount);
  renderDonateButtons($("banner-buttons"), $("banner-note"));
  $("banner").hidden = false;
  return true;
}

// Rating card: once ever, after the 50th nap, never in the same render as the donation banner.
async function maybeShowRating(bannerShown) {
  if (bannerShown || !G.shouldAskRating(state.rating, state.napCount, G.RATING_THRESHOLD)) return;
  state.rating = { shown: true, at: Date.now() };
  await chrome.storage.local.set({ rating: state.rating });
  $("rating").hidden = false;
}

let shareTimer;
async function onShare() {
  const btn = $("share");
  const mem = napped.length ? L.formatMemory(L.estimateMb(napped.length, state.settings.avgMb)) : null;
  const text = G.shareText(L.formatHours(state.tabHours), mem, G.shareUrl(chrome.runtime.id));
  let label = "Copied!";
  try { await navigator.clipboard.writeText(text); } catch (e) { label = "Copy failed"; }
  btn.textContent = label;
  clearTimeout(shareTimer);
  shareTimer = setTimeout(() => { btn.textContent = "Share"; }, 1500);
}

async function setPause(value) {
  state.pausedUntil = value;
  await chrome.storage.local.set({ pausedUntil: value });
  renderPause();
}

async function init() {
  await refresh();
  const bannerShown = await maybeShowBanner();
  await maybeShowRating(bannerShown);
  $("share").addEventListener("click", onShare);
  $("rating-rate").addEventListener("click", () => { chrome.tabs.create({ url: G.reviewsUrl(chrome.runtime.id) }); $("rating").hidden = true; });
  $("rating-no").addEventListener("click", () => { $("rating").hidden = true; });
  $("banner-close").addEventListener("click", () => { $("banner").hidden = true; });
  $("banner-never").addEventListener("click", async (e) => {
    e.preventDefault();
    const donation = Object.assign({}, state.donation, { dontAskAgain: true });
    state.donation = donation;
    await chrome.storage.local.set({ donation });
    $("banner").hidden = true;
  });
  $("pause").addEventListener("change", (e) => setPause(e.target.checked ? PAUSE_FOREVER : 0));
  $("pause1h").addEventListener("click", () => setPause(Date.now() + PAUSE_MS));
  $("optionsLink").addEventListener("click", (e) => { e.preventDefault(); chrome.runtime.openOptionsPage(); });
  setInterval(refresh, 15000);
}
init();
