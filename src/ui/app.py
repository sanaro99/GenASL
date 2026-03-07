"""GenASL — Streamlit web UI.

Launch with::

    streamlit run src/ui/app.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
import streamlit as st

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.pipeline.run_pipeline import run as run_pipeline  # noqa: E402
from src.compositor.downloader import download_source_video  # noqa: E402
from src.compositor.compositor import compose_pip  # noqa: E402

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _load_test_videos() -> list[dict]:
    """Load test video list from config.yaml."""
    cfg_path = _PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return cfg.get("test_videos", [])


# ---------------------------------------------------------------------------
# Streamlit page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="GenASL — ASL Overlay POC", layout="wide")

st.title("GenASL — ASL Overlay POC (GenAI)")
st.markdown(
    "Enter a YouTube video ID or select a test video to generate a Picture-in-Picture "
    "ASL overlay using **LLM-powered English-to-ASL gloss translation** and "
    "**word-level clip chaining**."
)

# ---------------------------------------------------------------------------
# Input — test video selector + manual entry
# ---------------------------------------------------------------------------
test_videos = _load_test_videos()
test_options = ["(enter manually)"] + [
    f"{v['id']} — {v['title']}" for v in test_videos
]
selection = st.selectbox("Select a test video", test_options)

if selection == "(enter manually)":
    video_id = st.text_input("YouTube Video ID", value="", max_chars=11)
else:
    video_id = selection.split(" — ")[0].strip()
    st.info(f"Selected: **{video_id}**")

run_button = st.button("Run Pipeline")

if run_button:
    if not video_id or not _VIDEO_ID_RE.match(video_id):
        st.error("Please enter a valid 11-character YouTube video ID.")
    else:
        # ── Stage 1: Pipeline ──────────────────────────────────────
        with st.spinner("Running pipeline (transcript → match → render plan) …"):
            try:
                plan = run_pipeline(video_id)
            except Exception as exc:
                st.error(f"Pipeline failed: {exc}")
                st.stop()

        # ── Stage 2: Download source video ─────────────────────────
        with st.spinner("Downloading source video …"):
            try:
                source_video = download_source_video(video_id)
            except Exception as exc:
                st.error(f"Video download failed: {exc}")
                st.stop()

        # ── Stage 3: Composite PiP overlay ─────────────────────────
        with st.spinner("Compositing PiP overlay …"):
            try:
                output_video = compose_pip(source_video, plan)
            except Exception as exc:
                st.error(f"Compositing failed: {exc}")
                st.stop()

        # ── Display results ────────────────────────────────────────
        st.success("Pipeline complete!")
        st.video(str(output_video))

        # ── Run summary ────────────────────────────────────────────
        summary = plan["summary"]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Segments", summary["total_segments"])
        col2.metric("ASL Segments", summary["asl_segments"])
        col3.metric("Captions Segments", summary["captions_segments"])
        col4.metric("Filtered", summary.get("filtered_segments", 0))

        st.markdown("---")
        pipeline_info = plan.get("pipeline", {})
        st.markdown(
            f"**Run ID:** `{plan['run_id']}`  \n"
            f"**Mode:** {pipeline_info.get('mode', 'n/a')}  \n"
            f"**LLM Model:** {pipeline_info.get('model', 'n/a')}  \n"
            f"**Timing overlaps detected:** {summary.get('timing_overlaps', 0)}  \n"
            f"**Overlaps resolved:** {summary.get('overlaps_resolved', 0)}"
        )

        # Show gloss details per segment
        with st.expander("Segment Gloss Details"):
            for seg in plan.get("segments", []):
                match_info = seg.get("match", {})
                action = match_info.get("action", "?")
                gloss_text = match_info.get("gloss_text", "")
                found = match_info.get("found_glosses", [])
                missing = match_info.get("missing_glosses", [])
                st.markdown(
                    f"**{seg['segment_id']}** [{action}] "
                    f"*\"{seg['source_text'][:80]}\"*  \n"
                    f"Gloss: `{gloss_text}`  \n"
                    f"Found: {', '.join(found) if found else 'none'} | "
                    f"Missing: {', '.join(missing) if missing else 'none'}"
                )

        st.markdown(
            "> **Disclosure:** This output uses AI-generated ASL overlay clips "
            "from the WLASL academic dataset. Word-level clips only — not "
            "grammatically correct ASL. See governance notes for full limitations."
        )
