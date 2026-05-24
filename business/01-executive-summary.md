# 1 — Executive Summary

> **The verdict in one line:** GenASL is a feasible and innovative project with a real business path — **if** it pivots from "ASL replacement for captions" to **"ASL augmentation layer for regulated video content and ASL learners,"** and prioritizes Deaf-community co-design before any paid GTM.

---

## The opportunity in three facts

| | Fact | Source |
|---|------|--------|
| 1 | **~48 million** US adults report hearing loss; ~2M are functionally Deaf; ~500k–1M use ASL as a primary language. Worldwide, the WFD estimates **~72M Deaf signers**. | [NIDCD](https://www.nidcd.nih.gov/health/statistics/quick-statistics-hearing); [WFD](https://wfdeaf.org/) |
| 2 | **Digital accessibility lawsuits hit 4,187 in 2024**, pacing **+37% in 2025**, with settlements **$10k–$75k per violation**. ADA Title II compliance deadline for state/local gov is **April 24, 2026**. The EU Accessibility Act began enforcement **June 28, 2025**. | [Deque](https://www.deque.com/blog/companys-videos-sued-ada-noncompliance/); [3Play Media](https://www.3playmedia.com/blog/european-accessibility-act-eaa/) |
| 3 | The **closed-captioning market is ~$2.5B in 2025**, projected to ~$8B by 2033 at **~15% CAGR**. North America is ~40% of the global market. ASL is the next compliance frontier as captions become commoditized. | [GlobalGrowthInsights](https://www.globalgrowthinsights.com/market-reports/captioning-and-subtitling-market-111936) |

---

## What GenASL does well (and doesn't)

| Strength | Weakness |
|----------|----------|
| **Hybrid retrieval architecture** (LLM gloss + WLASL clips) is cheaper, more deterministic, and easier to QA than pure neural avatar synthesis. | **Word-level gloss is not real ASL.** It lacks ASL grammar (topic-comment structure, classifiers, non-manual markers). Native Deaf signers will reject it for primary consumption. |
| **Browser overlay** is the right distribution surface — it meets users on the platforms they already use (YouTube), instead of forcing them to a destination site. | **WLASL has known label-quality issues**, and 2,000 glosses ≈ a fraction of conversational ASL vocabulary. Coverage will be a persistent ceiling. |
| **Provider-agnostic LLM layer** (Ollama, Gemini, OpenAI) means enterprises can self-host — a real wedge against incumbents like 3Play that require cloud. | **Single-platform (YouTube) + dependency on `youtube-transcript-api`** is fragile. Any TOS change breaks distribution. |
| **Pipeline architecture is clean** (recent refactor to a staged `Pipeline` class) — readable, testable, well-documented. | **No Deaf-community validation yet.** Sprint docs explicitly mark this as a student PoC. This is the most important blocker for monetization. |

---

## Headline market sizing (full derivation in [02-market-analysis.md](02-market-analysis.md))

| Layer | Definition | Size |
|-------|------------|------|
| **TAM** | Global video accessibility tools (captioning, audio description, sign language, transcription) | **~$3.0B in 2026**, growing to ~$8B by 2033 |
| **SAM** | English-speaking markets requiring ASL/BSL for regulated digital video (US, UK, CA, AU, IE) | **~$650M** addressable in 2026 |
| **SOM** | Realistic 5-year capture: 0.5% of SAM through education + mid-market enterprise + creator tools | **~$15–25M ARR by year 5** |

---

## The product evolution path

GenASL today is a **demo**. The path to a defensible business has three rungs:

```
   ┌─────────────────────────────────────────────────────────────┐
   │  YEAR 1  →  EDUCATION WEDGE                                  │
   │  K-12 + community college ASL learners; Chrome extension     │
   │  freemium + $9/mo individual; B2B school district pilot     │
   │  Gross profit goal: break-even on infra; learn product       │
   └─────────────────────────────────────────────────────────────┘
                              ↓
   ┌─────────────────────────────────────────────────────────────┐
   │  YEAR 2  →  ENTERPRISE AUGMENTATION LAYER                    │
   │  LMS, MOOC, gov portal video — ASL-on-top-of-captions        │
   │  $0.40–$1.20/min pricing, audited compliance reports         │
   │  Self-hosted option for regulated buyers                     │
   └─────────────────────────────────────────────────────────────┘
                              ↓
   ┌─────────────────────────────────────────────────────────────┐
   │  YEAR 3+  →  GENERATIVE ASL PLATFORM                         │
   │  Deaf-led co-design; sentence-level synthesis;               │
   │  white-label SDK for creators, EdTech, telehealth            │
   │  Defensible moat: certified ASL corpus + community trust     │
   └─────────────────────────────────────────────────────────────┘
```

---

## Why this is innovative

Existing AI sign-language tools fall into two camps and both have problems:

| Camp | Examples | Limitation |
|------|----------|------------|
| **Pure avatar synthesis** | Signapse, SignAvatar, Hand Talk's Hugo | High-effort 3D avatar; Deaf community pushback on lack of facial grammar; expensive to render |
| **Translation-as-a-service** | SignAll, Sorenson AI | Heavy ML stack; cloud-only; designed for interpreting, not media |

**GenASL is the first credible attempt to be a *browser-native overlay* using a *retrieval-augmented* approach.** That makes it cheaper to ship, easier to audit, and uniquely positioned for the regulated-video market where deterministic outputs are a feature, not a bug.

---

## Why this is risky

Three risks dominate. All are surmountable but must be confronted directly.

1. **Cultural-acceptability risk.** Research consistently shows Deaf users reject avatars / synthetic ASL that lack non-manual markers and authentic grammar (see [PMC 8866438](https://pmc.ncbi.nlm.nih.gov/articles/PMC8866438/)). The mitigation is co-design and explicit positioning ("ASL augmentation, not interpretation").
2. **Platform risk.** YouTube can break the transcript API, throttle extensions, or ship native ASL features. The mitigation is multi-platform support (Vimeo, Coursera, Brightcove, Kaltura) and a B2B SDK that runs without YouTube at all.
3. **Coverage risk.** 2,000 glosses ≈ ~70% lexical coverage of common educational content but ~40% of conversational content. The mitigation is corpus expansion via a paid Deaf signer panel — which doubles as a community-trust signal.

Full risk register in [06-go-to-market-and-risk.md](06-go-to-market-and-risk.md).

---

## Recommendation

**Continue. Pivot from "consumer ASL captions" to "education + enterprise compliance augmentation."** The architecture and team are good. The product needs a sharper wedge and a Deaf-community-first validation loop. The market is unambiguously real, mandated by law in two of the world's largest economies, and underserved by current solutions.

See [04-value-proposition.md](04-value-proposition.md) for the product strategy and [06-go-to-market-and-risk.md](06-go-to-market-and-risk.md) for the 24-month operating plan.
