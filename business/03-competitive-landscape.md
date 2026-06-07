# 3 — Competitive Landscape

GenASL competes on two planes at once: **which technical approach** to sign production
wins, and **which company** owns distribution. This section maps both, then locates the
white space — which is narrower than it was a year ago.

---

## 3.1 — The five technical families

Sign-language production splits into five technical families. Most products mix two or
three; few are pure. GenASL is the only one committed to the fifth.

| # | Family | Representative systems | One-line description |
|---|--------|------------------------|----------------------|
| 1 | **Word/clip retrieval** | Old GenASL PoC; Hand Talk clip mode | English → gloss → look up one clip per word → concatenate. No grammar, no NMMs. |
| 2 | **Notation-driven avatar** | JASigning (SiGML/HamNoSys), Paula (EASIER) | Linguists author each sign in symbolic notation; avatar renders it. Doesn't scale. |
| 3 | **MoCap playback** | Signapse (Kara avatar) | Capture Deaf signers; play back per sentence with limited stitching. Coverage bounded by capture. |
| 4 | **End-to-end neural** | SignDiff, T2S-GPT, Sign-MExD; **Sorenson text-to-sign POC** | Text → motion in one shot, no retrieval anchor. BLEU-4 in the teens; hallucination risk. |
| 5 | **Hybrid retrieval + generative** ← **GenASL** | (no widely productised ASL system) | Phrase-level retrieval of Deaf-signer clips + generative transitions + parallel NMM channel. |

### Comparison matrix (1–5, higher is better)

| Dimension | (1) Clip | (2) Notation | (3) MoCap | (4) Neural | (5) Hybrid (GenASL) |
|---|:--:|:--:|:--:|:--:|:--:|
| Manual-sign fidelity | 4 | 3 | **5** | 3 | **5** |
| Non-manual markers (NMMs) | 1 | 2 | 4 | 3 | 4 |
| ASL grammar (topic-comment, classifiers) | 1 | 3 | 3 | 3 | 4 |
| Vocabulary coverage | 2 | 5 | 2 | 4 | 4 (scales with corpus) |
| Determinism / auditability | **5** | **5** | **5** | 1 | 4 |
| Failure modes acceptable to Deaf community | 2 | 3 | 4 | 1 (uncanny) | 4 |
| Real-time latency feasible | **5** | 4 | 2 | 3 | 4 |
| Inference cost | **5** | **5** | 4 | 2 | 4 |
| Scales to new content domains | 2 | 3 | 2 | 4 | 4 |
| Defensibility / moat | 1 | 2 | 4 | 2 | **5** (corpus + system) |
| Time-to-MVP | **5** | 3 | 3 | 2 | 2 |
| **TOTAL** | 43 | 46 | 44 | 31 | **51** |

The hybrid approach is neither cheapest nor fastest, but it is the **only** family that
*simultaneously* clears fidelity, Deaf-acceptance, and auditability. Full scoring rationale
in [F2](feasibility-study/02-competitive-tech-comparison.md).

---

## 3.2 — Direct competitors: AI sign-language generation

| Company | HQ | Approach | Funding / scale | Strength | Weakness vs. GenASL |
|---------|----|----------|-----------------|----------|---------------------|
| **Sorenson** | US | Family 3+4. Acquired **Hand Talk + OmniBridge** (Jan 2025); April 2026 POCs: text-to-sign **human-looking avatar** + real-time sign-to-text | Largest US VRS base; established enterprise revenue | **The incumbent threat** — Deaf customer base + brand + capital | Pure-neural avatar (experts raised concerns); POC aimed at *point-of-service* interactions (retail, airports), not media overlay; slow institutional velocity |
| **Signapse AI** | UK | Family 3 + light 4 — MoCap of Deaf signers + neural style transfer; BSL + ASL | **~$3.5M total**; ~$6.6M seed valuation (2024); accelerator round Aug 2025 | Deaf-led credibility; transport partnerships (Network Rail, Translink) | Vocabulary bounded by sessions captured; expanding coverage scales linearly with studio time; SaaS-portal, not browser overlay |
| **Hand Talk** | Brazil | Family 2 (Hugo avatar) + neural smoothing; **now part of Sorenson** | 4M+ downloads; 700M+ words; UN "World's Best Social App" | Distribution scale in emerging markets | Libras-first; avatar criticised for stiff motion / missing NMMs; ASL secondary |
| **SignDiff / T2S-GPT / Sign-MExD** | Academic | Family 4, pure neural | Research grants | Generalises to arbitrary input | BLEU-4 ~12–17 on How2Sign; not productised; documented hallucinated handshapes |
| **JASigning** | Academic (UEA) | Family 2, notation | Research | Linguistically rigorous; many languages | Every sign hand-authored; doesn't scale as a runtime |

