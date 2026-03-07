"""Fetch YouTube transcript via InnerTube API (bypasses some bot detection).

Usage:  python scripts/fetch_transcript_innertube.py <VIDEO_ID>

This saves the result to transcripts/<VIDEO_ID>.json so the pipeline
can use it from cache without hitting YouTube again.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CACHE_DIR = _PROJECT_ROOT / "transcripts"

_INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/get_transcript"
_INNERTUBE_CLIENTS = [
    {
        "name": "web",
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB",
                "clientVersion": "2.20241126.01.00",
            }
        },
    },
    {
        "name": "web_embedded",
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB_EMBEDDED_PLAYER",
                "clientVersion": "1.20241126.01.00",
            }
        },
    },
]

_PLAYER_URL = "https://www.youtube.com/youtubei/v1/player"


def _get_caption_tracks(video_id: str) -> list[dict]:
    """Use InnerTube player endpoint to find caption track URLs."""
    for client in _INNERTUBE_CLIENTS:
        payload = {
            "videoId": video_id,
            "context": client["context"],
        }
        headers = {"Content-Type": "application/json"}
        try:
            r = requests.post(_PLAYER_URL, json=payload, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {})
            tracks = captions.get("captionTracks", [])
            if tracks:
                print(f"  Found {len(tracks)} caption tracks via {client['name']}")
                return tracks
        except Exception as e:
            print(f"  {client['name']} player failed: {e}")
    return []


def _download_timed_text(base_url: str) -> list[dict]:
    """Download and parse a timedtext XML or JSON3 track."""
    # Request json3 format
    url = base_url + "&fmt=json3"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    chunks = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        start_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 0)
        chunks.append({
            "text": text,
            "start": start_ms / 1000.0,
            "duration": dur_ms / 1000.0,
        })
    return chunks


def _try_xml_timed_text(base_url: str) -> list[dict]:
    """Try fetching in srv3 XML format as fallback."""
    import xml.etree.ElementTree as ET
    url = base_url + "&fmt=srv3"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    chunks = []
    for p in root.iter("p"):
        text = "".join(p.itertext()).strip()
        if not text:
            continue
        start_ms = int(p.get("t", 0))
        dur_ms = int(p.get("d", 0))
        chunks.append({
            "text": text,
            "start": start_ms / 1000.0,
            "duration": dur_ms / 1000.0,
        })
    return chunks


def fetch_innertube(video_id: str) -> list[dict]:
    """Fetch transcript via InnerTube API."""
    tracks = _get_caption_tracks(video_id)
    if not tracks:
        raise RuntimeError(f"No caption tracks found for {video_id}")

    # Prefer manual English captions, fall back to auto-generated
    en_tracks = [t for t in tracks if t.get("languageCode", "").startswith("en")]
    if not en_tracks:
        raise RuntimeError(f"No English captions for {video_id}")

    # Sort: manual first, then auto
    en_tracks.sort(key=lambda t: t.get("kind", "") == "asr")
    track = en_tracks[0]
    kind = "auto-generated" if track.get("kind") == "asr" else "manual"
    print(f"  Using {kind} English track")

    base_url = track["baseUrl"]
    try:
        chunks = _download_timed_text(base_url)
    except Exception:
        print("  json3 format failed, trying srv3 XML …")
        chunks = _try_xml_timed_text(base_url)

    if not chunks:
        raise RuntimeError(f"Caption track was empty for {video_id}")

    return chunks


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/fetch_transcript_innertube.py <VIDEO_ID>")
        sys.exit(1)

    video_id = sys.argv[1]
    print(f"Fetching transcript for {video_id} via InnerTube API …")

    chunks = fetch_innertube(video_id)
    print(f"Got {len(chunks)} raw chunks")

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _CACHE_DIR / f"{video_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=1)
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    main()
