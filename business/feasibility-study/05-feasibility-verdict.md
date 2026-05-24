# F5 — Feasibility Verdict

> A synthesis of [F1](01-technology-feasibility.md), [F2](02-competitive-tech-comparison.md), [F3](03-market-expansion.md), and [F4](04-pricing-strategy-comparison.md) into a single go/no-go judgment with conditions.

---

## 5.1 — Is the project feasible?

**Yes — technically, commercially, and ethically — under specific conditions.** The remainder of this document states those conditions.

### Feasibility across the four required lenses

| Lens | Verdict | Why |
|------|---------|-----|
| **Technical** | ✅ Buildable | Retrieval-augmented hybrid is within reach of a focused 8-person team in 24 months at ~$5.5M; uses well-understood components (Whisper, T2S-GPT-class, retrieval, WebGPU rigging) ([F1](01-technology-feasibility.md)) |
| **Competitive** | ✅ White-space exists | No productized system today combines retrieval anchoring + parallel-NMM generation + platform-agnostic SDK; window is open ~24 months ([F2](02-competitive-tech-comparison.md)) |
| **Market** | ✅ Tool *grows* the market | Conservative induced-demand modeling shows the addressable ASL-content market expands ~3× by 2035 in the with-tool scenario ([F3](03-market-expansion.md)) |
| **Commercial** | ✅ Platform-pays works | $22M Y5 ARR realistic with ~90 platform contracts; 78–82% gross margins; defensible integration moat ([F4](04-pricing-strategy-comparison.md)) |
| **Ethical** | ⚠️ Conditional | Only if Deaf-community-led co-design is the first hire and the loudest brand position. This is not optional. |

---

## 5.2 — The conditions that must hold

These are sequential. A failure at any prior condition invalidates the next.

### Condition 1 — Deaf-community partnership is real, not performative

| Requirement | Concrete test |
|---|---|
| 5-person paid Deaf advisory board, signed agreements, equity participation | In place by month 3 |
| First non-founder hire is Deaf | Hired by month 4 |
| Public "augmentation, not replacement" position statement | Published, with NAD or equivalent endorsement |
| Corpus contributors compensated per-sign + royalty | Documented in contributor agreement |
| Quarterly community quality review with named Deaf rater panel | First panel run by month 8 |

If any of these fails: the project is not the right shape. Restructure as research/open-source contribution, not as a venture.

### Condition 2 — Seed capital, not bridge capital

| Requirement | Concrete test |
|---|---|
| ~$4–5M raised at a respectable post (Phase 1+2 fully funded) | Closed by month 6 |
| At least one strategic partner LOI from a platform buyer | Signed before close |
| At least one academic / Deaf-institution partner (Gallaudet, Boston U, RIT/NTID) on data | MoU in place |

A $1M pre-seed with consumer-revenue-bridge ambitions is the wrong shape for this product. Either raise the larger round on the larger thesis, or pivot to the v1 consumer-learner thesis where smaller capital makes sense.

### Condition 3 — Technical milestones gated by user trust, not by engineering

| Milestone | Gate to release |
|---|---|
| Closed beta launch | Deaf advisory board rates intelligibility ≥ 3.5/5 on standardized test set |
| Public beta launch | ≥3 paid platform pilots active; second Deaf-rater panel ≥ 3.8/5 |
| GA launch | SOC 2 Type I; ≥10 platform contracts active; Deaf-rater panel ≥ 4.0/5 |

Engineering velocity is not the constraint. Trust calibration is.

### Condition 4 — Platform-pays as the primary motion

| Requirement | Concrete test |
|---|---|
| First paid platform contract by month 12 | Single logo with ≥$25k ACV |
| 4+ Tier 2 platform contracts by month 18 | $300k+ ARR |
| Tier 3 strategic pipeline by month 24 | At least 2 enterprises in late-stage RFP |
| Consumer surfaces remain ≤10% of engineering effort | Tracked in monthly engineering review |

