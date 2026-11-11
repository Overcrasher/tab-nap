// Unsaved-typing protection switch, shared by options and welcome (ES module).
// Turning it on asks Chrome for the optional host permission (must run inside the click handler), then tells the worker.

export async function hasPermission() {
  try { return await chrome.permissions.contains({ origins: ["<all_urls>"] }); } catch (e) { return false; }
}

// Returns true if protection is now on.
export async function enableProtection() {
  let granted = false;
  try { granted = await chrome.permissions.request({ origins: ["<all_urls>"] }); } catch (e) { granted = false; }
  if (!granted) return false;
  const r = await chrome.runtime.sendMessage({ type: "setProtection", enabled: true });
  return !!(r && r.ok);
}

export async function disableProtection() {
  const r = await chrome.runtime.sendMessage({ type: "setProtection", enabled: false });
  return !!(r && r.ok);
}
