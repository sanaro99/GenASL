/* ================================================================
   ASL Overlay for YouTube — Content Script
   ================================================================
   Injected on youtube.com.  On /watch pages, extracts the video ID,
   fetches the full transcript + ASL translations from the local API
   server in one call, then plays ASL clips at the correct timestamps
   as the YouTube video plays — zero API calls during playback.
   ================================================================ */

"use strict";

const API_BASE     = "http://127.0.0.1:8794";
const POLL_MS      = 250;       // timestamp-check interval
const PLAYBACK_MIN = 0.7;
const PLAYBACK_MAX = 2.5;

const SIZES = [
  { w: 160, h: 130, label: "S"  },
  { w: 220, h: 180, label: "M"  },
  { w: 320, h: 260, label: "L"  },
  { w: 420, h: 340, label: "XL" },
];

// ── State ──────────────────────────────────────────────────────────
let overlayRoot   = null;
let overlayVideo  = null;
let glossLabel    = null;
let enabled       = true;
let clipQueue     = [];
let isPlaying     = false;
let pollTimer     = null;
let sizeIndex     = 1;
let showGloss     = false;
let currentGlosses = [];
let ytVideoListenersAttached = false;

// Transcript playlist state
let aslPlaylist       = [];    // sorted array of { start_ms, end_ms, clip_url, glosses, clip_duration_ms }
let lastTriggeredIdx  = -1;    // index of the last entry we started playing
let currentVideoId    = null;  // YouTube video ID currently loaded
let transcriptLoading = false; // true while /asl/transcript is in-flight
let transcriptLoaded  = false; // true once playlist is ready

// ── Helpers ────────────────────────────────────────────────────────

function getYTVideo() {
  return document.querySelector("video.html5-main-video") ||
         document.querySelector("#movie_player video");
}

function getPlayerContainer() {
  return document.querySelector("#movie_player") ||
         document.querySelector(".html5-video-player");
}

/** Extract the 11-char video ID from the current YouTube URL. */
function getVideoId() {
  const params = new URLSearchParams(location.search);
  const v = params.get("v");
  if (v && /^[A-Za-z0-9_-]{11}$/.test(v)) return v;
  return null;
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
  overlayVideo.muted = true;
  overlayVideo.playsInline = true;
  overlayVideo.preload = "auto";

  const label = document.createElement("div");
  label.id = "asl-overlay-label";
  label.textContent = "ASL";

  glossLabel = document.createElement("div");
  glossLabel.id = "asl-gloss-label";
  glossLabel.style.display = showGloss ? "block" : "none";

  const videoWrap = document.createElement("div");
  videoWrap.id = "asl-overlay-video-wrap";
  videoWrap.appendChild(overlayVideo);

  overlayRoot.appendChild(videoWrap);
  overlayRoot.appendChild(label);
  overlayRoot.appendChild(glossLabel);
  player.appendChild(overlayRoot);

  applySize();

  overlayVideo.addEventListener("ended", () => playNextClip());
  overlayVideo.addEventListener("error", () => {
    console.warn("[ASL] overlay video error", overlayVideo.error);
    playNextClip();
  });

  attachYTListeners();
  console.log("[ASL] overlay created");
}

// ── YouTube video event listeners ─────────────────────────────────

function attachYTListeners() {
  if (ytVideoListenersAttached) return;
  const ytVid = getYTVideo();
  if (!ytVid) return;
  ytVideoListenersAttached = true;

  ytVid.addEventListener("pause", () => {
    if (overlayVideo && isPlaying) {
      overlayVideo.pause();
      console.log("[ASL] paused (YT paused)");
    }
  });

  ytVid.addEventListener("play", () => {
    if (overlayVideo && isPlaying && overlayVideo.paused) {
      overlayVideo.play().catch(() => {});
      console.log("[ASL] resumed (YT playing)");
    }
  });

  ytVid.addEventListener("seeked", () => {
    console.log("[ASL] YT seeked — resetting playlist position");
    clipQueue = [];
    lastTriggeredIdx = -1;
    if (overlayVideo && isPlaying) {
      overlayVideo.pause();
      overlayVideo.removeAttribute("src");
      isPlaying = false;
      if (overlayRoot) overlayRoot.classList.remove("asl-visible");
    }
    updateGlossLabel([]);
  });
}

// ── Overlay size ──────────────────────────────────────────────────

function applySize() {
  if (!overlayRoot) return;
  const s = SIZES[sizeIndex];
  overlayRoot.style.setProperty("width",  s.w + "px", "important");
  overlayRoot.style.setProperty("height", s.h + "px", "important");
}

function changeSize(delta) {
  sizeIndex = Math.max(0, Math.min(SIZES.length - 1, sizeIndex + delta));
  applySize();
  chrome.storage.local.set({ aslSizeIndex: sizeIndex });
}

// ── Gloss label ───────────────────────────────────────────────────

function updateGlossLabel(glosses) {
  currentGlosses = glosses;
  if (glossLabel) {
    glossLabel.textContent = glosses.length ? glosses.join("  ") : "";
  }
}

function setGlossVisible(visible) {
  showGloss = visible;
  if (glossLabel) glossLabel.style.display = visible ? "block" : "none";
}

// ── Loading state label ───────────────────────────────────────────

function showLoadingState(msg) {
  if (glossLabel) {
    glossLabel.textContent = msg;
    glossLabel.style.display = "block";
  }
}

function hideLoadingState() {
  if (glossLabel) {
    glossLabel.style.display = showGloss ? "block" : "none";
    glossLabel.textContent = "";
  }
}

// ── Clip queue management ─────────────────────────────────────────

