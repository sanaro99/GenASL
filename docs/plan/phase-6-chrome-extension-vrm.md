# Phase 6 — Chrome Extension VRM Frontend

> Mounts a three.js + @pixiv/three-vrm canvas in a PiP overlay on
> YouTube watch pages, plays the `AvatarRenderPlan` v5.0 timeline, and
> stays in sync with the host `<video>` element.

---

## Goal

After this phase, loading the extension on a YouTube watch page produces
a visible signing avatar in the bottom-right corner that:
- loads from `AvatarSettings.vrm_model_url`,
- animates from the `motion[]` and `nmm[]` arrays,
- pauses, plays, seeks, and rate-changes in sync with the host video,
- tears down cleanly on SPA navigation away from the watch page.

## Why this phase

This is what the user actually sees. The pipeline can produce perfect
JSON but if the canvas mounts wrong or drifts out of sync, the demo
fails. Getting this phase right also locks in the
`AvatarRenderPlan` contract from the consumer side.

## Dependencies & prerequisites

- Phase 5 complete: the API can return real `AvatarRenderPlan` payloads
  (even if Phase 7 hasn't formalised it — Phase 6 can scaffold against
  generated `logs/avatar_plan_*.json` files served via a tiny static
  endpoint).
- No new Python deps.
- Vendored JS libraries (browser-side, committed under
  `chrome-extension/vendor/`):
  - `three.min.js` (three.js r160+)
  - `three-vrm.min.js` (@pixiv/three-vrm v2+)

---

## Step-by-step implementation

### 1. Vendor JS libraries

```bash
mkdir -p chrome-extension/vendor
# Pin specific versions; do not load from CDN in the extension
# (Manifest V3 forbids remote code).
curl -L -o chrome-extension/vendor/three.min.js \
  "https://unpkg.com/three@0.160.0/build/three.min.js"
curl -L -o chrome-extension/vendor/three-vrm.min.js \
  "https://unpkg.com/@pixiv/three-vrm@2.1.0/lib/three-vrm.min.js"
```

Commit both. ~700 kB combined; acceptable for an extension.

### 2. `chrome-extension/avatar.js`

The core renderer / animator. Exports a small class on `window.GenASLAvatar`:

```js
class GenASLAvatar {
  constructor(hostVideoEl, plan, options) {
    this.host = hostVideoEl;
    this.plan = plan;                          // AvatarRenderPlan v5.0
    this.opts = { widthRatio: 0.30, ...options };
    this._mount();
    this._loadVrm(plan.vrm_model_url || DEFAULT_VRM_URL).then(() => this._wire());
  }
  _mount() { /* create PiP <div> + <canvas>, three.js scene/camera/renderer */ }
  async _loadVrm(url) { /* GLTFLoader + VRMLoaderPlugin */ }
  _wire() {
    this.host.addEventListener('play',       () => this._onPlay());
    this.host.addEventListener('pause',      () => this._onPause());
    this.host.addEventListener('seeked',     () => this._onSeek());
    this.host.addEventListener('ratechange', () => this._onRate());
    this._tick();
  }
  _tick() {
    if (!this._raf) return;
    const tMs = this.host.currentTime * 1000;
    this._applyFrame(tMs);
    this.renderer.render(this.scene, this.camera);
    this._raf = requestAnimationFrame(() => this._tick());
  }
  _applyFrame(tMs) {
    // Binary-search for the motion frame at or before tMs; same for nmm.
    // Set vrm.humanoid.getNormalizedBoneNode(name).quaternion from
    // bone_rotations; set vrm.expressionManager.setValue from blendshapes.
  }
  destroy() { /* remove DOM, cancel RAF, dispose renderer */ }
}
```

Key implementation details:

- **Bone resolution:** use
  `vrm.humanoid.getNormalizedBoneNode("Hips")` etc. The names match the
  `VRM_HUMANOID_BONES` list in `src/avatar/vrm_schema.py`.
- **Blendshapes:** use
  `vrm.expressionManager.setValue(name, weight)` then
  `vrm.expressionManager.update()` after applying all values.
  Note RPM avatars expose ARKit-name expressions out of the box.
- **Binary search by `t_ms`:** keep a cursor so consecutive frames are
  O(1). Reset cursor on seek.
- **No interpolation in JS:** the Python pipeline already emits frames
  at 30 fps. JS just plays them.

### 3. PiP container styling

The avatar canvas needs a fixed-position overlay anchored to the
YouTube player. CSS injected from `avatar.js`:

```js
const styleEl = document.createElement('style');
styleEl.textContent = `
  #genasl-pip {
    position: fixed; right: 16px; bottom: 90px;
    width: ${Math.round(window.innerWidth * widthRatio)}px;
    aspect-ratio: 3 / 4;
    background: rgba(0,0,0,0.85);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 8px;
    z-index: 2147483647;   /* above YouTube chrome */
    overflow: hidden;
  }
  #genasl-pip canvas { width: 100%; height: 100%; display: block; }
  #genasl-pip .label {
    position: absolute; top: 4px; left: 6px;
    color: #fff; font: 10px/1.2 system-ui;
    opacity: 0.6;
  }
