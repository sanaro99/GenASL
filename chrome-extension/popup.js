"use strict";

const toggle      = document.getElementById("toggle");
const glossToggle = document.getElementById("gloss-toggle");
const sizeUp      = document.getElementById("size-up");
const sizeDown    = document.getElementById("size-down");
const sizeLabel   = document.getElementById("size-label");
const dot         = document.getElementById("dot");
const statusText  = document.getElementById("status-text");

// Must match SIZES array in content.js
const SIZE_LABELS = ["S", "M", "L", "XL"];
let currentSizeIndex = 1;  // default M

// ── Helper: send message to the content script on the active tab ──
async function sendToContent(message) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return null;
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tab.id, message, () => {
      if (chrome.runtime.lastError) { resolve(null); return; }
      resolve(true);
    });
  });
}

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

// ── Enable / disable toggle ────────────────────────────────────────
toggle.addEventListener("change", async () => {
  const enabled = toggle.checked;
  chrome.storage.local.set({ aslEnabled: enabled });
  await sendToContent({ type: "asl-toggle", enabled });
});

// ── Overlay size buttons ───────────────────────────────────────────
function updateSizeLabel() {
  sizeLabel.textContent = SIZE_LABELS[currentSizeIndex];
}

sizeUp.addEventListener("click", () => {
  currentSizeIndex = Math.min(SIZE_LABELS.length - 1, currentSizeIndex + 1);
  updateSizeLabel();
  chrome.storage.local.set({ aslSizeIndex: currentSizeIndex });
  sendToContent({ type: "asl-resize", delta: 1 });
});

sizeDown.addEventListener("click", () => {
  currentSizeIndex = Math.max(0, currentSizeIndex - 1);
  updateSizeLabel();
  chrome.storage.local.set({ aslSizeIndex: currentSizeIndex });
  sendToContent({ type: "asl-resize", delta: -1 });
});

// ── Gloss text toggle ──────────────────────────────────────────────
glossToggle.addEventListener("change", async () => {
  const visible = glossToggle.checked;
  chrome.storage.local.set({ aslShowGloss: visible });
  await sendToContent({ type: "asl-gloss-toggle", visible });
});

// ── Init: restore saved preferences ────────────────────────────────
chrome.storage.local.get(["aslEnabled", "aslSizeIndex", "aslShowGloss"], (data) => {
  toggle.checked = data.aslEnabled !== false;        // default: on
  glossToggle.checked = data.aslShowGloss === true;  // default: off

  // Size label — read directly from storage (no content script needed)
  if (typeof data.aslSizeIndex === "number" && data.aslSizeIndex >= 0 && data.aslSizeIndex < SIZE_LABELS.length) {
    currentSizeIndex = data.aslSizeIndex;
  }
  updateSizeLabel();
});

checkServer();
