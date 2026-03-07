/* ================================================================
   ASL Overlay for YouTube — Content Script
   ================================================================
   Injected on youtube.com.  Watches the YouTube player for caption
   cue changes and sends each new caption line to the local ASL API
   server, which returns a clip URL played in an overlay <video>.
   ================================================================ */

"use strict";

const API_BASE = "http://127.0.0.1:8794";   // local FastAPI server
const POLL_MS  = 250;                        // caption-check interval

// ── State ──────────────────────────────────────────────────────────
let overlayRoot   = null;   // container div inside the YT player
let overlayVideo  = null;   // <video> element for ASL clips
let lastCaption   = "";     // dedup: skip unchanged captions
let enabled       = true;   // global on/off (toggled from popup)
let clipQueue     = [];     // queued clip URLs awaiting playback
let isPlaying     = false;  // true while overlay video is active
let pollTimer     = null;

// ── Helpers ────────────────────────────────────────────────────────

/** Find the YouTube <video> element. */
function getYTVideo() {
  return document.querySelector("video.html5-main-video") ||
         document.querySelector("#movie_player video");
}

/** Find the YT player container (for overlay positioning). */
function getPlayerContainer() {
  return document.querySelector("#movie_player") ||
         document.querySelector(".html5-video-player");
}

/** Read the currently-visible caption text from the DOM. */
function getCurrentCaption() {
  // YouTube renders captions in a container with this class
  const segments = document.querySelectorAll(
    ".ytp-caption-segment"
  );
  if (segments.length === 0) return "";
  return Array.from(segments).map(s => s.textContent.trim()).join(" ");
}

// ── Overlay creation ───────────────────────────────────────────────

function ensureOverlay() {
  if (overlayRoot && document.contains(overlayRoot)) return;

  const player = getPlayerContainer();
  if (!player) return;

  overlayRoot = document.createElement("div");
  overlayRoot.id = "asl-overlay-root";

  overlayVideo = document.createElement("video");
  overlayVideo.id = "asl-overlay-video";
  overlayVideo.muted = true;            // autoplay requires muted first
  overlayVideo.playsInline = true;
  overlayVideo.preload = "auto";

  const label = document.createElement("div");
  label.id = "asl-overlay-label";
  label.textContent = "ASL";

  overlayRoot.appendChild(overlayVideo);
  overlayRoot.appendChild(label);
  player.appendChild(overlayRoot);

  // When a clip finishes, play the next queued clip (or hide).
  overlayVideo.addEventListener("ended", () => {
    playNextClip();
  });
  overlayVideo.addEventListener("error", () => {
    console.warn("[ASL] overlay video error", overlayVideo.error);
    playNextClip();
  });
}

// ── Clip queue management ──────────────────────────────────────────

function enqueueClip(url) {
  clipQueue.push(url);
  if (!isPlaying) playNextClip();
}

function playNextClip() {
  if (clipQueue.length === 0) {
    isPlaying = false;
    if (overlayRoot) overlayRoot.classList.remove("asl-visible");
    return;
  }
  isPlaying = true;
  const url = clipQueue.shift();
  overlayVideo.src = url;
  overlayRoot.classList.add("asl-visible");
  overlayVideo.play().catch(err => {
    console.warn("[ASL] play() rejected:", err);
    playNextClip();
  });
}

// ── Caption → ASL pipeline ─────────────────────────────────────────

async function processCaption(text) {
  if (!text || text === lastCaption) return;
  lastCaption = text;

  try {
    const resp = await fetch(`${API_BASE}/asl`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) {
      console.warn("[ASL] API error", resp.status);
      return;
    }
    const data = await resp.json();
    // data: { clip_url, glosses, found, missing }
    if (data.clip_url) {
      enqueueClip(data.clip_url);
    }
  } catch (err) {
    // Server down — silently ignore so we don't spam console
    if (err.name !== "TypeError") console.warn("[ASL] fetch error:", err);
  }
}

// ── Main poll loop ─────────────────────────────────────────────────

function tick() {
  if (!enabled) return;

  const ytVid = getYTVideo();
  if (!ytVid || ytVid.paused) return;          // only when playing

  ensureOverlay();
  const caption = getCurrentCaption();
  if (caption && caption !== lastCaption) {
    processCaption(caption);
  }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(tick, POLL_MS);
  console.log("[ASL] caption polling started");
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ── Listen for popup toggle messages ───────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "asl-toggle") {
    enabled = msg.enabled;
    if (!enabled) {
      stopPolling();
      if (overlayRoot) overlayRoot.classList.remove("asl-visible");
      clipQueue = [];
      isPlaying = false;
    } else {
      startPolling();
    }
    sendResponse({ enabled });
  }
  if (msg.type === "asl-status") {
    sendResponse({ enabled, lastCaption });
  }
});

// ── SPA navigation handling (YouTube is a SPA) ────────────────────

function onNavigate() {
  lastCaption = "";
  clipQueue = [];
  isPlaying = false;
  // Re-check for the player after YouTube's SPA navigation
  setTimeout(() => {
    if (location.pathname === "/watch") {
      ensureOverlay();
      startPolling();
    } else {
      stopPolling();
    }
  }, 1500);
}

// YouTube fires yt-navigate-finish on SPA transitions
window.addEventListener("yt-navigate-finish", onNavigate);

// Initial start
if (location.pathname === "/watch") {
  startPolling();
}