`;
document.head.appendChild(styleEl);
```

(Adjust right/bottom for theater mode; YouTube layout heuristics in
`content.js` decide where to anchor.)

### 4. Rewrite `chrome-extension/content.js`

Replace the stub with the real lifecycle:

```js
(() => {
  "use strict";
  const API_BASE = "http://127.0.0.1:8794";
  let avatar = null;

  function videoId() {
    return new URL(window.location.href).searchParams.get("v");
  }

  async function start() {
    teardown();
    const vid = videoId();
    if (!vid) return;
    const hostVideo = document.querySelector("video.html5-main-video");
    if (!hostVideo) {
      // YouTube SPA: retry shortly.
      setTimeout(start, 1000);
      return;
    }
    const r = await fetch(`${API_BASE}/asl/avatar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: vid }),
    });
    if (!r.ok) return;
    const plan = await r.json();
    avatar = new window.GenASLAvatar(hostVideo, plan);
  }

  function teardown() {
    if (avatar) { avatar.destroy(); avatar = null; }
  }

  // SPA navigation
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      if (location.pathname === "/watch") start();
      else teardown();
    }
  }).observe(document, { subtree: true, childList: true });

  if (location.pathname === "/watch") start();
})();
```

### 5. Update `chrome-extension/manifest.json`

Add the vendored libs and `avatar.js` to the content_scripts list:

```json
{
  "content_scripts": [
    {
      "matches": ["https://www.youtube.com/*"],
      "js": [
        "vendor/three.min.js",
        "vendor/three-vrm.min.js",
        "avatar.js",
        "content.js"
      ],
      "run_at": "document_idle"
    }
  ]
}
```

(Manifest V3 forbids loading scripts from CDNs at runtime; vendoring is mandatory.)

### 6. Popup updates (`popup.html`, `popup.js`)

Add a toggle to show/hide the avatar, a slider for canvas width,
read/write from `chrome.storage.local`. Content script reads the same
keys on mount.

---

## Tests to add

Browser-side automated tests are out of scope for this prototype. **Manual
test plan** — execute these in this exact order:

1. Server up: `python -m src.api.server`
2. Generate at least one `logs/avatar_plan_<id>.json` for the test video
   (`python -m src.pipeline.run_pipeline 31y2Bq1RYQA`).
3. Open `scripts/preview.html` and drag-drop the JSON. Confirm avatar
   animates without limb teleportation, T-pose flashes, or frame gaps.
4. Load the extension unpacked (`chrome://extensions`).
5. Navigate to `https://www.youtube.com/watch?v=31y2Bq1RYQA`.
6. Confirm PiP canvas appears within ~2 s of page load, in the
   bottom-right corner of the viewport, above the YouTube chrome.
7. Play the video; confirm the avatar starts signing.
8. Pause the video; the avatar should freeze on its current frame.
9. Seek backward 10 s; the avatar should jump to that point in the
   timeline within ~300 ms.
10. Change playback speed to 1.5×; the avatar's frame cursor should
    advance at 1.5× (host video's `currentTime` does the work).
11. Navigate to the homepage (SPA navigation, not a full reload); the
    avatar should be removed.
12. Navigate to a different video; the avatar should re-mount with the
    new video's plan.

A passing run on all 12 steps closes the phase.

---

## Commit hygiene

1. `chore(extension): vendor three.js + three-vrm`
2. `feat(extension): GenASLAvatar — VRM loader + timeline player`
3. `feat(extension): content.js lifecycle (mount, sync, teardown, SPA)`
4. `feat(extension): popup toggle + width slider + storage`
5. `chore(extension): update manifest for vendored scripts`

---

## Hand-off notes

- **YouTube's SPA is the trickiest part.** Watch-page navigations don't
  fire `DOMContentLoaded`. The `MutationObserver` pattern above is the
  canonical workaround; don't simplify.
- **z-index ceiling.** YouTube uses z-indices in the millions; use
  `2147483647` (int32 max) for the PiP container.
- **Performance budget.** A 1024×768 canvas at 30 fps with a VRM avatar
  costs ~5–10% CPU on modern laptops. Cap canvas resolution if users
  report fan spinup on low-end machines.
- **CSP and CORS:** the extension fetches from `127.0.0.1:8794`. The
  server already sets `Access-Control-Allow-Origin: chrome-extension://*`
  via the FastAPI middleware. Verify the same applies to the response
  for `/asl/avatar`.
- **Default VRM model.** Ready Player Me avatars are GLB, but
  @pixiv/three-vrm wants `.vrm` (which is also GLB-based). RPM offers
  a `?type=vrm` URL flag — use that or convert with a free RPM-to-VRM
  converter. Document the URL pattern in `AvatarSettings.vrm_model_url`'s
  docstring.

---

## Open questions

- Should the canvas pop out into a separate window (Document PiP API)?
  v1 decision: no — same-page PiP overlay is simpler and demos better.
- Should we support fullscreen YouTube? Yes — re-anchor on the
  `fullscreenchange` event. Defer if it eats time; the demo doesn't need it.
