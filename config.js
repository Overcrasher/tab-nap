// Donation configuration. Fill in the placeholders before publishing.
// Stripe Payment Links in EUR (buy.stripe.com or donate.stripe.com): small = EUR 3, medium = EUR 5 (emphasized),
// large = EUR 10, custom = EUR 1 product with adjustable quantity ("Pick your own amount"),
// monthly = EUR 2 per month subscription (shown as a small text link).
// An empty string hides that button; if no link is set at all the popup never shows the ask.
// First release: only the EUR 3 link is live; medium/large/custom/monthly will be added in a later release.
export const DONATE_LINKS = { small: "https://donate.stripe.com/aFa14o3tB3U00Fc70Gfbq0a", medium: "", large: "", custom: "", monthly: "" };

// Optional USD set (same links created in USD). Used only if small, medium AND large are all non-empty
// AND the browser language is a US locale (region US or PR, e.g. en-US, es-US).
export const DONATE_LINKS_USD = { small: "", medium: "", large: "", custom: "", monthly: "" };

// Amounts shown on the buttons (data, not code). Must match the Stripe products.
export const DONATE_AMOUNTS = { small: 3, medium: 5, large: 10 };

// Static GitHub Pages thank-you page (served from docs/thanks.html).
// If the extension moves to another repo/username, change this AND the thanks.html match in
// manifest.json (content_scripts), then run tools/check_release.py.
export const THANKS_URL = "https://overcrasher.github.io/tab-nap/thanks.html";
