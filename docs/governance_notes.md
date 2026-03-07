# GenASL — Governance & Design Notes

## Sprint 2: ASL Asset Pipeline

### Why word-level video clips (not a 3-D avatar)?

Several open-source avatar systems exist (e.g. JASigning / SiGML), but they
introduce heavy dependencies (Java, BML/SiGML toolchains) and produce
robotic-looking output that Deaf community members have consistently rated as
less natural than human signers.  For this POC the fastest path to a credible
demo is to overlay **real human signing clips** sourced from an academic
dataset.  An avatar approach can be revisited in a later sprint once grammar
reordering is in place.

### Known limitation — no ASL grammar reordering

ASL has its own syntax (topic–comment, spatial referencing, non-manual markers).
Sprint 2 uses a naïve **word-for-word keyword substitution** model: each
English caption keyword is mapped to a single sign clip.  This is **not**
grammatically correct ASL.  The limitation is documented here and will be
addressed in a future sprint that adds a lightweight gloss-reordering layer.

### WLASL dataset citation

> Dongxu Li, Cristian Rodriguez, Xin Yu, and Hongdong Li.
> "Word-level Deep Sign Language Recognition from Video: A New Large-scale
> Dataset and Methods Comparison."  *Proceedings of the IEEE/CVF Winter
> Conference on Applications of Computer Vision (WACV)*, 2020.
> <https://dxli94.github.io/WLASL/>

The WLASL v0.3 dataset (2 000 glosses) is used under its original academic
license for non-commercial research.  Only the publicly hosted video URLs are
consumed; no proprietary data is redistributed.

### Cultural sensitivity

ASL is a full natural language with its own grammar, regional dialects, and
cultural norms.  This project does **not** claim to produce fluent ASL
translation.  The overlay is labelled "word-level ASL keywords" in all outputs
to set appropriate expectations.  Future work should involve consultation with
Deaf community members and professional ASL interpreters before any
production-facing release.

### Data-handling & privacy

- Raw and intermediate clips are deleted after QA (see `docs/asset_qa_notes.md`).
- Only final, approved clips (50 files) are retained in `assets/final/`.
- No personally identifiable information is stored in the asset manifest or
  render plan.

---

## Sprint 3: End-to-End Overlay, Pilot & Responsible AI

### Confidence threshold restoration

The matcher confidence threshold was reverted from 0.70 (undocumented Sprint 2
change) back to the designed value of **0.80**.  At 0.70, borderline matches
slipped through the allowlist gate — for example, a 16-second intro monologue
matched a Supported Set phrase at only 0.72 (Sprint 2 retro Issue 1).

The threshold is now documented in `config.yaml` with an explanatory comment
block covering its purpose, RAI rationale, and change history.  Any future
change must be reviewed and recorded in this document.

### Transcript normalization fixes

Two normalization issues were resolved:

1. **Bracket tag stripping:** Auto-caption tags like `[music]` and `[applause]`
   were diluting sentence embeddings and suppressing valid matches.  The
   normaliser now strips all `[…]` content before embedding.  This recovered
   previously missed matches (e.g. "Do you need help?" went from 0.58 to a
   correct ASL match).

2. **Short segment filter:** Artefact segments with fewer than 3 words or
   shorter than 2 seconds (e.g. "cc.", "point.") are now filtered before
   reaching the matcher.  These are logged as `action: "FILTERED"` in the
   render plan for transparency.

### Overlap resolution

When consecutive ASL overlay clips overlap in time, the pipeline now
automatically resolves the conflict by keeping the higher-scoring match and
marking the lower-scoring entry as `kept: False`.  Each resolution is logged
with segment IDs and scores.  The compositor skips non-kept entries, ensuring
no two ASL clips play simultaneously.

### Transparency / disclosure label

The disclosure label **"AI-generated ASL overlay (POC)"** is burned directly
into the composited output video using FFmpeg's `drawtext` filter.  It is
visible at all times during playback — it is part of the video itself, not
removable UI chrome.  This meets the CVAA/ADA-informed requirement that viewers
always understand they are seeing a machine-generated overlay.

### Original captions preserved

The PiP compositor overlays ASL clips in a bottom-right window (~25% of screen
width) and never modifies or suppresses the original video captions.  For
segments with `action: "CAPTIONS"`, no overlay is shown and the original
caption track plays unaltered.

### Pilot design

- Participants are briefed before each session that this is a student POC with
  word-level clips only and known limitations.  Informed consent is obtained.
- Feedback is collected anonymously using a standard form (1–5 star rating,
  issue checkboxes, free-text, disclosure label noticed yes/no).
- No personally identifiable information is retained in pilot data.
- If no DHH participants are available, this is documented as an explicit
  limitation of the pilot findings.

### Updated risk assessment — Sprint 3

| Risk | Status | Evidence |
|------|--------|----------|
| Incorrect ASL match shown | Mitigated | Threshold restored to 0.80; bracket stripping recovers valid matches |
| Two ASL clips playing simultaneously | Mitigated | Overlap resolution keeps only higher-scoring entry |
| Disclosures not noticed by viewers | Mitigated | Label burned into video; pilot to measure noticed percentage |
| Word-level clips misrepresent ASL | Accepted limitation | Documented in pilot briefing and all output labels |
| No Deaf community review | Accepted limitation | Documented; recommended for future sprints |
| Privacy concern in pilot data | Mitigated | Anonymous collection; no PII retained |

### Sustainability note

The pipeline processes one video at a time using a lightweight sentence-
transformer model (all-MiniLM-L6-v2, ~22M parameters) on CPU.  FFmpeg
compositing is a single-pass operation.  Compute usage is minimal for a POC.

