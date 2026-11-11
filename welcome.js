import { enableProtection, hasPermission } from "./lib/protect.js";
import { getAll } from "./lib/store.js";

const status = document.getElementById("protect-status");
const btn = document.getElementById("protect");
function show(msg) { status.textContent = msg; status.hidden = !msg; }

document.getElementById("open-settings").addEventListener("click", () => chrome.runtime.openOptionsPage());

btn.addEventListener("click", async () => {
  // The permission request has to start inside this click.
  const ok = await enableProtection();
  if (ok) { btn.hidden = true; show("Protection is on. Tabs with unsaved typing will be left awake."); }
  else show("Protection stays off. You can turn it on any time in the settings.");
});

(async () => {
  const { settings } = await getAll();
  if (settings.protectTyping && await hasPermission()) { btn.hidden = true; show("Protection is on. Tabs with unsaved typing will be left awake."); }
})();
