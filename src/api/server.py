"""Local API server for the ASL Overlay Chrome extension.

Two endpoints carry traffic from the extension:
  - ``POST /asl`` — translate one caption line to ASL, return a clip URL
    (ad-hoc, used for legacy single-caption requests).
  - ``POST /asl/transcript`` — fetch + translate the full transcript for a
    YouTube video, return a sorted playlist the extension polls against.

Run with::

    python -m src.api.server
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.logging import setup_logging
from src.core.paths import CHAINED_CLIPS_DIR
from src.gloss.chainer import chain_clips
from src.gloss.translator import GlossTranslator
from src.gloss.word_lookup import WordLookup
from src.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons (avoid slow startup on import) ──────────

_translator: GlossTranslator | None = None
_lookup: WordLookup | None = None
_pipeline: Pipeline | None = None


def _get_translator() -> GlossTranslator:
    global _translator
    if _translator is None:
        logger.info("Initialising GlossTranslator …")
        _translator = GlossTranslator()
    return _translator


def _get_lookup() -> WordLookup:
    global _lookup
    if _lookup is None:
        logger.info("Initialising WordLookup …")
        _lookup = WordLookup()
    return _lookup


def _get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        logger.info("Initialising Pipeline …")
        _pipeline = Pipeline()
    return _pipeline


# ── Warm up translator + LLM on server startup ────────────────────

@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Pre-init translator, lookup, pipeline; send a dummy LLM query to warm up."""
    loop = asyncio.get_event_loop()

    def _do_warmup():
        try:
            t = _get_translator()
            _get_lookup()
            _get_pipeline()
            logger.info("Warming up LLM with a dummy translation …")
            t.translate("hello")
            logger.info("Warmup complete — model is hot.")
        except Exception as exc:
            logger.warning("Warmup failed (non-fatal, will retry on first request): %s", exc)

    await loop.run_in_executor(None, _do_warmup)
    yield  # server is running


app = FastAPI(
    title="ASL Overlay API",
    version="2.0.0",
    description="English captions → ASL gloss → chained video clips",
    lifespan=_lifespan,
)

# Allow the Chrome extension (and localhost dev) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.youtube.com",
        "chrome-extension://*",
        "http://localhost:*",
        "http://127.0.0.1:*",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ──────────────────────────────────────

class CaptionRequest(BaseModel):
    text: str


class AslResponse(BaseModel):
    glosses: list[str]
    found: list[str]
    missing: list[str]
    clip_url: str | None = None
    clip_duration_ms: int = 0
    cached: bool = False


class TranscriptRequest(BaseModel):
    video_id: str


class TranscriptEntry(BaseModel):
    start_ms: int
    end_ms: int
    text: str
    glosses: list[str]
    found: list[str]
    missing: list[str]
    clip_url: str | None = None
    clip_duration_ms: int = 0


class TranscriptResponse(BaseModel):
    entries: list[TranscriptEntry]
    cached: bool = False


# ── In-memory caches (process-lifetime) ────────────────────────────

_response_cache: dict[str, dict] = {}
_transcript_cache: dict[str, list[dict]] = {}

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


def _clip_base_url() -> str:
    s = get_settings().api
    return f"http://{s.host}:{s.port}/clips"


# ── Blocking pipeline (runs in thread pool) ────────────────────────

def _translate_sync(text: str, ck: str) -> dict:
    """Run the blocking translate → lookup → chain pipeline for a single caption."""
    translator = _get_translator()
    glosses = translator.translate(text)
    if not glosses:
        resp = {"glosses": [], "found": [], "missing": [], "clip_url": None, "cached": False}
        _response_cache[ck] = resp
        return resp

    lookup = _get_lookup()
    entries = lookup.lookup_sequence(glosses)
    found = [e["gloss"] for e in entries if e["found"]]
    missing = [e["gloss"] for e in entries if not e["found"]]

    clip_url: str | None = None
    clip_duration_ms = 0
    if found:
        clip_name = f"ext_{ck}"
        result = chain_clips(entries, clip_name)
        if result and Path(result["path"]).is_file():
            clip_url = f"{_clip_base_url()}/{clip_name}.mp4"
            clip_duration_ms = result.get("duration_ms", 0)

    resp = {
        "glosses": glosses,
        "found": found,
        "missing": missing,
        "clip_url": clip_url,
        "clip_duration_ms": clip_duration_ms,
        "cached": False,
    }
    cache_max = get_settings().api.response_cache_max
    if len(_response_cache) >= cache_max:
        for k in list(_response_cache.keys())[:100]:
            del _response_cache[k]
    _response_cache[ck] = resp
    return resp


