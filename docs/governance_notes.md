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
