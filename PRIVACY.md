# Privacy Policy – Tab Nap

**No data leaves your device.**

Tab Nap stores its settings (idle threshold, whitelist, average memory per tab, pause state), lifetime counters (tab-hours napped and total naps) and donation state in your browser's local extension storage (`chrome.storage.local`). Short-lived working state lives in session storage, which Chrome clears when the browser closes.

- No analytics, no tracking, no ads, no accounts.
- No server is contacted by the extension. It makes no network requests of its own.
- To decide which tabs are idle, Tab Nap tracks the last time each tab was active. It reads tab titles and addresses only to show the list of napped tabs in the popup and to match your whitelist. Tab favicons are loaded through the browser's internal favicon service, not from the internet by the extension.
- Tabs are put to sleep with Chrome's built-in tab discarding only. Tab Nap never rewrites a tab's address and never replaces a tab with a page of its own.
- Unsaved typing protection is optional and off until you turn it on. It requires access to sites, which Chrome asks you to approve. When on, a small script in each page notices that something was typed and reports only a yes/no flag ("has unsaved typing") to the extension. It never reads or sends what you typed, and password fields are ignored entirely. The flag is kept per tab in session storage and cleared when the tab closes or navigates.
- Estimates: "memory saved" is the number of tabs currently napped by Tab Nap times an average size per tab that you can change. It is an estimate, not a measurement.
- Permissions: `tabs` (tab list, activity and discarding), `storage`, `alarms` (the once-a-minute idle check), `contextMenus` (the right-click "Nap this tab now", "Never nap this site" and "Nap all other tabs" items), `scripting` (to register the typing detector only if you turn the protection on) and `favicon` (to show tab icons in the popup). Access to all sites is optional and requested only for the typing protection.
- Donation links open in a normal browser tab, at your request. Payments are handled entirely by Stripe on their own page; the extension never sees payment details.
- The optional thank-you page only lets the extension mark you as a supporter locally (a flag stored on your device). It is hosted on GitHub Pages, so visiting it contacts GitHub (their privacy policy applies). The extension itself still sends nothing.

You can erase all data at any time by removing the extension.

Questions: open an issue at https://github.com/Overcrasher/tab-nap/issues.

Publisher: Quantumbyte Labs.
