# Sprint 2 Retrospective — ASL Clip Acquisition, Asset Pipeline & Timed Render Planning

**Sprint dates:** Feb 25 – Mar 4, 2026  
**Team:** Yijie Ren, Sanchit Arora

---

## Sprint Goal

Source and QA 50 word-level ASL video clips from the WLASL open academic dataset — one per Supported Set sentence — integrate them into the Sprint 1 render plan to produce a time-aligned asset render plan, and validate the full mapping path end-to-end on a 60–90s test clip with run logging active and raw media deletion confirmed.

---

## What We Accomplished

### Asset Acquisition — Final State

| Area | Target | Delivered |
|---|---|---|
| Sentence clips from WLASL | 50 | **48/50 (96%)** |
| Placeholders remaining | 0 | **2** (PASSWORD, DO — not in WLASL) |
| Signer consistency | — | **44/50 clips from signer 9** (asl5200) |
| Descriptive filenames | — | ✅ e.g. `A001_S001_GUM.mp4` |
| Manifest version | 1.0 | **2.0** (with `signer_id` per asset) |
| Word-level asset library | Not planned | **241 words added** |
| Total tests passing | — | **21 tests** ✅ |

### Pipeline & Infrastructure

- Multi-instance retry logic built for clip downloading — all available WLASL instances are tried before falling back to placeholder, eliminating the original single-attempt failure that left 21 placeholders
- Signer preference chain configured, ensuring visual consistency across clips — 44 of 50 sentence assets feature the same signer
- Render plan enriched with clip metadata: file path, duration, frame rate, and signer ID per ASL segment
- Timing overlap detection active and confirmed zero overlaps on test run
- Run logging updated to capture assets used, placeholder count, and timing overlap count
- Word-level asset library of 241 common vocabulary words built as a separate downloadable set with its own manifest, ready for future phrase-chaining work in production
- Raw source clips deleted after QA; no raw media retained

### Governance

- Scope change rationale formally documented — why 3D avatar renderer was replaced with word-level video clips
- Known POC limitation documented — word-level clips do not capture ASL sentence grammar or spatial nuance
- WLASL dataset citation added: Dongxu Li et al., WACV 2020
- Cultural sensitivity note added — clips not reviewed by a Deaf community member

---

## Key Metrics from Pipeline Test Run (video `E-gGacOpjCA`)

| Metric | Value |
|---|---|
| Total segments processed | 51 |
| ASL matched | 32 (62.75%) |
| Captions fallback | 19 (37.25%) |
| Timing overlaps | 0 |
| Confidence threshold used | 0.70 ⚠️ (should be 0.80) |
| Placeholders used in matched segments | 0 |

---

## What Went Well

- **Signer consistency made a big difference.** Switching from a single-instance attempt to a ranked multi-instance retry with signer preference dropped placeholder count from 21 to 2. The visual experience is now far more coherent — 44 clips feature the same signer with consistent framing and background.
- **The matcher performs well on ASL word order.** The test run revealed that the FAISS matcher correctly scores ASL-order phrasing higher than English phrasing — for example "pencil borrow, please" scored 0.98 while the English "can I borrow a pencil?" scored 0.85. This is an emergent, positive behavior.
- **Word-level library adds real future value.** The 241-word asset library was not in the original sprint scope but was delivered at zero pipeline risk. It creates a foundation for phrase-chaining in a production system without requiring any rework of the current architecture.
- **Zero timing overlaps on a 6.5-minute video.** The timing validation held cleanly across 51 segments with no clip overflow — the Sprint 3 compositor can trust the render plan timing.

---

## What Didn't Go Well

**Issue 1 — Confidence threshold lowered without documentation (Critical)**  
The threshold was changed from 0.80 to 0.70 between Sprint 1 and the test run without a recorded reason. At 0.70, borderline matches slip through — SEG_002 matched a 16-second intro monologue to a Supported Set phrase at only 0.72. This is a responsible AI concern: the allowlist gate is less strict than designed. Must be reverted to 0.80 in Sprint 3 with a documented rationale for any future changes.

**Issue 2 — Bracket tags diluting embeddings (Medium)**  
Transcript segments containing `[music]`, `[applause]`, and similar auto-caption tags are hurting match scores. "Do you need help?" scored 0.58 and fell to CAPTIONS because of the `[music]` prefix, while "help. need you?" (same content, no tag) scored 0.93 and matched correctly. Stripping bracket content during normalization would recover several valid matches per video.

**Issue 3 — Overlapping segment timestamps (Medium)**  
Several consecutive segment pairs have overlapping time ranges — for example SEG_002 (14,880–25,960ms) and SEG_003 (22,080–30,640ms) overlap by ~4 seconds. Both matched the same asset so no visual conflict occurred in Sprint 2, but the Sprint 3 compositor needs an explicit strategy to handle these without showing two clips simultaneously.

**Issue 4 — Short transcript artifact segments (Low)**  
Segments like "cc.", "point.", and "no bar." are auto-caption artifacts that passed through the matcher unnecessarily. A minimum word count or duration filter in normalization would remove these before they reach matching.

---

## Lessons Learned

- Config changes (especially the confidence threshold) must be commented and tracked — they directly affect the responsible AI allowlist gate
- Always test on a full-length real video, not just the short scripted Sprint 1 clip — the 6.5-minute test run surfaced normalization issues the shorter clip would have hidden
- Signer consistency matters more than coverage percentage for user experience — 48/50 real clips with a consistent signer is significantly better than 50/50 with random signers
- Building slightly beyond scope (word-level library) is valuable when it reuses existing infrastructure and does not delay sprint goals

---

## Sprint 3 Readiness Checklist

- [x] 48/50 sentence clips available in final assets folder
- [x] 2 placeholder clips documented (PASSWORD, DO)
- [x] Render plan enriched with clip file path, duration, frame rate, signer ID
- [x] Timing validation active — zero overlaps confirmed
- [x] Asset manifest v2.0 committed with signer tracking
- [x] 241-word asset library available for future use
- [x] Governance notes updated with scope change, limitation, citation
- [x] All 21 tests passing
- [ ] Confidence threshold reverted to 0.80 — **Sprint 3 Day 1**
- [ ] Bracket tag stripping added to normalization — **Sprint 3 Day 1**
