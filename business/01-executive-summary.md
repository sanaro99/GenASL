# 1 — Executive Summary

> **The verdict in one line:** GenASL is a feasible, innovative, and business-viable
> accessibility-infrastructure play — **if** it ships the *retrieval-augmented,
> grammar-aware* ASL avatar it has committed to, sells to **platforms** (not Deaf
> viewers), and makes Deaf-community co-design the first hire rather than the last check.

---

## The committed approach in one paragraph

A production GenASL ingests speech, chunks it on prosody and clause boundaries, translates
to an ASL *plan* with an LLM (gloss + topic-comment structure, classifiers, role shifts,
question/negation flags — **internal only, never shown to a user**), and drives a rigged
VRM avatar with motion that is **anchored to real Deaf-signer recordings**. The default
tier retrieves a *continuous clip at the phrase level* from a real corpus; a lexical
secondary covers gaps; per-gloss stitching is a tagged last resort. Generative steps fill
*only* transitions and the non-manual-marker (NMM) channel synthesised from prosody. The
result is a **platform-agnostic ASL track** — a JS SDK any video player embeds, billed B2B
per minute. This is the "middle" of ASL: more than word clips, short of pure neural
synthesis. It needs clean data, compute, and Deaf partnership — and that cost *is* the moat.

---

## The opportunity in three facts (refreshed May 2026)

