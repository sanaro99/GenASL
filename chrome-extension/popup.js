"use strict";

// Popup just probes the local API so the user can see whether the
// avatar pipeline server is running and how far along the build-out is.
// All wiring for runtime controls (e.g. avatar size, voice mode) lands
// alongside Phase 6.

const API_BASE = "http://127.0.0.1:8794";

async function probeHealth() {
  const el = document.getElementById("api-status");
  try {
    const r = await fetch(`${API_BASE}/health`);
    const body = await r.json();
    if (body.ready) {
      el.className = "status ok";
      el.textContent = `API ready (v${body.version}).`;
    } else {
      el.className = "status warn";
      el.textContent =
        `API up (v${body.version}) but pipeline not fully wired yet. ` +
        `See docs/plan/.`;
    }
  } catch (e) {
    el.className = "status err";
    el.textContent = `API unreachable — start it with: python -m src.api.server`;
  }
}

probeHealth();
