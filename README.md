# Tab Nap – Tab Suspender & Memory Saver

Part of the Quantumbyte Labs set ("Software built for humans. Sustainable and secure."). A Manifest V3 Chrome extension that puts idle tabs to sleep and gives the memory back, without ever losing a tab.

## The main trust point: native discarding only

Tab Nap uses `chrome.tabs.discard()` and nothing else. It **never rewrites a tab's URL** to a custom "suspended" page. That is how older suspender extensions lost people's tabs when they were removed or broke: the tabs were left pointing at a page that no longer existed. A tab napped by Tab Nap is an ordinary Chrome discarded tab: it keeps its address, title and history, it survives uninstalling Tab Nap, and Chrome reloads it when you click it.

(Chrome gives a discarded tab a new internal tab id. Tab Nap tracks that through the id returned by `discard()` and `tabs.onReplaced`.)

## Install (unpacked)

1. `chrome://extensions` → Developer mode → "Load unpacked" → select this folder.
2. A welcome page opens on first install only.

## How it works

- An alarm fires every minute. Tabs whose last activity is older than the threshold (5 / 15 / 30 default / 60 / 120 minutes) are discarded.
- Activity is tracked from `tabs.onActivated`, `tabs.onUpdated` (load complete, woken up, audio changes) and `windows.onFocusChanged`, kept in `chrome.storage.session` so it survives service-worker restarts, combined with Chrome's own `tab.lastAccessed`.
- **Never napped:** the active tab of any window, pinned tabs (option, default on), audible tabs, tabs with `autoDiscardable === false`, tabs already discarded, whitelisted domains (and subdomains), tabs with unsaved typing, tabs still loading, and anything that is not an `http(s)` page (`chrome://`, extension pages, `about:`, `file:`...). These are skipped quietly. All of it is pure logic in `lib/nap.js` (`whyNot`) and unit-tested.
- **Pause:** "until turned back on" (switch) or "for 1 hour" (popup). Options has the same switch.
- **Context menu** (right-click a page):
  - *Nap this tab now*: ignores the idle threshold but keeps every NEVER rule. You cannot discard the tab you are looking at, so Tab Nap first switches to another awake tab in the same window; if there is none (or the tab is protected) it does nothing and flashes "!" on the toolbar icon.
  - *Never nap this site*: adds the domain to the whitelist.
  - *Nap all other tabs*: this window, ignoring the threshold, respecting all NEVER rules.