| | Fact | Source |
|---|------|--------|
| 1 | **~70M Deaf signers worldwide** (WFD), across 300+ sign languages. In the US: ~500k–1M primary ASL users, ~6.4–7.0M total signers (~2.8% of adults), ~2M functionally Deaf, ~48M with some hearing loss. | [WFD](https://wfdeaf.org/); [ASL Bloom](https://www.aslbloom.com/blog/how-many-people-use-asl); [NIDCD](https://www.nidcd.nih.gov/health/statistics/quick-statistics-hearing) |
| 2 | **The compliance runway moved toward us.** The ADA Title II web deadline was **extended to April 26, 2027** (≥50k pop.) / **2028** (smaller) by a DOJ interim final rule effective April 20, 2026 — which explicitly cites *the limits of current AI to remediate accessibility at scale*. The EU Accessibility Act has been live across 27 states since **June 28, 2025** and names sign-language interpretation for audiovisual media. | [Federal Register](https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web); [3Play — EAA](https://www.3playmedia.com/blog/european-accessibility-act-eaa/) |
| 3 | **Digital-accessibility litigation rebounded** to ~3,900 filings in 2025 (+24% YoY), and **sign-language-specific markets are growing 8–20% CAGR** — interpretation services ~$0.89B (2026) → $1.72B (2034); translation software ~$0.5–1.2B (2026) → $2.5–4.5B (2033). | [EcomBack](https://www.ecomback.com/annual-2025-ada-website-accessibility-lawsuit-report); [Business Research Insights](https://www.businessresearchinsights.com/market-reports/sign-language-interpretation-services-market-112737) |

---

## What GenASL does well (and doesn't)

| Strength | Weakness / open risk |
|----------|----------------------|
| **Retrieval anchoring to Deaf-signer recordings** bounds the failure modes that sink pure-neural avatars (no six-fingered hands), and produces an *auditable* artifact a compliance officer can defend. | **Clean data is the hard part.** Phrase-level retrieval needs a curated, consented, NMM-annotated corpus. Public datasets (OpenASL, ASL Citizen) are the floor; the proprietary corpus is a multi-quarter, paid-Deaf-signer effort. |
| **Grammar-aware plan stage** encodes topic-comment, classifiers, and NMMs as explicit labels — the structure word-level systems can't represent. | **Idiomatic / classifier-heavy / narrative ASL is fundamentally generative**, not lexical. Poetry and storytelling stay out of scope for years; this must be disclosed, not hidden. |
| **Platform-agnostic SDK** meets viewers on the platforms they already use and removes single-platform (YouTube) dependency. | **Incumbent risk is now live.** [Sorenson acquired Hand Talk + OmniBridge](https://sorenson.com/newsroom/sorenson-acquires-omnibridge-and-hand-talk-to-develop-automated-sign-language-translation-capabilities/) and is demoing ASL avatars. The window is ~24 months. |
| **Per-stage cached, Pydantic-typed pipeline** (Phases 1–3 shipped: audio backbone + interpreter brain) is real, testable, and reproducible — not a slide. | **No Deaf-community validation yet.** This is the single most important blocker for monetisation and the first gate in the plan. |

---

## Headline market sizing (full derivation in [02-market-analysis.md](02-market-analysis.md))

| Layer | Definition | Size |
|-------|------------|------|
| **TAM** | Global video-accessibility tooling (captioning, audio description, sign language, transcription) | **~$3.5–4B in 2026**, ~$8–10B by early 2030s |
| **SAM** | English-speaking regulated digital video (US, UK, CA, AU, IE), ASL/BSL slice | **~$750M in 2026**, ~$1.8B by 2030 |
| **SOM** | Realistic 5-year capture via platform-pays B2B | **~$22M ARR by Year 5** (~3–5% of SAM) |
| **Induced** | Net-new ASL-content market the tool *creates* (see [F3](feasibility-study/03-market-expansion.md)) | **~+$4.5B/yr by 2035** (~3× baseline) |

---

## The product evolution path

GenASL today is a **working pipeline through Phase 3**. The path to a defensible business
runs through data and trust, not features:

```
   ┌─────────────────────────────────────────────────────────────┐
   │  M0–M6  →  FOUNDATION & DATA                                 │
   │  Deaf advisory board + first Deaf hire; corpus from public   │
   │  sets (OpenASL/ASL Citizen) + first proprietary capture;     │
   │  Phases 4–5 (retrieval + motion synth) land                  │
   │  Goal: intelligibility ≥ 3.5/5 on a Deaf-rater panel         │
   └─────────────────────────────────────────────────────────────┘
                              ↓
   ┌─────────────────────────────────────────────────────────────┐
   │  M6–M18  →  PLATFORM SDK + FIRST PAID CONTRACTS             │
   │  Phases 6–7 (VRM extension + API); platform-agnostic SDK;    │
   │  compliance reporting (WCAG/EAA/508); 3–5 paid pilots        │
   │  Goal: $300k+ ARR; SOC 2 Type I; panel ≥ 3.8/5               │
   └─────────────────────────────────────────────────────────────┘
                              ↓
   ┌─────────────────────────────────────────────────────────────┐
   │  M18–M24+  →  SCALE                                          │
   │  10+ platform contracts; Tier-3 strategic pipeline;          │
   │  BSL/AUSLAN reuse of the same architecture                   │
   │  Goal: ~$2M ARR run-rate; Series A; panel ≥ 4.0/5            │
   └─────────────────────────────────────────────────────────────┘
```

---

## Why this is innovative

Existing AI sign-language tools fall into camps that each hit a wall:

| Camp | Examples | Limitation |
|------|----------|------------|
| **Word/clip retrieval** | Old GenASL PoC; Hand Talk clip mode | No grammar, no NMMs; not real ASL |
| **Notation-driven avatar** | JASigning (HamNoSys), Paula | Every sign hand-authored by linguists; doesn't scale |
| **MoCap playback** | Signapse (Kara avatar) | Vocabulary bounded by what was captured; coverage scales linearly with studio time |
| **End-to-end neural** | SignDiff, T2S-GPT; Sorenson's text-to-sign POC | BLEU-4 still in the teens; hallucinated handshapes; uncanny faces |

**GenASL's lane is the uncontested fifth: retrieval-augmented + parallel-NMM + SDK
distribution + platform-pays.** It is cheaper to QA, defensible by corpus ownership, and
the only approach that simultaneously clears fidelity, Deaf-acceptance, and auditability
bars (full scoring in [03-competitive-landscape.md](03-competitive-landscape.md)).

---

## Why this is risky

Three risks dominate; all are surmountable but must be confronted directly.

1. **Cultural-acceptability risk.** Deaf users reject avatars that lack NMMs and authentic
   grammar ([PMC 8866438](https://pmc.ncbi.nlm.nih.gov/articles/PMC8866438/)). Mitigation:
   Deaf-led co-design from day 0; explicit "augmentation, not replacement" position;
   compensated corpus contributors. This is a gate, not a workstream.
2. **Incumbent / platform-build risk.** Sorenson is moving; a platform could ship native
   ASL. Mitigation: move first, win 3+ platform reference logos by month 18, differentiate
   on Deaf-trust + auditable corpus + media-overlay (not point-of-service) use case;
   acquisition by an incumbent is a legitimate outcome, not only a threat.
3. **Data / coverage risk.** Long-tail vocabulary (medical, legal, technical) and
   classifier-heavy ASL are hard. Mitigation: domain-specific capture in later phases;
   honest scope disclosure; phrase-level retrieval degrades gracefully (tagged fidelity).

Full register in [06-go-to-market-and-risk.md](06-go-to-market-and-risk.md).

---

## Recommendation

**Proceed — on the committed thesis, not the old one.** Build the retrieval-augmented,
grammar-aware avatar; raise a real seed (~$4–5M, not a pre-seed bridge); hire Deaf-first;
sell only to platforms. The architecture is sound, Phases 1–3 are shipped, the corpus is
the moat, and the regulatory runway (extended ADA Title II, live EAA) lands inside the
24-month build window.

**If the four conditions in [§5.2 of the verdict](feasibility-study/05-feasibility-verdict.md)
cannot be met in their time-frames, stop and reorganise as a research / open-source
contribution.** That is a legitimate outcome — and far better than a venture that fails for
the wrong reasons in year 3.
