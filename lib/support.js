// Shared renderer for the donation buttons (used by popup banner and options page). ES module.
import { DONATE_LINKS, DONATE_LINKS_USD, DONATE_AMOUNTS } from "../config.js";

const D = globalThis.TabNapDonation;

// Only Stripe Payment Link origins are ever opened (mirrored in tools/check_release.py).
export const ALLOWED_DONATION_ORIGINS = D.STRIPE_ORIGINS;

const selected = () => D.selectLinks(navigator.language, DONATE_LINKS, DONATE_LINKS_USD);

// True if the selected link set has at least one non-empty link.
export function hasDonateLinks() {
  return D.hasAnyLink(selected().links);
}

function openLink(url) {
  if (!url || !D.isStripeUrl(url)) { if (url) console.warn("Tab Nap: refusing to open a non-Stripe donation link"); return false; }
  chrome.tabs.create({ url });
  return true;
}

// Renders the amount buttons, the "pick your own amount" button and the small monthly text link into `container`.
// `note` receives the quantity hint. Returns the number of links rendered.
export function renderDonateButtons(container, note) {
  const sel = selected();
  const sym = sel.symbol;
  const have = D.availableKeys(sel.links);
  container.textContent = "";
  for (const key of ["small", "medium", "large"]) {
    if (!have.includes(key)) continue;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "donate" + (key === "medium" ? " emphasized" : "");
    b.textContent = sym + DONATE_AMOUNTS[key];
    b.addEventListener("click", () => openLink(sel.links[key]));
    container.appendChild(b);
  }
  if (have.includes("custom")) {
    const c = document.createElement("button");
    c.type = "button";
    c.className = "donate custom";
    c.textContent = "Pick your own amount";
    c.addEventListener("click", () => {
      if (openLink(sel.links.custom) && note) note.textContent = "On the next page, choose the quantity (" + sym + "1 each).";
    });
    container.appendChild(c);
  }
  if (typeof sel.links.monthly === "string" && sel.links.monthly) {
    const a = document.createElement("a");
    a.className = "monthly";
    a.href = "#";
    a.textContent = "Or support monthly (" + sym + "2/month)";
    a.addEventListener("click", (e) => { e.preventDefault(); openLink(sel.links.monthly); });
    container.appendChild(a);
  }
  return container.children.length;
}
