# Sprint 3 Plan — End-to-End Overlay, Pilot & Final Demonstration

**Sprint dates:** Mar 4–11, 2026  
**Team:** Yijie Ren, Sanchit Arora

---

## Sprint Goal

Fix the two normalization issues carried over from Sprint 2, build the Picture-in-Picture overlay compositor and a simple web UI, run a small pilot with 5–10 users, and deliver a final end-to-end demonstration — achieving >50% positive pilot feedback, transparency disclosure label noticed by ≥80% of users, and a completed responsible AI assessment with in-text citations throughout all documentation.

---

## Value Delivered

- **DHH viewers** see a working demonstration of ASL clip overlays playing in sync with a real YouTube video, with captions always preserved — the first tangible proof of the viewing experience the product promises
- **Streaming platforms** receive evidence that the system correctly scopes itself to approved content, falls back gracefully, and meets transparency requirements (CVAA/ADA disclosure label)
- **Content creators** see a pipeline that requires no changes to their existing content — just a YouTube URL in, accessible video out

---

## Sprint Backlog

| Feature | Task Name | Task Description | Acceptance Criteria | Priority | Effort | Owner |
|---|---|---|---|---|---|---|
| Normalization Fix | Revert confidence threshold to 0.80 and document | Reset the threshold in config back to 0.80. Add a comment explaining what the threshold means and the responsible AI reason it should not be lowered without review. Re-run the pipeline on the test video and compare ASL match count before and after. | Threshold is 0.80 in config with explanatory comment. Re-run shows no borderline matches below 0.80 accepted. Match count difference documented. **RAI:** Allowlist gate restored to designed specification. | High | S | Sanchit |
| Normalization Fix | Strip bracket tags and filter short segments | Update the transcript normalization step to remove any text inside square brackets (e.g., [music], [applause]) before matching. Filter out segments shorter than 2 seconds or containing fewer than 3 words. Re-run and confirm previously missed matches are now correctly recovered. | Bracket-stripped segments produce correct match scores. Previously missed matches now returning action: ASL. Short artifact segments no longer reaching the matcher. Tested on the Sprint 2 test video. | High | S | Sanchit |
| Overlay Compositor | Build Picture-in-Picture overlay compositor | Using FFmpeg, build the compositor that reads the original YouTube video and the enriched render plan, and overlays each matched ASL clip in a PiP window (bottom-right corner, ~25% of screen width) at the exact start timestamp. For CAPTIONS segments, no overlay is shown. Original captions are always preserved and never removed. | Output video plays correctly with PiP ASL clips at the right timestamps. Captions preserved throughout. Tested on the Sprint 2 test video end-to-end. **RAI:** Captions never suppressed — verified by checking a CAPTIONS segment in output. | High | L | Sanchit |
| Overlay Compositor | Handle overlapping segment timestamps | When two consecutive ASL segments overlap in time, show only the higher-scoring match and skip the lower-scoring one. Log each resolved conflict with the segment IDs and scores. | No two ASL clips play simultaneously in the output video. Conflicts logged with segment ID and score. Tested with a manufactured overlap case. | Medium | M | Sanchit |
| UI | Build simple web UI | Using Streamlit, build a minimal web interface where a user enters a YouTube video ID, clicks Run, and the output video with PiP ASL overlay is produced and displayed. Show a run summary below the video. The disclosure label "AI-generated ASL avatar (POC)" must be visible on screen at all times during playback — burned into the video itself, not just UI chrome. | UI launches with one command. A real YouTube video ID produces an output video. Run summary appears. Disclosure label visible on the video during playback. **RAI:** Label confirmed present in output video. | High | L | Sanchit |
| Pilot | Recruit and brief pilot users | Identify 5–10 people willing to test the tool. Brief each one: this is a student POC, word-level clips only, known limitations disclosed. Prioritize recruiting at least 1–2 people from the DHH community or with ASL experience. If no DHH participants are available, document this as a pilot limitation. | ≥5 users confirmed and briefed before sessions begin. Recruitment approach and participant profile documented. Known limitations disclosed to all participants before testing. **RAI:** Informed consent — participants know what they are testing. | High | M | Yijie |
| Pilot | Run pilot sessions and collect feedback | Have each participant watch the output video with PiP overlay active. Collect feedback using the standard form: 1–5 star rating, issue checkboxes, free-text notes, and disclosure label noticed yes/no. | Feedback form completed by ≥5 participants. All responses recorded anonymously — no personally identifiable information retained. **RAI:** Privacy requirement met. | High | M | Yijie |
| Pilot | Analyze pilot results and document | Tally all feedback. Calculate percentage of positive ratings (4–5 stars). Identify most common issue. Calculate what percentage of users noticed the disclosure label. Document full results including honest interpretation. | Results documented with positive rating percentage, most common issue, and disclosure label noticed percentage. Both members review before submission. | High | M | Yijie |
| Responsible AI | Complete Sprint 3 RAI assessment | Update governance notes with a final Sprint 3 section: updated risk matrix with pilot evidence, transparency label confirmation percentage, fairness limitations, privacy confirmation, sustainability note on compute usage. | Governance notes updated and committed. All six RAI checkpoint items confirmed. Risk matrix reflects actual Sprint 3 findings. | High | M | Yijie |
| Documentation | Add in-text citations to scope document | Go through the AI Proof of Concept Scope Document and add in-text citations for all factual claims. Priority sections: Opportunity Assessment, OKRs, and Responsible AI Assessment. This was flagged as missing since Sprint 1 — must be resolved before submission. | At least 5 in-text citations added across the three priority sections. No factual claim left unsupported. Both members review. | High | M | Yijie |

