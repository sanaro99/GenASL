"use strict";

const toggle     = document.getElementById("toggle");
const dot        = document.getElementById("dot");
const statusText = document.getElementById("status-text");

// ── Check if the local API server is reachable ─────────────────────
async function checkServer() {
  try {
    const r = await fetch("http://127.0.0.1:8794/health", { signal: AbortSignal.timeout(2000) });
    if (r.ok) {
      dot.className = "dot on";
      statusText.textContent = "Server running";
    } else {
      dot.className = "dot off";
      statusText.textContent = "Server error";
    }
  } catch {
    dot.className = "dot off";
    statusText.textContent = "Server offline — run: python -m src.api.server";
  }
}

// ── Send toggle to content script ──────────────────────────────────
toggle.addEventListener("change", async () => {
  const enabled = toggle.checked;
  // Save preference
  chrome.storage.local.set({ aslEnabled: enabled });
  // Notify content script on the active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    chrome.tabs.sendMessage(tab.id, { type: "asl-toggle", enabled });
  }
});

// ── Init ───────────────────────────────────────────────────────────
chrome.storage.local.get("aslEnabled", (data) => {
  const on = data.aslEnabled !== false;   // default: on
  toggle.checked = on;
});

checkServer();
