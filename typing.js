// Typing detector (content script, registered only after the user grants the optional host permission).
// Sends ONE boolean message the first time the user types into a text field on the page. It never reads,
// stores or sends what was typed, ignores password fields completely, and never touches chrome.storage.
(() => {
  if (globalThis.__tabNapTyping) return;
  globalThis.__tabNapTyping = true;
  const NON_TEXT = new Set(["password", "hidden", "checkbox", "radio", "button", "submit", "reset", "image", "file", "range", "color"]);
  let sent = false;

  function isTextEntry(el) {
    if (!el || el.nodeType !== 1) return false;
    const tag = el.tagName;
    if (tag === "TEXTAREA") return true;
    if (tag === "INPUT") return !NON_TEXT.has((el.getAttribute("type") || "text").toLowerCase());
    return el.isContentEditable === true;
  }

  function onInput(e) {
    if (sent || !e.isTrusted) return;
    // composedPath()[0] sees through open shadow roots.
    const target = (e.composedPath && e.composedPath()[0]) || e.target;
    if (!isTextEntry(target)) return;
    sent = true;
    try { chrome.runtime.sendMessage({ type: "dirty", dirty: true }).catch(() => {}); } catch (err) { /* extension reloaded */ }
  }
  addEventListener("input", onInput, true);
})();