Sources: [Sorenson newsroom](https://sorenson.com/newsroom/sorenson-acquires-omnibridge-and-hand-talk-to-develop-automated-sign-language-translation-capabilities/),
[Slator on Signapse](https://slator.com/ai-sign-language-firm-signapse-raises-usd-2-4m-in-seed-funding/),
[Crunchbase — Signapse](https://www.crunchbase.com/organization/signapse-ec44),
[Hand Talk on App Store](https://apps.apple.com/us/app/hand-talk-learn-sign-language/id659816995).

**GenASL's defensible difference:** phrase-level **retrieval of Deaf-signer recordings**
+ **platform-agnostic media overlay**. Sorenson is attacking the *transactional service
desk*; Signapse the *bounded-vocabulary announcement*; GenASL the *long tail of
instructional/expository online video* that neither addresses and that no human
interpreter is economically viable for.

---

## 3.3 — The data layer: why the corpus is the moat

GenASL's approach is only as good as the corpus it retrieves from. The public datasets set
the floor; the proprietary, consented, NMM-annotated corpus is the asset competitors can't
copy.

| Dataset | Scale | Role in GenASL |
|---------|-------|----------------|
| [**OpenASL**](https://arxiv.org/pdf/2205.12870) | 288 h, 200+ signers, multi-domain — largest public ASL translation set | **Default phrase-level retrieval tier** |
| [**ASL Citizen**](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-description/) | 83,399 videos, 2,731 signs, 52 signers, consented | **Lexical secondary** (gap coverage) |
| [**YouTube-ASL**](https://arxiv.org/pdf/2306.15162) | 984 h, 11,093 videos (~3× OpenASL), open-domain | Training/retrieval expansion |
| **WLASL** | ~2,000 glosses | **Last-resort per-gloss fallback** (tagged `fidelity="stitched"`/`"degraded"`) |
| **Proprietary capture** | 200 h+ Deaf-signer, NMM-annotated (built over Phases 4+) | **The moat** — consented, royalty-bearing, auditable |

A neural-only system can be reverse-engineered from public data. A 200 h+ Deaf-signer
corpus you *own*, with explicit consent and royalty agreements, cannot be — and it doubles
as the community-trust signal that wins enterprise deals.

---

## 3.4 — Adjacent competitors: captioning incumbents

These are the businesses GenASL **prices against** and may **partner with or be acquired by.**

| Company | Model | Pricing | Implication for GenASL |
|---------|-------|---------|------------------------|
| **3Play Media** | Hybrid AI + human captioning, AD, transcripts | ~$0.90/min; avg enterprise ~$117k/yr | Benchmark for enterprise pricing; partner or acquirer |
| **Verbit** | AI live + post-production captioning | ~$0.95/min | Aggressive EdTech sales; likely acquirer |
| **Rev / Rev AI** | API-first transcription & captions | **$0.25/min** AI-only | Sets the floor price for AI-only output |
| **AI Media / AIMG** | Live captioning, broadcast | Custom | Established in broadcast |

**Strategic implication:** price ASL as a **premium add-on to captioning, not a replacement.**

```
  Captions:      $0.25 – $1.00 / min   (commodity)
  ASL overlay:   $0.30 – $1.20 / min   ← GenASL band (1–3× captioning, volume-discounted)
  Audio descr.:  $4 – $15 / min        (specialised human)
  Human ASL:     $300 – $800 / min     (gold standard; what GenASL does NOT replace)
```

---

## 3.5 — Positioning map

```
                                           HIGH FIDELITY
                                                  │
                                   Human interpreter
                                                  │
                              Signapse (MoCap) ●  │  ● Sorenson AST
                                                  │    (avatar POC)
   COMMODITY ─────────────────────────────────────┼────────────────────── BESPOKE
   COST                                           │                       COST
                                                  │   ★ GenASL
                                                  │     retrieval-augmented
                                          ●       │     (target zone)
                                  Hand Talk Hugo  │
                              ● JASigning          │
                         ● SignDiff / T2S-GPT      │
                           (research)              │
                       ● old GenASL PoC            │
                                            LOW FIDELITY
```

The empty quadrant — **high fidelity at commodity cost** — is what the hybrid pipeline
opens. A year ago it was uncontested; today **Sorenson's AST program is aiming at the same
quadrant from above.** The difference: Sorenson is pure-neural and point-of-service;
GenASL is retrieval-anchored and media-overlay. The race is real and the moat is
*corpus + community + integration*, not algorithms.

---

## 3.6 — Five forces summary

| Force | Strength | Notes |
|-------|----------|-------|
| **Threat of new entrants** | High | LLM + public datasets are reproducible; the barrier is a *consented, NMM-annotated* corpus and community trust |
| **Bargaining power of customers** | Medium-High | Platforms have RFP leverage; one integration is worth millions of viewers |
| **Bargaining power of suppliers** | Low | LLM is multi-provider; OpenASL/ASL Citizen are public; rendering is open |
| **Substitutes** | High | Captions, transcripts, human interpreters all substitute partially |
| **Industry rivalry** | **Rising fast** | Sorenson's acquisitions + POCs moved this from "niche" to "contested" inside a year |

**Moats GenASL can build (none are fully present yet):**

1. **A licensed, expanded Deaf-signer corpus** with NMMs and royalty agreements — the
   single most valuable asset.
2. **Integration lock-in.** Once a platform embeds the SDK in its player + compliance
   pipeline, switching is a multi-month engineering project.
3. **Audit-grade compliance reporting** mapped to WCAG/EAA/508 — procurement buys paperwork.
4. **Deaf-community endorsement** (NAD / Gallaudet / NTID advisory) — non-replicable for
   late entrants and the thing Sorenson's pure-neural avatar most conspicuously lacks.
