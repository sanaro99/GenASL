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
        # compositor.py still consumes a dict; pass through model_dump().
        with st.spinner("Compositing PiP overlay …"):
            try:
                output_video = compose_pip(source_video, plan.model_dump())
            except Exception as exc:
                st.error(f"Compositing failed: {exc}")
                st.stop()

        # ── Display results ────────────────────────────────────────
        st.success("Pipeline complete!")
        st.video(str(output_video))

        # ── Run summary ────────────────────────────────────────────
        summary = plan.summary
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Segments", summary.total_segments)
        col2.metric("ASL Segments", summary.asl_segments)
        col3.metric("Captions Segments", summary.captions_segments)
        col4.metric("Filtered", summary.filtered_segments)

        st.markdown("---")
        st.markdown(
            f"**Run ID:** `{plan.run_id}`  \n"
            f"**Mode:** {plan.pipeline.mode}  \n"
            f"**Provider / Model:** {plan.pipeline.provider} / {plan.pipeline.model}  \n"
            f"**Timing overlaps detected:** {summary.timing_overlaps}  \n"
            f"**Overlaps resolved:** {summary.overlaps_resolved}"
        )

        # Show gloss details per segment
        with st.expander("Segment Gloss Details"):
            for seg in plan.segments:
                m = seg.match
                st.markdown(
                    f"**{seg.segment_id}** [{m.action}] "
                    f"*\"{seg.source_text[:80]}\"*  \n"
                    f"Gloss: `{m.gloss_text}`  \n"
                    f"Found: {', '.join(m.found_glosses) if m.found_glosses else 'none'} | "
                    f"Missing: {', '.join(m.missing_glosses) if m.missing_glosses else 'none'}"
                )

        st.markdown(
            "> **Disclosure:** This output uses AI-generated ASL overlay clips "
            "from the WLASL academic dataset. Word-level clips only — not "
            "grammatically correct ASL. See governance notes for full limitations."
        )
