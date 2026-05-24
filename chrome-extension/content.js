// GenASL — content script (interpreter_avatar mode, stub)
//
// The production behaviour: on YouTube watch pages, POST the videoId
// to http://127.0.0.1:8794/asl/avatar, receive an AvatarRenderPlan v5.0
// JSON timeline, mount a three.js + @pixiv/three-vrm canvas in a PiP
// overlay, and play the timeline in sync with the host <video>.
//
// Until Phases 2-7 land (see docs/plan/ in the repo) this script:
//   1. detects YouTube watch pages,
//   2. logs a console banner so it's obvious the extension is loaded,
//   3. probes the local API once and logs the result,
//   4. exits without injecting any overlay.
//
// All clip-PiP / overlay.css code from the previous WLASL pipeline is
// gone; the avatar canvas mounter ships in Phase 6.

(() => {
  "use strict";

  const API_BASE = "http://127.0.0.1:8794";
  const TAG = "[GenASL]";

  function getVideoId() {
    const url = new URL(window.location.href);
    return url.searchParams.get("v");
  }

  function isWatchPage() {
    return window.location.pathname === "/watch" && !!getVideoId();
  }

  async function probeApi() {
    try {
      const r = await fetch(`${API_BASE}/health`);
      const body = await r.json();
      console.info(TAG, "API /health:", body);
      return body;
    } catch (e) {
      console.warn(TAG, "API /health unreachable:", e.message);
      return null;
    }
  }

  async function requestAvatarPlan(videoId) {
    try {
      const r = await fetch(`${API_BASE}/asl/avatar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: videoId }),
      });
      const body = await r.json();
      if (r.status === 503) {
        console.info(TAG, "Avatar pipeline not wired yet:", body.phase_status);
      } else if (!r.ok) {
        console.warn(TAG, `Avatar request failed (${r.status}):`, body);
      } else {
        console.info(TAG, "Received avatar plan:", body);
        // Phase 6 will mount the three.js canvas here.
      }
    } catch (e) {
      console.warn(TAG, "Avatar request error:", e.message);
    }
  }

  if (!isWatchPage()) return;

  console.info(
    TAG,
    "Loaded on watch page (videoId=" + getVideoId() + "). " +
      "Interpreter-avatar pipeline is in build-out — see docs/plan/ in the repo."
  );

  probeApi().then((health) => {
    if (health && health.ready) {
      requestAvatarPlan(getVideoId());
    }
  });
})();
