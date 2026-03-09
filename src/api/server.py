"""Local API server for the ASL Overlay Chrome extension.

Receives caption text from the extension, translates it to ASL gloss,
looks up word-level clips, chains them into a single video, and returns
a URL the extension can play in an overlay <video> element.

Run with:
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

from src.gloss.translator import GlossTranslator
from src.gloss.word_lookup import WordLookup
from src.gloss.chainer import chain_clips
from src.transcript_ingestion.fetcher import fetch_transcript

logger = logging.getLogger(__name__)

# ── App setup ──────────────────────────────────────────────────────

# ── Lazy-loaded singletons (avoid slow startup on import) ──────────

_translator: GlossTranslator | None = None
_lookup: WordLookup | None = None
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CLIP_CACHE_DIR = _PROJECT_ROOT / "assets" / "chained"


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


# ── Warm up translator + LLM on server startup ────────────────────

@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Pre-init translator & send a throwaway query to warm the model."""
    loop = asyncio.get_event_loop()

    def _do_warmup():
        try:
            t = _get_translator()
            _get_lookup()
            logger.info("Warming up LLM with a dummy translation …")
            t.translate("hello")
            logger.info("Warmup complete — model is hot.")
        except Exception as exc:
            logger.warning("Warmup failed (non-fatal, will retry on first request): %s", exc)

    await loop.run_in_executor(None, _do_warmup)
    yield   # server is running


app = FastAPI(
    title="ASL Overlay API",
    version="1.0.0",
    description="Translates English captions → ASL gloss → chained video clips",
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


# ── In-memory cache for recent translations ────────────────────────
# Key: normalised caption text → value: AslResponse dict
_response_cache: dict[str, dict] = {}
_MAX_CACHE = 500

# Video-level transcript cache (keyed by video_id)
_transcript_cache: dict[str, list[dict]] = {}

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


# ── Blocking pipeline (runs in thread pool) ────────────────────────

def _translate_sync(text: str, ck: str) -> dict:
    """Run the blocking translate → lookup → chain pipeline."""
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

    clip_url = None
    clip_duration_ms = 0
    if found:
        clip_name = f"ext_{ck}"
        result = chain_clips(entries, clip_name)
        if result and Path(result["path"]).is_file():
            clip_url = f"http://127.0.0.1:8794/clips/{clip_name}.mp4"
            clip_duration_ms = result.get("duration_ms", 0)

    resp = {
        "glosses": glosses,
        "found": found,
        "missing": missing,
        "clip_url": clip_url,
        "clip_duration_ms": clip_duration_ms,
        "cached": False,
    }
    if len(_response_cache) >= _MAX_CACHE:
        keys = list(_response_cache.keys())[:100]
        for k in keys:
            del _response_cache[k]
    _response_cache[ck] = resp
    return resp


# ── Endpoints ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "time": time.time()}


@app.post("/asl", response_model=AslResponse)
async def translate_caption(req: CaptionRequest):
    """Translate a caption line to ASL and return a clip URL."""
    text = req.text.strip()
    if not text:
        return AslResponse(glosses=[], found=[], missing=[])

    # Check cache
    ck = _cache_key(text)
    if ck in _response_cache:
        cached = _response_cache[ck].copy()
        cached["cached"] = True
        return AslResponse(**cached)

    # Run the blocking pipeline in a thread so we don't stall the event loop
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, _translate_sync, text, ck)
    return AslResponse(**resp)


# ── Full-transcript pipeline ───────────────────────────────────────

def _process_transcript_sync(video_id: str) -> list[dict]:
    """Fetch transcript, batch-translate, lookup, chain — all blocking."""
    segments = fetch_transcript(video_id)
    if not segments:
        return []

    translator = _get_translator()
    lookup = _get_lookup()

    # Batch translate all lines at once (1 LLM call)
    texts = [seg["text"] for seg in segments]
    all_glosses = translator.translate_batch(texts)

    entries = []
    for seg, glosses in zip(segments, all_glosses):
        found_list = []
        missing_list = []
        clip_url = None
        clip_duration_ms = 0

        if glosses:
            word_entries = lookup.lookup_sequence(glosses)
            found_list = [e["gloss"] for e in word_entries if e["found"]]
            missing_list = [e["gloss"] for e in word_entries if not e["found"]]

            if found_list:
                ck = hashlib.md5(seg["text"].strip().lower().encode()).hexdigest()
                clip_name = f"ext_{ck}"
                result = chain_clips(word_entries, clip_name)
                if result and Path(result["path"]).is_file():
                    clip_url = f"http://127.0.0.1:8794/clips/{clip_name}.mp4"
                    clip_duration_ms = result.get("duration_ms", 0)

        entries.append({
            "start_ms": seg["start_ms"],
            "end_ms": seg["end_ms"],
            "text": seg["text"],
            "glosses": glosses,
            "found": found_list,
            "missing": missing_list,
            "clip_url": clip_url,
            "clip_duration_ms": clip_duration_ms,
        })

    logger.info(
        "Transcript processed: %d segments, %d with clips",
        len(entries), sum(1 for e in entries if e["clip_url"]),
    )
    return entries


@app.post("/asl/transcript", response_model=TranscriptResponse)
async def translate_transcript(req: TranscriptRequest):
    """Fetch, translate, and chain an entire YouTube video transcript."""
    video_id = req.video_id.strip()
    if not _VIDEO_ID_RE.match(video_id):
        return JSONResponse({"error": "invalid video_id"}, status_code=400)

    # Check video-level cache
    if video_id in _transcript_cache:
        logger.info("Transcript cache hit for %s", video_id)
        return TranscriptResponse(entries=_transcript_cache[video_id], cached=True)

    loop = asyncio.get_event_loop()
    entries = await loop.run_in_executor(None, _process_transcript_sync, video_id)
    _transcript_cache[video_id] = entries
    return TranscriptResponse(entries=entries, cached=False)


@app.get("/clips/{filename}")
async def serve_clip(filename: str):
    """Serve a chained clip file from assets/chained/."""
    # Sanitise: only allow simple filenames (no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse({"error": "invalid filename"}, status_code=400)
    path = _CLIP_CACHE_DIR / filename
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
    return {"count": len(lookup.available_glosses), "glosses": sorted(lookup.available_glosses)}


# ── Entry point ────────────────────────────────────────────────────

def main():
    import uvicorn
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    logger.info("Starting ASL Overlay API server on http://127.0.0.1:8794")
    uvicorn.run(app, host="127.0.0.1", port=8794, log_level="info")


if __name__ == "__main__":
    main()
