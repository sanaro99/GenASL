// GenASL — service worker (Manifest V3).
// Minimal — installation marker only; content + popup talk to the local
// API directly. Reserve this file for future cross-tab coordination if
// the avatar pipeline ever needs a long-lived background channel.

chrome.runtime.onInstalled.addListener(() => {
  console.log("[GenASL] Extension installed (interpreter_avatar mode).");
});
