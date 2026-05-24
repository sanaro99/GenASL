# F2 — Competitive Technology Landscape

> **Question:** What technical approaches exist in sign language production today, and how do they compare on the dimensions that matter — fidelity, determinism, cost, scalability, community acceptance?
> **Short answer:** There are 5 distinct technical camps. Each has a sharp limitation. **The retrieval-augmented + parallel-NMM architecture proposed in [F1](01-technology-feasibility.md) sits in an uncontested white space.**

---

## 2.1 — Taxonomy of approaches

Sign language production splits into five technical families. Most products mix two or three; few are pure.

| # | Family | Representative system(s) | One-line description |
|---|---|---|---|
| 1 | **Word/clip retrieval** | Current GenASL PoC; Hand Talk Hugo (clip mode); older interpreter-video systems | English → gloss → look up pre-recorded clip per word; concatenate |
| 2 | **Notation-driven 3D avatar** | JASigning (SiGML/HamNoSys), Paula (EASIER) | Linguists author signs in a symbolic notation; avatar renders the notation |
| 3 | **Motion-capture playback** | Signapse (Kara avatar — neural face on MoCap'd body), TV broadcast interpreter studios | Capture real Deaf signers in studio; play back per sentence with limited stitching |
| 4 | **End-to-end neural production** | Progressive Transformer, SignDiff (diffusion), T2S-GPT (motion VQ-VAE) | Text → motion sequence in one shot; no retrieval anchor |
| 5 | **Hybrid retrieval + generative** ← **proposed** | (none widely productized for ASL) | Retrieval for individual signs + generative for transitions + parallel channel for NMMs |

---

## 2.2 — Comparison matrix

Scored 1–5 (5 = best). Sources cited in row notes; subjective ratings are calibrated against research literature and Deaf-user acceptance studies.

| Dimension | (1) Clip retrieval | (2) JASigning / notation | (3) MoCap playback | (4) End-to-end neural | (5) Hybrid (proposed) |
|---|:--:|:--:|:--:|:--:|:--:|
| Manual sign fidelity | 4 | 3 | **5** | 3 | **5** |
| Non-manual markers (NMMs) | 1 | 2 | 4 | 3 | 4 |
| ASL grammar (topic-comment, classifiers) | 1 | 3 | 3 | 3 | 4 |
| Vocabulary coverage | 2 (~2k WLASL) | 5 (any signable in HamNoSys) | 2 (limited by session) | 4 (in-domain) | 4 (scales with corpus) |
| Determinism / auditability | **5** | **5** | **5** | 1 | 4 |
| Failure modes acceptable to Deaf community | 2 | 3 | 4 | 1 (uncanny) | 4 |
| Real-time latency feasible | **5** | 4 | 2 | 3 | 4 |
| Compute cost at inference | **5** ($) | **5** ($) | 4 ($$) | 2 ($$$) | 4 ($$) |
| Compute cost at training | **5** (none) | **5** (none) | 3 ($) | 1 ($$$) | 2 ($$$) |
| Scales to new content domains | 2 | 3 | 2 | 4 | 4 |
| Defensibility / moat | 1 | 2 | 4 (corpus) | 2 (model is reproducible) | **5** (corpus + system) |
| Engineering complexity | **5** (low) | 3 | 3 | 2 | 2 |
| Time-to-MVP | **5** (months) | 3 (months) | 3 (year) | 2 (1–2 yr) | 2 (1.5–2 yr) |
| **TOTAL** | 43 | 46 | 44 | 31 | **51** |

The hybrid approach is not the cheapest or fastest, but is the only one that **simultaneously** clears the bars on fidelity, Deaf acceptance, and defensibility.

---

## 2.3 — Profiles of the leading systems

### Signapse (UK, BSL + ASL, Series Seed)

- **Tech:** Pre-recorded MoCap of Deaf signers; neural face/style transfer for variety. Effectively a Family 3 + light Family 4 system.
- **Strength:** Deaf-led; visual quality high; partnerships with transport operators (Network Rail, Translink).
- **Limit:** Vocabulary limited to the sessions captured; reusing a signer's recorded sentence ≠ producing arbitrary new ones. Cost of expanding coverage scales linearly with studio time.
- **Funding:** ~$3.5M total ([Crunchbase](https://www.crunchbase.com/organization/signapse-ec44)).
- **Lesson:** Their wedge (transport / announcements) is one where vocabulary is bounded — a smart product choice. GenASL must pick its analogous bounded wedge first (we propose: **educational / instructional video**).

### Hand Talk (Brazil, Libras + ASL)

- **Tech:** "Hugo" 3D avatar; mostly Family 2 (rule-based notation) with neural smoothing. ASL is bolted on top of Libras pipeline.
- **Strength:** 10M+ app downloads; deep B2B with Brazilian banks/gov ([App Store](https://apps.apple.com/us/app/hand-talk-learn-sign-language/id659816995)).
- **Limit:** Avatar is widely criticized in the Brazilian Deaf community for stiff motion and missing NMMs. Family 2 systems hit this wall.
- **Lesson:** *Distribution can scale ahead of fidelity in emerging markets, but not in the US/EU.* North American Deaf advocacy is more organized and more skeptical.

### SignDiff / T2S-GPT / Sign-MExD (academic, Family 4)

- **Tech:** Pure neural. SignDiff is a diffusion model conditioned on text ([arxiv](https://arxiv.org/pdf/2308.16082)); T2S-GPT uses VQ-VAE motion tokens + autoregressive prediction ([arxiv](https://arxiv.org/html/2406.07119v1)); Sign-MExD adds expert priors to diffusion ([APSIPA 2025](http://www.apsipa.org/proceedings/2025/papers/APSIPA2025_P422.pdf)).
- **Strength:** Generalizes beyond corpus; arbitrary sentence input.
- **Limit:** BLEU-4 still ~12–17 on How2Sign — not user-ready. Hallucinated hand shapes documented in SignDiff paper. No commercial productization yet.
- **Lesson:** **Research is improving fast.** A productized version is 2–3 years out without retrieval anchoring. The window for a retrieval-augmented entrant to establish corpus + community moat is closing.

### JASigning (academic, UEA)

- **Tech:** SiGML→3D avatar rendering. Family 2.
- **Strength:** Linguistically rigorous; supports many sign languages.
- **Limit:** Requires every sign to be hand-authored in HamNoSys. Productizing means employing linguists at scale.
- **Lesson:** Notation is a powerful intermediate representation, but as a *production format* it doesn't scale. Use it as a debug surface, not a production runtime.

### Sorenson AI / VRS players (US, incumbent)

- **Tech:** Long-tail human VRS plus a new AI translation effort. Largely a service business that is becoming a tech business.
- **Strength:** Massive existing Deaf customer base; brand trust.
- **Limit:** Slow product velocity; institutional risk-aversion; legacy revenue dependence on VRS minutes.
- **Lesson:** **Likely future acquirer.** Their distribution + GenASL's tech is a credible exit thesis at Y3–Y5.

---

## 2.4 — Efficiency comparison (per minute of generated output)

How much does it actually cost to *produce* one minute of ASL for each approach? Estimates are blended from published cloud-rate benchmarks and our own modeling.

| Approach | Production cost | Quality (subjective, 1–5) | Notes |
|---|---|---|---|
| Human Deaf interpreter (live or recorded) | **$300 – $800 / min** | 5 | Gold standard; what regulated buyers replace |
| Human studio MoCap + post (Signapse-style) | $200 – $600 / min | 4–5 | High one-time cost; reusable for matching domains |
| Notation-authored (JASigning) | $50 – $150 / min | 3 | Linguist labor dominates |
| Pure neural (SignDiff / T2S-GPT, if productized) | $0.05 – $0.15 / min | 2–3 | Tiny variable cost; quality not there yet |
| **Hybrid retrieval-augmented (proposed)** | **$0.10 – $0.40 / min variable** + corpus amortization | **3–4 at MVP, 4–5 by Y3** | Sweet spot |
| Current GenASL PoC (word clips + FFmpeg) | $0.05 / min | 1–2 | Demo only |

**The hybrid approach is 1,000× cheaper than human interpretation and 10× cheaper than studio MoCap, at quality that *could* approach studio-MoCap by year 3** if the corpus and Deaf-led QA are funded properly.

---

## 2.5 — Where the white space is

Plotting the field on two axes that matter for buyers:

```
                                           HIGH FIDELITY
                                                  │
                                  Human interpreter
                                                  │
                              Signapse (MoCap) ●  │
                                                  │   ● Sorenson AI
                                                  │     (future)
                                                  │
                                                  │ 
   COMMODITY ─────────────────────────────────────┼────────────────────── BESPOKE
   COST                                           │                       COST
                                                  │
                                                  │   ★ Proposed
                                                  │     hybrid GenASL
                                                  │     (target zone)
                                          ●       │
                                  Hand Talk Hugo  │
                                  ●               │
                              JASigning           │
                                                  │
                         ● SignDiff, T2S-GPT      │
                           (research / unproven)  │
                                                  │
                       ●                          │
                  GenASL PoC today                │
                                                  │
                                            LOW FIDELITY
```

**The empty quadrant — high fidelity + commodity cost — is what the hybrid pipeline opens up.** The only other player aiming there is the Sorenson AI program, which is years out and burdened by an incumbent's organizational drag.

---

## 2.6 — Three external signals to watch (and how to react)

| Signal | What it means | Response |
|---|---|---|
| **SignDiff-class model + decent open dataset → public demo at production quality** | Pure-neural overtakes hybrid on quality; corpus moat erodes | Accelerate productization; differentiate on Deaf-community trust and platform-distribution lock-in |
| **YouTube or Netflix ships native AI ASL** | Distribution closes; consumer wedge dead | Shift entirely to the platforms-NOT-named-YouTube-or-Netflix tier (Brightcove, Kaltura, Coursera, Khan, Vimeo, Mux); pivot to SDK/white-label |
| **A research group publishes Deaf-rated quality benchmark** | The field gets a public scoreboard; hype settles | Be on the leaderboard or be ignored; commit to publishing internal metrics quarterly |

---

## 2.7 — Bottom line

The technology landscape has many players, but **no productized system today combines retrieval anchoring, parallel NMM generation, and a platform-agnostic SDK distribution model.** That gap is exactly where GenASL can land.

The risk is not that the technology can't be built. It is that two adjacent things happen first:

1. A pure-neural model gets good enough to skip the retrieval moat.
2. An incumbent (Sorenson, Signapse, or a captioning vendor) ships a hybrid with their existing distribution.

Both are plausible inside 24 months. Speed and Deaf-community trust are the only durable moats.
