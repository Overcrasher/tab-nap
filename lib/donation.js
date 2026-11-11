// Pure donation logic. Classic script on globalThis (popup/options <script> tag + jsc tests).
(function (root) {
  "use strict";

  const MILESTONES = [100, 1000, 10000]; // lifetime tab-hours napped
  const MIN_GAP_MS = 30 * 24 * 60 * 60 * 1000;
  const USD_LOCALES = ["en-US", "es-US", "en-PR", "es-PR"];
  const KEYS = ["small", "medium", "large", "custom"];

  // state: { supporter, dontAskAgain, asked: number[], lastAskAt: number|0 }
  // Returns the milestone to ask about, or null.
  function pickAsk(state, hours, now) {
    state = state || {};
    if (state.supporter || state.dontAskAgain) return null;
    const asked = state.asked || [];
    if (state.lastAskAt && now - state.lastAskAt < MIN_GAP_MS) return null;
    let best = null;
    for (const m of MILESTONES) if (hours >= m && !asked.includes(m)) best = m; // highest reached, unasked
    return best;
  }

  // Returns a new state with `milestone` and all lower ones marked as asked.
  function applyAsk(state, milestone, now) {
    const asked = new Set((state && state.asked) || []);
    for (const m of MILESTONES) if (m <= milestone) asked.add(m);
    return Object.assign({}, state, { asked: [...asked].sort((a, b) => a - b), lastAskAt: now });
  }

  const filled = (links, k) => !!links && typeof links[k] === "string" && links[k] !== "";
  function hasAnyLink(links) {
    return !!links && Object.values(links).some((v) => typeof v === "string" && v !== "");
  }
  // Button keys (small/medium/large/custom) that have a URL.
  const availableKeys = (links) => KEYS.filter((k) => filled(links, k));

  function isUsdLocale(language) {
    if (typeof language !== "string") return false;
    const lang = language.replace("_", "-");
    if (USD_LOCALES.includes(lang)) return true;
    const region = lang.split("-").slice(1).find((p) => /^[A-Za-z]{2}$/.test(p));
    return !!region && ["US", "PR"].includes(region.toUpperCase());
  }

  // USD only if small, medium AND large USD links are set and the locale is USD. The monthly link falls back to EUR.
  function selectLinks(language, eurLinks, usdLinks) {
    const usdComplete = ["small", "medium", "large"].every((k) => filled(usdLinks, k));
    if (usdComplete && isUsdLocale(language)) {
      const links = Object.assign({}, usdLinks);
      if (!filled(links, "monthly") && filled(eurLinks, "monthly")) links.monthly = eurLinks.monthly;
      return { currency: "USD", symbol: "$", links };
    }
    return { currency: "EUR", symbol: "€", links: eurLinks };
  }

  const STRIPE_ORIGINS = ["https://buy.stripe.com", "https://donate.stripe.com"];
  function isStripeUrl(u) {
    const x = typeof u === "string" ? /^(https:\/\/[^\/?#\s]+)(?:[\/?#]|$)/.exec(u) : null;
    return !!x && STRIPE_ORIGINS.includes(x[1]);
  }

  function bannerText(milestone, fmt) {
    return "Tab Nap has napped your tabs for " + fmt(milestone) + " tab-hours. Built by one developer, no ads, no tracking. If this helped, a coffee keeps it going.";
  }

  root.TabNapDonation = {
    MILESTONES, MIN_GAP_MS, USD_LOCALES, STRIPE_ORIGINS, pickAsk, applyAsk, isUsdLocale, selectLinks,
    hasAnyLink, availableKeys, isStripeUrl, bannerText,
  };
})(globalThis);
