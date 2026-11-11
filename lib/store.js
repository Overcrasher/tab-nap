// Shared storage helpers (ES module, used by background, popup, options, welcome).
import "./validate.js"; // classic scripts: define globalThis.TabNap*
import "./nap.js";
import "./growth.js";
import "./donation.js";
const V = globalThis.TabNapValidate;
const G = globalThis.TabNapGrowth;

export const DEFAULT_SETTINGS = V.DEFAULT_SETTINGS;
export const DEFAULT_DONATION = { asked: [], lastAskAt: 0, dontAskAgain: false };
export const PAUSE_MS = 60 * 60 * 1000;
export const PAUSE_FOREVER = -1;

// Durable data (chrome.storage.local), sanitized, with defaults applied (fresh install safe).
export async function getAll() {
  const d = await chrome.storage.local.get(["settings", "pausedUntil", "napCount", "tabHours", "donation", "supporter", "rating"]);
  return {
    settings: V.sanitizeSettings(d.settings),
    pausedUntil: V.sanitizePausedUntil(d.pausedUntil),
    napCount: V.sanitizeCount(d.napCount),
    tabHours: V.sanitizeCount(d.tabHours),
    donation: Object.assign({}, DEFAULT_DONATION, d.donation && typeof d.donation === "object" ? d.donation : {}),
    supporter: d.supporter === true,
    rating: G.sanitizeRating(d.rating),
  };
}

// Per-browser-session data (chrome.storage.session): tab activity, napped tab ids, unsaved-typing flags.
export async function getSession() {
  const d = await chrome.storage.session.get(["lastActive", "napped", "dirty", "activeByWindow"]);
  return {
    lastActive: V.sanitizeTimes(d.lastActive),
    napped: V.sanitizeIds(d.napped),
    dirty: V.sanitizeFlags(d.dirty),
    activeByWindow: V.sanitizeTimes(d.activeByWindow),
  };
}

// Serializes read-modify-write operations within one context.
let chain = Promise.resolve();
export function mutate(fn) {
  const p = chain.then(fn);
  chain = p.catch(() => {});
  return p;
}
