"""PlanStage — assemble the final RenderPlan, run RAI checks, resolve overlaps.

Combines what was, in the legacy ``run_pipeline.py``, three sequential helpers:
``_build_gloss_render_plan``, ``_detect_timing_overlaps``, ``_resolve_overlaps``,
plus the ``_responsible_ai_warnings`` check. Output is :class:`RenderPlan` v4.0.

PlanStage is not disk-cached — its output carries volatile fields (``run_id``,
``generated_at``) and the work itself is tiny once upstream stages are cached.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.pipeline.models import (
    AslOverlayEntry,
    PipelineInfo,
    PlanInput,
    PlanSegment,
    RenderPlan,
    SegmentMatch,
    Summary,
    Timing,
)
from src.pipeline.stages.base import Stage

logger = logging.getLogger(__name__)


class PlanStage(Stage[PlanInput, RenderPlan]):
    """Build the final RenderPlan."""

    name = "plan"
    output_model = RenderPlan

    def fingerprint(self, inp: PlanInput) -> str:
        # PlanStage bypasses the disk cache (volatile run_id) — fingerprint
        # is unused, return a constant for hygiene.
        return "no-cache"

    def run(self, inp: PlanInput, *, use_cache: bool = True) -> RenderPlan:
        # Bypass the base Stage.run cache entirely.
        return self.process(inp)

    def process(self, inp: PlanInput) -> RenderPlan:
        generated_at = datetime.now(timezone.utc).isoformat()

        plan_segments: list[PlanSegment] = []
        overlay_track: list[AslOverlayEntry] = []
        asl_count = 0
        cap_count = 0

        for seg in inp.segments:
            timing = Timing.from_ms(seg.start_ms, seg.end_ms)
            found_count = sum(1 for wc in seg.word_clips if wc.found)
            total_glosses = len(seg.gloss_sequence)
            chained = seg.chained_clip

            if chained and found_count > 0:
                action = "ASL"
                asl_count += 1
                coverage = (
                    round(found_count / total_glosses, 4) if total_glosses else 0.0
                )
            else:
                action = "CAPTIONS"
                cap_count += 1
                coverage = 0.0

            match = SegmentMatch(
                action=action,
                gloss_sequence=seg.gloss_sequence,
                gloss_text=seg.gloss_text,
                word_coverage=coverage,
                found_glosses=[wc.gloss for wc in seg.word_clips if wc.found],
                missing_glosses=[wc.gloss for wc in seg.word_clips if not wc.found],
                chained_clip_path=chained.rel_path if chained else None,
                chained_duration_ms=chained.duration_ms if chained else None,
                chained_clip_count=chained.clip_count if chained else 0,
            )
            plan_segments.append(PlanSegment(
                segment_id=seg.segment_id,
                source_text=seg.text,
                timing=timing,
                match=match,
            ))

            if action == "ASL" and chained:
                overlay_track.append(AslOverlayEntry(
                    segment_id=seg.segment_id,
                    start_ms=seg.start_ms,
                    end_ms=seg.end_ms,
                    start_tc=timing.start_tc,
                    end_tc=timing.end_tc,
                    asset_file_path=chained.rel_path,
                    asset_duration_ms=chained.duration_ms,
                    score=coverage,
                    gloss_sequence=seg.gloss_sequence,
                    kept=True,
                ))

        filtered_plan: list[PlanSegment] = []
        for fseg in inp.filtered:
            timing = Timing.from_ms(fseg.start_ms, fseg.end_ms)
            filtered_plan.append(PlanSegment(
                segment_id=fseg.segment_id,
                source_text=fseg.text,
                timing=timing,
                match=SegmentMatch(action="FILTERED", reason="short_or_artefact"),
            ))

        total = asl_count + cap_count
        summary = Summary(
            total_segments=total,
            asl_segments=asl_count,
            captions_segments=cap_count,
            filtered_segments=len(filtered_plan),
            asl_ratio=round(asl_count / total, 4) if total else 0.0,
        )

        overlaps, resolved = self._handle_overlaps(overlay_track)
        summary.timing_overlaps = overlaps
        summary.overlaps_resolved = resolved

        plan = RenderPlan(
            run_id=inp.run_id,
            video_id=inp.video_id,
            generated_at=generated_at,
            pipeline=PipelineInfo(provider=inp.provider, model=inp.model),
            summary=summary,
            segments=plan_segments,
            filtered_segments=filtered_plan,
            asl_overlay_track=overlay_track,
        )

        self._rai_check(plan)
        return plan

    # --- Helpers ------------------------------------------------------

    def _rai_check(self, plan: RenderPlan) -> None:
        summary = plan.summary
        total = summary.total_segments
        asl = summary.asl_segments

        if total == 0:
            logger.warning(
                "RAI WARNING: 0 segments for video %s — verify transcript availability.",
                plan.video_id,
            )
            return
        ratio = asl / total
        warn_at = self.settings.pipeline.high_asl_ratio_warn
        if ratio > warn_at:
            logger.warning(
                "RAI WARNING: %.0f%% of segments matched to ASL (%d/%d). "
                "This is suspiciously high — review match quality.",
                ratio * 100, asl, total,
            )

    def _handle_overlaps(self, track: list[AslOverlayEntry]) -> tuple[int, int]:
        """Detect timing overlaps, then resolve by keeping the higher-scoring entry.

        Returns ``(overlap_count, resolved_count)``.
        """
        # Detect
        overlap_count = 0
        for i in range(len(track) - 1):
            cur, nxt = track[i], track[i + 1]
            cur_end = cur.start_ms + cur.asset_duration_ms
            if cur_end > nxt.start_ms:
                overlap_ms = cur_end - nxt.start_ms
                overlap_count += 1
                logger.warning(
                    "TIMING OVERLAP: %s (start=%d + dur=%d = %d) overflows into "
                    "%s (start=%d) by %d ms",
                    cur.segment_id, cur.start_ms, cur.asset_duration_ms, cur_end,
                    nxt.segment_id, nxt.start_ms, overlap_ms,
                )
        if overlap_count:
            logger.warning("Total timing overlaps detected: %d", overlap_count)
        else:
            logger.info("Timing validation passed — no overlaps detected")

        # Resolve
        resolved = 0
        i = 0
        while i < len(track) - 1:
            cur = track[i]
            nxt = track[i + 1]
            if not cur.kept:
                i += 1
                continue
            cur_end = cur.start_ms + cur.asset_duration_ms
            if cur_end > nxt.start_ms:
                if cur.score >= nxt.score:
                    loser, winner = nxt, cur
                else:
                    loser, winner = cur, nxt
                loser.kept = False
                winner.kept = True
                resolved += 1
                logger.info(
                    "OVERLAP RESOLVED: kept %s (score=%.4f), dropped %s (score=%.4f)",
                    winner.segment_id, winner.score,
                    loser.segment_id, loser.score,
                )
            i += 1
        if resolved:
            logger.info("Total overlaps resolved: %d", resolved)
        return overlap_count, resolved
