# Governance Notes — Sprint 1

> **Project:** GenASL — AI-Powered ASL Overlay Generator (Student POC)
> **Sprint:** 1 — Foundation & Feasibility
> **Last updated:** 2026-02-25

---

## 1. Unsupported Use Categories

The current system is scoped to a **50-sentence Supported Set** of everyday conversational English. The allowlist-only gate in the matcher forces any unmatched text to fall back to `action="CAPTIONS"`. The following categories are explicitly out of scope:

| Category | Risk Level | Rationale | Enforcement Mechanism |
|----------|-----------|-----------|----------------------|
| **Medical / Legal content** | **High** | Mistranslation of medical instructions, dosage information, or legal rights could cause direct harm to DHH viewers. The POC's 50-sentence vocabulary cannot cover specialised terminology. | Allowlist-only gate: any medical/legal sentence will not match a supported sentence above the 0.80 threshold and will automatically receive `action="CAPTIONS"`, `sentence_id=null`. |
| **Emergency alerts** | **High** | Incorrect or delayed rendering of emergency information (weather alerts, evacuation orders, Amber alerts) poses safety risks. Real-time latency and accuracy requirements far exceed POC capabilities. | Allowlist-only gate: emergency-specific language is absent from the Supported Set, guaranteeing CAPTIONS fallback. Additionally, the pipeline is offline/batch — it cannot serve real-time alerts. |
| **Open-ended vocabulary** | **Medium** | Arbitrary unconstrained text increases the probability of semantically incorrect ASL matches, producing misleading overlay content. | Allowlist-only gate: the FAISS matcher can only return sentence_ids present in the 50-row Supported Set. Any input beyond that vocabulary falls below the confidence threshold and receives CAPTIONS. |

---

## 2. Disclosure Label

### Finalized Text

> **"AI-generated ASL avatar (POC)"**

### Placement

The label must be displayed as a persistent overlay in the lower-right corner of the video frame whenever an ASL asset is rendered. It must remain visible for the full duration of each ASL segment.

### CVAA / ADA Rationale

- The **21st Century Communications and Video Accessibility Act (CVAA)** requires that advanced communications services and video programming be accessible to people with disabilities. A clear disclosure ensures viewers understand the ASL content is machine-generated, not produced by a certified interpreter.
- The **Americans with Disabilities Act (ADA)** effective communication standard requires that auxiliary aids be clearly identified so that viewers can make informed decisions about reliance on the content.
- Transparent labelling reduces the risk of viewers treating POC-level output as equivalent to certified human interpretation.

### Sprint 2 Implementation Note

In Sprint 2, the disclosure label will be composited into the video overlay by the render engine. For Sprint 1 the label is included as a metadata field in the render plan JSON but is not yet visually rendered.

---

## 3. Data Source Compliance

| Component | License / Terms | Notes |
|-----------|----------------|-------|
| **youtube-transcript-api** | MIT License (open-source Python library) | Fetches publicly available auto-generated or manually uploaded captions. No YouTube Data API key required. |
| **YouTube Transcripts** | YouTube Terms of Service — **Section 5B** | Section 5B restricts automated access to YouTube content for commercial purposes. This POC is a non-commercial student project. **Before any production deployment**, legal review of YouTube ToS Section 5B is required, and the project should migrate to the official YouTube Data API v3 with proper API key and quota management. |
| **all-MiniLM-L6-v2** | Apache License 2.0 | Sentence-transformer model from Hugging Face. Apache 2.0 permits use, modification, and distribution with attribution. |
| **FAISS** | MIT License | Facebook AI Similarity Search library. MIT permits unrestricted use with attribution. |

---

## 4. Citation Gap — Action Required

### Issue

The current scope document is missing in-text citations in several critical sections. Academic integrity requires that all factual claims, statistics, and framework references include proper citations before the final submission.

### Priority Sections Requiring Citations

1. **Opportunity Assessment** — Statistics on DHH population size, video accessibility gaps, and market opportunity claims need primary source citations (e.g., WHO, NAD, Pew Research).
2. **OKRs (Objectives and Key Results)** — Benchmark targets (e.g., confidence thresholds, match-rate goals) should cite the source studies or industry standards they are derived from.
3. **Responsible AI Assessment** — References to CVAA, ADA, and Microsoft RAI principles need formal in-text citations with corresponding bibliography entries.

### Assignment

| Team Member | Responsibility | Deadline |
|-------------|---------------|----------|
| **Team Member 1** | Sections 1 & 2 (Opportunity Assessment, OKRs) | Before Sprint 3 kickoff |
| **Team Member 2** | Section 3 (Responsible AI Assessment) | Before Sprint 3 kickoff |

Both team members should cross-review the other's citations before final submission.

---

## 5. Sprint 1 RAI Checkpoint

Both team members must review and sign off on each item below before Sprint 1 is considered complete.

- [ ] Allowlist-only gate is implemented and tested (matcher forces CAPTIONS for unmatched text)
- [ ] Confidence threshold (0.80) is enforced and logged on every segment
- [ ] CAPTIONS fallback includes a WARNING-level log entry with the original text and score
- [ ] Disclosure label text ("AI-generated ASL avatar (POC)") is documented and agreed upon
- [ ] Unsupported use categories (medical/legal, emergency, open-ended) are documented with risk levels
- [ ] Data source licenses (youtube-transcript-api MIT, MiniLM Apache 2.0, FAISS MIT, YouTube ToS 5B) are reviewed and recorded