# ── Endpoints ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "time": time.time()}


@app.post("/asl", response_model=AslResponse)
async def translate_caption(req: CaptionRequest):
    """Translate one caption line to ASL and return a clip URL."""
    text = req.text.strip()
    if not text:
        return AslResponse(glosses=[], found=[], missing=[])

    ck = _cache_key(text)
    if ck in _response_cache:
        cached = _response_cache[ck].copy()
        cached["cached"] = True
        return AslResponse(**cached)

    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, _translate_sync, text, ck)
    return AslResponse(**resp)


# ── Full-transcript pipeline ───────────────────────────────────────

def _process_transcript_sync(video_id: str) -> list[dict]:
    """Run the full Pipeline and project the RenderPlan to TranscriptResponse entries."""
    plan = _get_pipeline().run(video_id)
    base = _clip_base_url()

    entries: list[dict] = []
    for seg in plan.segments:
        m = seg.match
        clip_url: str | None = None
        if m.chained_clip_path:
            filename = Path(m.chained_clip_path).name
            clip_url = f"{base}/{filename}"
        entries.append({
            "start_ms": seg.timing.start_ms,
            "end_ms": seg.timing.end_ms,
            "text": seg.source_text,
            "glosses": m.gloss_sequence,
            "found": m.found_glosses,
            "missing": m.missing_glosses,
            "clip_url": clip_url,
            "clip_duration_ms": m.chained_duration_ms or 0,
        })

    logger.info(
        "Transcript processed: %d segments, %d with clips",
        len(entries), sum(1 for e in entries if e["clip_url"]),
    )
    return entries


@app.post("/asl/transcript", response_model=TranscriptResponse)
async def translate_transcript(req: TranscriptRequest):
    """Fetch + translate + chain an entire YouTube video transcript."""
    video_id = req.video_id.strip()
    if not _VIDEO_ID_RE.match(video_id):
        return JSONResponse({"error": "invalid video_id"}, status_code=400)

    if video_id in _transcript_cache:
        logger.info("Transcript cache hit for %s", video_id)
        return TranscriptResponse(entries=_transcript_cache[video_id], cached=True)

    loop = asyncio.get_event_loop()
    try:
        entries = await loop.run_in_executor(None, _process_transcript_sync, video_id)
    except Exception as exc:
        logger.error("Transcript processing failed for %s: %s", video_id, exc)
        return JSONResponse({"error": f"transcript unavailable: {exc}"}, status_code=404)
    _transcript_cache[video_id] = entries
    return TranscriptResponse(entries=entries, cached=False)


@app.get("/clips/{filename}")
async def serve_clip(filename: str):
    """Serve a chained clip file from assets/chained/."""
    if "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse({"error": "invalid filename"}, status_code=400)
    path = CHAINED_CLIPS_DIR / filename
    if not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(
        path,
        media_type="video/mp4",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/glosses")
async def list_glosses():
    """Return the full set of available ASL glosses."""
    lookup = _get_lookup()
    return {
        "count": len(lookup.available_glosses),
        "glosses": sorted(lookup.available_glosses),
    }


# ── Entry point ────────────────────────────────────────────────────

def main() -> None:
    import uvicorn

    setup_logging()
    s = get_settings().api
    logger.info("Starting ASL Overlay API server on http://%s:%d", s.host, s.port)
    uvicorn.run(app, host=s.host, port=s.port, log_level="info")


if __name__ == "__main__":
    main()