- **Popup:** "Currently napping N tabs, ≈ X (estimated)", lifetime tab-hours napped and total naps, a list of napped tabs (favicons through the `favicon` permission's `_favicon` URL, no remote images; click to wake), pause, Share.
- **Numbers:** memory estimate = tabs currently napped *by Tab Nap* × average MB per tab (default 150, setting 50–500), always labelled an estimate. Tab-hours: each minute check adds `napped tabs / 60`; a tab stops counting when it wakes, reloads or closes.
- **Share text:** `Tab Nap has put my tabs to sleep for 1,240 tab-hours and saved ≈ 2.3 GB of memory right now. #TabNap <store URL>` (the store URL is derived from `chrome.runtime.id`).

## Unsaved typing protection (permission choice)

Seeing which tabs have typing in them needs a content script in every page, which means host access to all sites. That is a scary install warning for a feature some people will not want, so:

- Shipped permissions: `tabs`, `storage`, `alarms`, `contextMenus`, `scripting`, `favicon`; `optional_host_permissions: ["<all_urls>"]`. The default install asks for **no host access**.
- Options and the welcome page offer "Protect tabs with unsaved typing (recommended)". Turning it on calls `chrome.permissions.request` (inside the click), and on grant the service worker registers `typing.js` with `chrome.scripting.registerContentScripts` (all frames, `document_idle`, persists across sessions) and injects it into already-open tabs. Turning it off unregisters the script, clears the flags and removes the permission. If the user revokes the permission in Chrome, the worker notices (`permissions.onRemoved`, startup reconcile) and switches the setting off.
- `typing.js` sends one boolean message, `{type:"dirty", dirty:true}`, the first time the user types (trusted `input` events only) in a text input, textarea or contenteditable. Password fields, checkboxes etc. are ignored entirely. It never reads or sends what was typed and never touches storage.
- The worker keeps the dirty set in `chrome.storage.session` keyed by tab id, clears it on a new page load, tab close and replacement. A tab is "dirty" from the first keystroke until its page reloads or closes.
- Without the permission Tab Nap cannot see forms: it still naps, and the options page says so plainly (a napped tab is restored by Chrome, but text that was never saved or submitted may be lost).

The `thanks.js` content script (supporter flag) matches only `https://overcrasher.github.io/tab-nap/thanks.html?session_id=*`; Chrome therefore lists that one site in the install warning.

## Security model

- `chrome.storage.local` and `chrome.storage.session` are set to `TRUSTED_CONTEXTS`: content scripts cannot read or write storage; they only message the service worker.
- The worker classifies every sender: extension pages (our own origin, no tab) vs content scripts (`sender.tab`). The tab id and URL always come from the sender, never from the message. Every field is validated; unknown types are rejected. The supporter flag is accepted only from the exact thanks page with a `^cs_(live|test)_[A-Za-z0-9]{20,}$` session id; `dirty` only from http(s) tabs, only as `dirty:true`, only while protection is on and the permission is held.
- Stored data is sanitized on every read (`lib/validate.js`); junk in storage falls back to defaults.
- Strict extension-page CSP (no inline script/style, no remote code, no eval), no innerHTML with page data (titles/URLs are set with `textContent`), only allow-listed URLs are opened (Stripe origins, the store reviews page, the two sibling store pages).
- `globalThis.__tabNapTest` in the worker is a test hook (run the check with a chosen "now", invoke menu handlers). It exists only in the worker's own scope: pages and content scripts cannot reach it, only a DevTools/CDP session attached to the worker.

## Permissions, and why

| Permission | Why |
|---|---|
| `tabs` | Read tab URL/title/pinned/audible/last-accessed state and call `discard`, `update`, `remove` bookkeeping. |
| `storage` | Settings, whitelist, counters (local); tab activity, napped ids, dirty flags (session). |
| `alarms` | The once-a-minute check. |
| `contextMenus` | "Nap this tab now", "Never nap this site", "Nap all other tabs". |
| `scripting` | Register/inject `typing.js` after the user opts in to typing protection. |
| `favicon` | Favicons in the popup list through the local `_favicon` URL (no remote images). |
| optional `<all_urls>` | Only if the user turns on typing protection; revocable. |

## Donations (Stripe) and growth features

Amounts and links are data in `config.js`: `DONATE_LINKS`, `DONATE_LINKS_USD` (`small`, `medium`, `large`, `custom`, `monthly`), `DONATE_AMOUNTS = {small:3, medium:5, large:10}`, `THANKS_URL`. Empty link = button hidden; no link at all = never ask.

Stripe setup: create Payment Links (EUR) for €3, €5, €10, a €1 product with adjustable quantity ("Pick your own amount"), and a €2/month subscription; set the "after payment" redirect to `https://overcrasher.github.io/tab-nap/thanks.html` (Stripe appends `?session_id=`). Paste the URLs into `config.js`. Only `buy.stripe.com` / `donate.stripe.com` ever open.

Asks happen only at lifetime milestones of 100, 1,000 and 10,000 tab-hours, as a dismissible popup banner; one ask per milestone, at least 30 days apart, permanent "Don't ask again", never for supporters ("Supporter ❤" badge). A one-time rating card appears after 50 naps (never in the same render as the banner). Options has a "Support this project" section, the rate link and the sibling extensions (Wait 24h, Meeting Meter).

## Tests

```
/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc tests/run.js   # unit tests (pure logic)
python3 tests/e2e/harness.py        # Chrome 157 end-to-end over CDP; ONLY=2,5 selects groups; needs network for the real-page group
python3 tools/check_release.py      # add --release to require at least one EUR Stripe link
```

The E2E harness drives real Chrome headless with real https tabs. It cannot drive the native context-menu UI or the permission prompt headless, so menu handlers are invoked directly and the permission request is stubbed on a test copy that already holds `<all_urls>`; the rest of the flow is real code.

## Packaging

```
python3 tools/package.py                         # runs check_release.py --release first
python3 tools/package.py --skip-release-check    # same zip while donation links are still empty
```
Output: `dist/tab-nap-1.0.0.zip` (runtime files only: manifest, JS, HTML/CSS, icons, `_locales`). The script verifies every file referenced by the manifest, HTML pages, ES-module imports and `__MSG_*` keys.

## Changes

- **1.0.0** – first release.
