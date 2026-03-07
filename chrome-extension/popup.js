"use strict";

const toggle      = document.getElementById("toggle");
const glossToggle = document.getElementById("gloss-toggle");
const sizeUp      = document.getElementById("size-up");
const sizeDown    = document.getElementById("size-down");
const sizeLabel   = document.getElementById("size-label");
const dot         = document.getElementById("dot");
const statusText  = document.getElementById("status-text");

// ── Helper: send message to the content script on the active tab ──
async function sendToContent(message) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return null;
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tab.id, message, (resp) => {
      resolve(resp || null);
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
sizeUp.addEventListener("click", async () => {
  const resp = await sendToContent({ type: "asl-resize", delta: 1 });
  if (resp?.sizeLabel) sizeLabel.textContent = resp.sizeLabel;
});

sizeDown.addEventListener("click", async () => {
  const resp = await sendToContent({ type: "asl-resize", delta: -1 });
  if (resp?.sizeLabel) sizeLabel.textContent = resp.sizeLabel;
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

  // Size label — ask the content script for the current label
  sendToContent({ type: "asl-status" }).then((resp) => {
    if (resp?.sizeLabel) sizeLabel.textContent = resp.sizeLabel;
  });
});

checkServer();
