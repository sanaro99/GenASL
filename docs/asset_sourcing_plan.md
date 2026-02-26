# Asset Sourcing Plan

> **Project:** GenASL — AI-Powered ASL Overlay Generator (Student POC)
> **Purpose:** Evaluate options for obtaining ASL animation/video assets for the 50-sentence Supported Set, and define a practical path for Sprint 2.

---

## Option A: JASigning + SiGML

### Description

[JASigning](http://vh.cmp.uea.ac.uk/index.php/JASigning) is an open-source avatar-based signing system that renders sign language animations from **SiGML** (Signing Gesture Markup Language) XML files. Each sentence would be authored as a SiGML document and rendered through the JASigning avatar engine.

### Effort Estimate (50 files)

| Task | Estimate |
|------|----------|
| JASigning environment setup & configuration | 4–6 hours |
| Learning SiGML authoring conventions | 6–8 hours |
| Authoring 50 SiGML files (avg 30 min each) | 25–30 hours |
| Rendering and quality review | 4–6 hours |
| **Total** | **39–50 hours** |

### Learning Curve Risk

**High.** SiGML is a niche XML dialect with limited documentation and community support. Neither team member has prior experience. Debugging avatar rendering issues could consume significant time. This option is not recommended for a 2-sprint POC timeline.

---

## Option B: Pre-recorded Video Clips

### Description

Use real video clips of a human signer or leverage existing ASL datasets. Two sub-options:

#### B1. Existing Datasets

- **ASLLVD** (American Sign Language Lexical Video Dataset) — word-level clips from Gallaudet University. Covers individual signs but not full sentences.
- **MS-ASL** (Microsoft ASL dataset) — sentence/phrase-level clips. Larger coverage but access requires a data use agreement.

**Limitation:** Both datasets are word- or phrase-level; composing full sentence clips from individual signs requires additional editing and may produce unnatural signing.

#### B2. Recording Own Clips

Record a team member or volunteer performing each of the 50 sentences in ASL. Requires basic video recording equipment, consistent framing/lighting, and ideally review by someone fluent in ASL.

### Effort Estimate (50 clips)

| Task | Estimate |
|------|----------|
| Setup recording environment | 2–3 hours |
| Record 50 clips (avg 3 min each incl. retakes) | 3–4 hours |
| Post-processing (trim, normalize, export MP4) | 4–6 hours |
| ASL accuracy review | 3–4 hours |
| **Total** | **12–17 hours** |

---

## Recommended Approach

> **Use 10 placeholder MP4 clips to unblock Sprint 2 pipeline testing, then iteratively replace with real assets.**

### Rationale

- Sprint 2's primary goal is end-to-end pipeline integration (transcript → match → overlay render). Asset quality is secondary at this stage.
- 10 placeholder clips (e.g., solid-colour frames with sentence text overlay, or short stock clips) are sufficient to validate the render engine, timing logic, and output format.
- Real assets (Option B2 — self-recorded clips) can be produced in parallel and swapped in without changing the pipeline code.

### Placeholder Spec

| Property | Value |
|----------|-------|
| Format | MP4, H.264 |
| Resolution | 480 × 480 px |
| Duration | Matches `duration_ms` from `supported_set_v1.csv` |
| Content | Solid background with `sentence_id` + `english_text` as centred white text |
| Naming | `A001.mp4` … `A010.mp4` |

---

## Per-Asset QA Checklist

Each asset (placeholder or final) must pass the following checks before being marked `qa_status="approved"` in the Supported Set CSV:

- [ ] File exists at the expected path (`assets/<asset_id>.mp4`)
- [ ] File plays without errors in VLC / browser `<video>` element
- [ ] Duration matches `duration_ms` in `supported_set_v1.csv` (± 200 ms tolerance)
- [ ] Resolution is at least 480 × 480 px
- [ ] Signing content accurately represents the `english_text` (verified by ASL-fluent reviewer for final assets)
- [ ] File size is under 5 MB per clip

---

## Sprint 2 Timeline Estimate

Based on **8–10 hours per person** available in Sprint 2:

| Task | Owner | Hours |
|------|-------|-------|
| Create 10 placeholder MP4 clips | Member 1 | 2–3 |
| Implement render engine (overlay compositor) | Member 2 | 4–5 |
| Integrate render engine with pipeline (`run_pipeline.py`) | Member 1 | 2–3 |
| End-to-end test with placeholder assets | Both | 2–3 |
| Begin recording real ASL clips (stretch goal) | Member 1 | 3–4 |
| Update `qa_status` and asset metadata | Member 2 | 1–2 |
| **Total** | | **14–20 hours** |
