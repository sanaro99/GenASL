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

// Overlay size presets (index into SIZES)
const SIZES = [
  { w: 160, h: 130, label: "S"  },
  { w: 220, h: 180, label: "M"  },   // default
  { w: 320, h: 260, label: "L"  },
  { w: 420, h: 340, label: "XL" },
];

// ── State ──────────────────────────────────────────────────────────
let overlayRoot   = null;   // container div inside the YT player
let overlayVideo  = null;   // <video> element for ASL clips
let glossLabel    = null;   // gloss text element
let lastCaption   = "";     // dedup: skip unchanged captions
let enabled       = true;   // global on/off (toggled from popup)
let clipQueue     = [];     // queued clip URLs awaiting playback
let isPlaying     = false;  // true while overlay video is active
let pollTimer     = null;
let sizeIndex     = 1;      // default M
let showGloss     = false;  // gloss word overlay visibility
let currentGlosses = [];    // glosses for the current clip
let ytVideoListenersAttached = false;

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

  // Gloss text overlay
  glossLabel = document.createElement("div");
  glossLabel.id = "asl-gloss-label";
  glossLabel.style.display = showGloss ? "block" : "none";

  // Gloss label must be ABOVE the video — use a wrapper with z-index
  const videoWrap = document.createElement("div");
  videoWrap.id = "asl-overlay-video-wrap";
  videoWrap.appendChild(overlayVideo);

  overlayRoot.appendChild(videoWrap);
  overlayRoot.appendChild(label);
  overlayRoot.appendChild(glossLabel);
  player.appendChild(overlayRoot);

  console.log("[ASL] overlay created, showGloss:", showGloss, "sizeIndex:", sizeIndex);

  // Apply saved size
  applySize();

  // When a clip finishes, play the next queued clip (or hide).
  overlayVideo.addEventListener("ended", () => {
    playNextClip();
  });
  overlayVideo.addEventListener("error", () => {
    console.warn("[ASL] overlay video error", overlayVideo.error);
    playNextClip();
  });

  // Attach YT video listeners for pause/play/seek sync
  attachYTListeners();
}

// ── YouTube video event listeners (pause/play/seek sync) ──────────

function attachYTListeners() {
  if (ytVideoListenersAttached) return;
  const ytVid = getYTVideo();
  if (!ytVid) return;
  ytVideoListenersAttached = true;

  // Pause ASL overlay when YouTube pauses
  ytVid.addEventListener("pause", () => {
    if (overlayVideo && isPlaying) {
      overlayVideo.pause();
      console.log("[ASL] paused (YT paused)");
    }
  });

  // Resume ASL overlay when YouTube plays
  ytVid.addEventListener("play", () => {
    if (overlayVideo && isPlaying && overlayVideo.paused) {
      overlayVideo.play().catch(() => {});
      console.log("[ASL] resumed (YT playing)");
    }
  });

  // On seek: clear queue and reset overlay (captions will re-trigger)
  ytVid.addEventListener("seeked", () => {
    console.log("[ASL] YT seeked — clearing clip queue");
    clipQueue = [];
    lastCaption = "";       // allow re-processing of the caption at new position
    if (overlayVideo && isPlaying) {
      overlayVideo.pause();
      overlayVideo.removeAttribute("src");
      isPlaying = false;
      if (overlayRoot) overlayRoot.classList.remove("asl-visible");
    }
    updateGlossLabel([]);
  });
}

// ── Overlay size control ───────────────────────────────────────────

function applySize() {
  if (!overlayRoot) return;
  const s = SIZES[sizeIndex];
  overlayRoot.style.setProperty("width",  s.w + "px", "important");
  overlayRoot.style.setProperty("height", s.h + "px", "important");
  console.log("[ASL] applySize:", s.label, s.w + "x" + s.h);
}

function changeSize(delta) {
  sizeIndex = Math.max(0, Math.min(SIZES.length - 1, sizeIndex + delta));
  applySize();
  chrome.storage.local.set({ aslSizeIndex: sizeIndex });
  console.log("[ASL] overlay size:", SIZES[sizeIndex].label);
}

// ── Gloss label ────────────────────────────────────────────────────

function updateGlossLabel(glosses) {
  currentGlosses = glosses;
  if (glossLabel) {
    glossLabel.textContent = glosses.length ? glosses.join("  ") : "";
    console.log("[ASL] gloss:", glossLabel.textContent, "visible:", showGloss);
  }
}

function setGlossVisible(visible) {
  showGloss = visible;
  if (glossLabel) glossLabel.style.display = visible ? "block" : "none";
}

// ── Clip queue management ──────────────────────────────────────────

function enqueueClip(url, glosses) {
  clipQueue.push({ url, glosses });
  if (!isPlaying) playNextClip();
}

function playNextClip() {
  if (clipQueue.length === 0) {
    isPlaying = false;
    if (overlayRoot) overlayRoot.classList.remove("asl-visible");
    updateGlossLabel([]);
    return;
  }

  // Respect YT pause state — don't start a new clip if YT is paused
  const ytVid = getYTVideo();
  if (ytVid && ytVid.paused) {
    // Don't dequeue — wait. A "play" event will resume.
    return;
  }

  isPlaying = true;
  const item = clipQueue.shift();
  overlayVideo.src = item.url;
  overlayRoot.classList.add("asl-visible");
  updateGlossLabel(item.glosses || []);
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
      enqueueClip(data.clip_url, data.glosses || []);
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
  if (!ytVid) return;

  ensureOverlay();

  // Still poll captions even when paused (don't skip) — the queue
  // will just wait until YT resumes.  But only send new captions
  // when the video is actually playing.
  if (ytVid.paused) return;

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

// ── Listen for popup messages + storage changes ───────────────────

// Storage-based sync: popup writes settings, content script picks them up.
// This is more reliable than chrome.tabs.sendMessage which can fail.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local") return;
  if (changes.aslSizeIndex) {
    sizeIndex = changes.aslSizeIndex.newValue;
    applySize();
  }
  if (changes.aslShowGloss) {
    setGlossVisible(changes.aslShowGloss.newValue);
  }
  if (changes.aslEnabled) {
    enabled = changes.aslEnabled.newValue;
    if (!enabled) {
      stopPolling();
      if (overlayRoot) overlayRoot.classList.remove("asl-visible");
      clipQueue = [];
      isPlaying = false;
    } else {
      startPolling();
    }
  }
});

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
    sendResponse({ enabled, lastCaption, sizeLabel: SIZES[sizeIndex].label, showGloss });
  }
  if (msg.type === "asl-resize") {
    changeSize(msg.delta);   // +1 = bigger, -1 = smaller
    sendResponse({ sizeLabel: SIZES[sizeIndex].label });
  }
  if (msg.type === "asl-gloss-toggle") {
    setGlossVisible(msg.visible);
    chrome.storage.local.set({ aslShowGloss: showGloss });
    sendResponse({ showGloss });
  }
});

// ── SPA navigation handling (YouTube is a SPA) ────────────────────

function onNavigate() {
  lastCaption = "";
  clipQueue = [];
  isPlaying = false;
  ytVideoListenersAttached = false;   // new video element after navigation
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

// ── Init: restore saved preferences ───────────────────────────────
chrome.storage.local.get(["aslSizeIndex", "aslShowGloss"], (data) => {
  if (typeof data.aslSizeIndex === "number") sizeIndex = data.aslSizeIndex;
  if (typeof data.aslShowGloss === "boolean") showGloss = data.aslShowGloss;
});

// Initial start
if (location.pathname === "/watch") {
  startPolling();
}
