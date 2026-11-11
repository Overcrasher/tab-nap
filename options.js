import { getAll, PAUSE_FOREVER } from "./lib/store.js";
import { renderDonateButtons, hasDonateLinks } from "./lib/support.js";
import { enableProtection, disableProtection, hasPermission } from "./lib/protect.js";

const G = globalThis.TabNapGrowth;
const V = globalThis.TabNapValidate;
const L = globalThis.TabNapLogic;
const $ = (id) => document.getElementById(id);
let settings;
let savedTimer;

async function save(whitelistChanged) {
  // Re-read so a change made elsewhere (e.g. the context menu adding a site) is not overwritten.
  const cur = (await getAll()).settings;
  settings = V.sanitizeSettings(Object.assign({}, settings, { protectTyping: cur.protectTyping, whitelist: whitelistChanged ? settings.whitelist : cur.whitelist }));
  await chrome.storage.local.set({ settings });
  renderWhitelist();
  const el = $("saved");
  el.classList.add("show");
  clearTimeout(savedTimer);
  savedTimer = setTimeout(() => el.classList.remove("show"), 1200);
}

function renderWhitelist() {
  const ul = $("wl-list");
  ul.textContent = "";
  $("wl-empty").hidden = settings.whitelist.length > 0;
  for (const d of settings.whitelist) {
    const li = document.createElement("li");
    li.append(document.createTextNode(d));
    const b = document.createElement("button");
    b.type = "button"; b.setAttribute("aria-label", "Remove " + d); b.title = "Remove"; b.textContent = "×";
    b.addEventListener("click", async () => {
      settings.whitelist = V.removeDomain((await getAll()).settings.whitelist, d);
      await save(true); renderWhitelist();
    });
    li.appendChild(b);
    ul.appendChild(li);
  }
}

function renderPause(pausedUntil) {
  const paused = pausedUntil === PAUSE_FOREVER || pausedUntil > Date.now();
  $("pause").checked = paused;
  $("pause-sub").textContent = pausedUntil === PAUSE_FOREVER ? "Paused until you turn it back on."
    : paused ? "Paused for about " + Math.ceil((pausedUntil - Date.now()) / 60000) + " more minutes." : "";
}

async function init() {
  const state = await getAll();
  settings = state.settings;

  for (const r of document.querySelectorAll("input[name=threshold]")) {
    r.checked = Number(r.value) === settings.thresholdMin;
    r.addEventListener("change", () => { if (r.checked) { settings.thresholdMin = Number(r.value); save(); } });
  }
  $("protectPinned").checked = settings.protectPinned;
  $("protectPinned").addEventListener("change", (e) => { settings.protectPinned = e.target.checked; save(); });

  $("avgMb").value = settings.avgMb;
  $("avgMb").addEventListener("change", (e) => {
    settings.avgMb = L.clampMb(parseFloat(e.target.value));
    e.target.value = settings.avgMb;
    save();
  });

  renderWhitelist();
  $("wl-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const d = V.normalizeDomain($("wl-input").value);
    if (!d) { $("wl-err").textContent = "That does not look like a domain. Try something like example.com."; return; }
    $("wl-err").textContent = "";
    if (settings.whitelist.length >= V.MAX_WHITELIST) { $("wl-err").textContent = "The list is full (" + V.MAX_WHITELIST + " sites)."; return; }
    settings.whitelist = V.addDomain((await getAll()).settings.whitelist, d);
    $("wl-input").value = "";
    await save(true); renderWhitelist();
  });

  // Typing protection: the switch shows reality (setting AND permission).
  const on = settings.protectTyping && await hasPermission();
  $("protectTyping").checked = on;
  $("protectTyping").addEventListener("change", async (e) => {
    const box = e.target, msg = $("protect-msg");
    if (box.checked) {
      const ok = await enableProtection(); // request must start inside this event
      box.checked = ok;
      msg.textContent = ok ? "Protection is on." : "Permission was not granted, so protection stays off.";
    } else {
      await disableProtection();
      msg.textContent = "Protection is off.";
    }
  });

  renderPause(state.pausedUntil);
  $("pause").addEventListener("change", async (e) => {
    const v = e.target.checked ? PAUSE_FOREVER : 0;
    await chrome.storage.local.set({ pausedUntil: v });
    renderPause(v);
  });

  // Support section
  $("thanks").hidden = !state.supporter;
  const shown = renderDonateButtons($("donate"), $("donate-note"));
  if (!shown) $("donate-note").textContent = "Donation links not configured yet";
  const allowed = G.allowedUrls(chrome.runtime.id);
  const open = (url) => { if (allowed.includes(url)) chrome.tabs.create({ url }); };
  const rate = $("rate-link");
  rate.href = G.reviewsUrl(chrome.runtime.id);
  rate.addEventListener("click", (e) => { e.preventDefault(); open(rate.href); });
  const sib = $("siblings");
  G.SIBLINGS.forEach((s, i) => {
    if (i) sib.append(document.createTextNode(", "));
    const a = document.createElement("a");
    a.href = s.url; a.textContent = s.name;
    a.addEventListener("click", (e) => { e.preventDefault(); open(s.url); });
    sib.append(a, document.createTextNode(" (" + s.blurb + ")"));
  });
}
init();
