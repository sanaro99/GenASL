"""Local API server for the GenASL Chrome extension (interpreter_avatar mode).

The extension POSTs to ``/asl/avatar`` with a YouTube video_id and
receives an :class:`AvatarRenderPlan` (v5.0) JSON timeline that
the three.js + @pixiv/three-vrm consumer plays in a PiP canvas synced
to the source video.

Until Phases 2–5 wire the pipeline, this endpoint returns
``503 Not Implemented Yet`` so the extension can fail gracefully and
surface a clear "pipeline not ready" message to the user. See
``docs/plan/`` for the implementation roadmap.

Run with::

    python -m src.api.server
"""

from __future__ import annotations

import logging
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Startup hook — Phases 2–5 will pre-warm the avatar pipeline here."""
    yield


app = FastAPI(
    title="GenASL Avatar API",
    version="5.0.0",
    description="Audio -> 3D-avatar ASL pipeline (interpreter_avatar mode)",
    lifespan=_lifespan,
)

# Allow the Chrome extension (and localhost dev) to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.youtube.com",
        "http://localhost:*",
        "http://127.0.0.1:*",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ─────────────────────────────────────────

class AvatarRequest(BaseModel):
    video_id: str


_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe — also reports whether the avatar pipeline is wired."""
    s = get_settings()
    return {
        "status": "ok",
        "time": time.time(),
        "version": "5.0.0",
        "pipeline": "interpreter_avatar",
        "vrm_model_url": s.avatar.vrm_model_url,
        "ready": False,   # flips True once Phases 2-5 land
    }


@app.post("/asl/avatar")
async def asl_avatar(req: AvatarRequest):
    """Return an AvatarRenderPlan for the given YouTube video.

    Phases 2–5 will replace the stub below with an actual pipeline run.
    """
    video_id = req.video_id.strip()
    if not _VIDEO_ID_RE.match(video_id):
        return JSONResponse({"error": "invalid video_id"}, status_code=400)

    logger.info("[stub] avatar request for video_id=%s", video_id)
    return JSONResponse(
        {
            "error": "avatar pipeline not implemented yet",
            "phase_status": "Phase 1 (bootstrap) complete; Phases 2–5 pending",
            "see": "docs/plan/ in the repository for the implementation roadmap",
        },
        status_code=503,
    )


# ── Entry point ───────────────────────────────────────────────────────

def main() -> None:
    import uvicorn

    setup_logging()
    s = get_settings().api
    logger.info("Starting GenASL Avatar API on http://%s:%d", s.host, s.port)
    uvicorn.run(app, host=s.host, port=s.port, log_level="info")


if __name__ == "__main__":
    main()
