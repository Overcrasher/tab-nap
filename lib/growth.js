// Growth helpers (rating prompt, share text, store URLs). Classic script on globalThis.
(function (root) {
  "use strict";

  const STORE_BASE = "https://chromewebstore.google.com/detail/";
  const RATING_THRESHOLD = 50; // naps
  const SIBLINGS = [
    { name: "Wait 24h", url: "https://chromewebstore.google.com/detail/wait-24h/pkgdjohoemjkejcbfbkfobbbjcpdabme", blurb: "a pause before impulse buys" },
    { name: "Meeting Meter", url: "https://chromewebstore.google.com/detail/meeting-meter/ffkniocclnaojfdcoofnjkfnihnpgnlb", blurb: "see what your meetings cost" },
  ];

  // The extension id is a parameter so these stay pure (callers pass chrome.runtime.id).
  const storeUrl = (id) => STORE_BASE + id;
  const reviewsUrl = (id) => storeUrl(id) + "/reviews";
  const shareUrl = (id) => storeUrl(id) + "?utm_source=share";
  // Exact URLs the UI may open from links.
  const allowedUrls = (id) => [storeUrl(id), reviewsUrl(id)].concat(SIBLINGS.map((s) => s.url));

  function sanitizeRating(r) {
    if (!r || typeof r !== "object" || r.shown !== true) return { shown: false, at: 0 };
    return { shown: true, at: typeof r.at === "number" && isFinite(r.at) ? r.at : 0 };
  }
  // True when the rating card may be shown: enough naps and never shown before.
  function shouldAskRating(state, count, threshold) {
    if (sanitizeRating(state).shown) return false;
    return typeof count === "number" && isFinite(count) && count >= threshold;
  }

  // hoursText/memText are preformatted ("1,240", "2.3 GB"); memText may be null when nothing is napped right now.
  function shareText(hoursText, memText, url) {
    const tail = memText ? " and saved ≈ " + memText + " of memory right now" : "";
    return "Tab Nap has put my tabs to sleep for " + hoursText + " tab-hours" + tail + ". #TabNap " + url;
  }

  root.TabNapGrowth = { STORE_BASE, RATING_THRESHOLD, SIBLINGS, storeUrl, reviewsUrl, shareUrl, allowedUrls, sanitizeRating, shouldAskRating, shareText };
})(globalThis);