---

## Effort Totals

| Owner | Tasks | Breakdown | Total |
|---|---|---|---|
| **Sanchit** | Threshold fix, bracket stripping, compositor, overlap handling, Streamlit UI | S + S + L + M + L | **~9h** ✅ |
| **Yijie** | Pilot recruitment, pilot sessions, results analysis, RAI assessment, citations | M + M + M + M + M | **~10h** ✅ |

---

## Responsible AI Controls — Sprint 3 Verification

Before the sprint closes, both members must confirm:

- [ ] Confidence threshold confirmed at 0.80 with documented rationale
- [ ] Disclosure label "AI-generated ASL avatar (POC)" visible in output video at all times during playback
- [ ] Original captions preserved alongside overlay — never removed
- [ ] Pilot participants briefed on limitations before testing (informed consent)
- [ ] Pilot feedback stored anonymously — no personally identifiable information retained
- [ ] Known limitations (word-level only, no ASL grammar, not reviewed by Deaf community member) disclosed in both pilot briefing and final documentation
- [ ] RAI risk matrix updated with Sprint 3 pilot evidence
- [ ] In-text citations added to scope document

---

## Sprint 3 Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| FFmpeg PiP compositor is harder to build than estimated | Medium | Sanchit runs a 30-minute spike on Day 1 using a 10-second test clip and a single hardcoded overlay before building the full compositor. If FFmpeg PiP proves unworkable, fall back to a side-by-side layout. |
| Pilot recruitment delayed, especially DHH participants | Medium | Yijie starts outreach on Day 1. If no DHH participants are available by Day 3, proceed with hearing participants and document the limitation explicitly. |
| Pilot feedback below 50% positive due to word-level limitation | Low-Medium | Set expectations in the briefing — this is a proof of concept, not a finished product. Frame feedback around the concept and pipeline, not production quality. |
| In-text citations require re-researching sources | Low | Use the three references already in the scope document as anchors. Add 2–3 new sources for DHH population statistics and OKR benchmarks. |

---

## Definition of Done

- [ ] Confidence threshold at 0.80 with comment in config
- [ ] Bracket tag stripping and short segment filter active and tested
- [ ] PiP compositor produces a watchable output video on the test clip
- [ ] Streamlit UI accepts a YouTube video ID and produces the overlay output
- [ ] Disclosure label visible on the output video at all times during playback
- [ ] Pilot conducted with ≥5 users, feedback collected anonymously
- [ ] Pilot results documented with positive rating percentage and disclosure label noticed percentage
- [ ] RAI assessment updated with Sprint 3 pilot evidence
- [ ] In-text citations added to scope document
- [ ] Final demo video recorded showing end-to-end functionality