function enqueueClip(url, glosses, clipDurationMs, availableMs) {
  clipQueue.push({ url, glosses, clipDurationMs: clipDurationMs || 0, availableMs: availableMs || 0 });
  if (!isPlaying) playNextClip();
}

function playNextClip() {
  if (clipQueue.length === 0) {
    isPlaying = false;
    if (overlayRoot) overlayRoot.classList.remove("asl-visible");
    updateGlossLabel([]);
    return;
  }

  const ytVid = getYTVideo();
  if (ytVid && ytVid.paused) return;

  isPlaying = true;
  const item = clipQueue.shift();
  overlayVideo.src = item.url;
  overlayRoot.classList.add("asl-visible");
  updateGlossLabel(item.glosses || []);

  // Adaptive playback speed: fit clip into the available time window
  if (item.clipDurationMs > 0 && item.availableMs > 0) {
    const idealRate = item.clipDurationMs / item.availableMs;
    const rate = Math.min(PLAYBACK_MAX, Math.max(PLAYBACK_MIN, idealRate));
    overlayVideo.playbackRate = rate;
    console.log("[ASL] rate:", rate.toFixed(2),
      `(clip ${item.clipDurationMs}ms / window ${item.availableMs}ms)`);
  } else {
    overlayVideo.playbackRate = 1.0;
  }

  overlayVideo.play().catch(err => {
    console.warn("[ASL] play() rejected:", err);
    playNextClip();
  });
}

// ── Transcript fetching ───────────────────────────────────────────

async function fetchTranscriptPlaylist(videoId) {
  if (transcriptLoading) return;
  transcriptLoading = true;
  transcriptLoaded = false;
  aslPlaylist = [];
  lastTriggeredIdx = -1;

  ensureOverlay();
  showLoadingState("Loading ASL transcript…");

  try {
    const resp = await fetch(`${API_BASE}/asl/transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId }),
    });
    if (!resp.ok) {
      console.warn("[ASL] transcript API error", resp.status);
      showLoadingState("ASL: transcript unavailable");
      return;
    }
    const data = await resp.json();
    aslPlaylist = (data.entries || []).filter(e => e.clip_url);
    aslPlaylist.sort((a, b) => a.start_ms - b.start_ms);
    transcriptLoaded = true;
    currentVideoId = videoId;
    hideLoadingState();
    console.log("[ASL] playlist loaded:", aslPlaylist.length, "entries",
      data.cached ? "(cached)" : "(fresh)");
  } catch (err) {
    console.warn("[ASL] transcript fetch error:", err);
    showLoadingState("ASL: server offline");
  } finally {
    transcriptLoading = false;
  }
}

// ── Timestamp-tracking tick loop ──────────────────────────────────

function tick() {
  if (!enabled) return;

  const ytVid = getYTVideo();
  if (!ytVid) return;

  ensureOverlay();

  // If we haven't fetched the transcript for this video yet, do it now
  const vid = getVideoId();
  if (vid && vid !== currentVideoId && !transcriptLoading) {
    fetchTranscriptPlaylist(vid);
    return;
  }

  if (!transcriptLoaded || ytVid.paused) return;

  const currentMs = ytVid.currentTime * 1000;

  // Find the playlist entry for the current timestamp
  // Binary-search friendly since playlist is sorted by start_ms
  for (let i = 0; i < aslPlaylist.length; i++) {
    const entry = aslPlaylist[i];
    if (currentMs >= entry.start_ms && currentMs < entry.end_ms) {
      if (i !== lastTriggeredIdx) {
        lastTriggeredIdx = i;
        const availableMs = entry.end_ms - entry.start_ms;
        enqueueClip(entry.clip_url, entry.glosses || [], entry.clip_duration_ms || 0, availableMs);
        console.log("[ASL] triggered entry", i, "@", Math.round(currentMs) + "ms:",
          (entry.glosses || []).join(" "));
      }
      break;
    }
  }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(tick, POLL_MS);
  console.log("[ASL] timestamp polling started");
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ── Listen for popup messages + storage changes ───────────────────

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
    sendResponse({
      enabled,
      sizeLabel: SIZES[sizeIndex].label,
      showGloss,
      playlistSize: aslPlaylist.length,
      transcriptLoaded,
    });
  }
  if (msg.type === "asl-resize") {
    changeSize(msg.delta);
    sendResponse({ sizeLabel: SIZES[sizeIndex].label });
  }
  if (msg.type === "asl-gloss-toggle") {
    setGlossVisible(msg.visible);
    chrome.storage.local.set({ aslShowGloss: showGloss });
    sendResponse({ showGloss });
  }
});

// ── SPA navigation handling ───────────────────────────────────────

function onNavigate() {
  clipQueue = [];
  isPlaying = false;
  lastTriggeredIdx = -1;
  aslPlaylist = [];
  transcriptLoaded = false;
  transcriptLoading = false;
  currentVideoId = null;
  ytVideoListenersAttached = false;

  setTimeout(() => {
    if (location.pathname === "/watch") {
      ensureOverlay();
      startPolling();
    } else {
      stopPolling();
    }
  }, 1500);
}

window.addEventListener("yt-navigate-finish", onNavigate);

// ── Init ──────────────────────────────────────────────────────────

chrome.storage.local.get(["aslSizeIndex", "aslShowGloss"], (data) => {
  if (typeof data.aslSizeIndex === "number") sizeIndex = data.aslSizeIndex;
  if (typeof data.aslShowGloss === "boolean") showGloss = data.aslShowGloss;
});

if (location.pathname === "/watch") {
  startPolling();
}
