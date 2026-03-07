/* ASL Overlay — Background service worker (Manifest V3) */

// Nothing complex needed; just relay messages between popup and content script.
chrome.runtime.onInstalled.addListener(() => {
  console.log("[ASL Overlay] Extension installed");
});