If platform sales does not land by month 18, *that* is the signal to pivot — either to a Signapse-style focused-vertical service business or to the v1 consumer-learner thesis.

---

## 5.3 — What this is *not*

A clear-eyed founder should know what GenASL is *not*:

- It is **not a unicorn**. Realistic best case is a $200–500M outcome at year 5–7, via acquisition by a captioning incumbent (3Play, Verbit) or accessibility platform (Sorenson, AudioEye, Deque). That is a great outcome. Anyone modeling a billion-dollar exit is mis-pricing the market.

- It is **not a quick build.** This is a 24-month research-and-data effort before there is a defensible product. Teams unwilling to commit to that timeline should pick a different problem.

- It is **not a replacement for human interpreters.** Saying so publicly is non-negotiable. Even if individual use cases bear that out, the brand position must always be augmentation. Markets where the only legally acceptable answer is a human interpreter (court, medical informed consent, formal education accommodations) are out of scope forever.

- It is **not a model breakthrough.** The technology is application of recent SOTA + careful systems engineering + proprietary corpus. The team should not pretend otherwise to investors. The moat is *corpus + community + integration*, not algorithms.

---

## 5.4 — What it *is*

- It is **the right shape for an accessibility-tech infrastructure company.** Aligned with where regulation is going (ADA Title II, EAA), aligned with where the captioning industry is heading (specialty add-on services), aligned with where the Deaf community accepts technology (augmentation tools, not replacement tools).

- It is **innovative in architecture, not in components.** The novelty is the *combination*: retrieval-augmented sign synthesis + parallel-NMM generation + platform-agnostic SDK + B2B-only commercial model + Deaf-led data sourcing. None of these is new alone. Together, they are unmatched.

- It is **a real business at a realistic scale.** $22M ARR with 78–82% margins by year 5 is a credible target. An acquirer pays 5–8× that. A late-stage growth investor pays it forward at the same multiple. Either way, this is a working company.

---

## 5.5 — Final recommendation

**Proceed. Build the production GenASL. Raise the right round, hire Deaf-first, build the corpus, prioritize the retrieval-augmented hybrid architecture, sell only to platforms.**

**If any of the four conditions in [§5.2](#52--the-conditions-that-must-hold) cannot be met within their stated time-frames, stop and reorganize as a research / open-source contribution.** That is also a legitimate and valuable outcome — and it is *much better* than a venture-backed effort that fails for the right reasons in year 3.

The market is real. The technology is feasible. The architecture has a defensible position. The community will participate if treated as partners. The capital is available for credible teams on accessibility theses. The window is ~24 months before incumbents close it.

**This is buildable, ethical, and commercially viable — under the conditions above, and only under those conditions.**

---

## 5.6 — Decision summary card

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│            GenASL Production — Decision Summary                 │
│                                                                 │
│  Technical feasibility ............. YES                        │
│  Competitive white space ........... YES                        │
│  Market grows with tool ............ YES (~3× by 2035)          │
│  Platform-pays viable .............. YES (~$22M Y5 ARR)         │
│  Ethical execution achievable ...... YES, conditional           │
│                                                                 │
│  Capital required (24 months) ...... ~$5.5M                     │
│  Team size (steady state) .......... ~8.5 FTE                   │
│  Time to defensible product ........ ~18 months                 │
│  Time to first paid platform ....... ~12 months                 │
│                                                                 │
│  Primary monetization .............. B2B platform-pays          │
│  Secondary monetization ............ minimal showcase only      │
│                                                                 │
│  Primary architecture .............. Retrieval-augmented        │
│                                       + parallel-NMM channel    │
│  Primary distribution .............. JS SDK, platform-agnostic  │
│  Primary moat ...................... Deaf-signed corpus +       │
│                                       integrations + community  │
│                                                                 │
│  Recommendation .................... PROCEED with conditions    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
