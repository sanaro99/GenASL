# F1 — Technology Feasibility

> **Question:** Can the proposed audio→3D-avatar system be built with today's technology, at acceptable cost and risk?
> **Short answer:** Yes — and the design has a real advantage over pure-neural avatar synthesis if executed correctly. The bottleneck is **clean data + Deaf community partnership**, not models or compute.
> **Status (May 2026):** Phases 1–3 of the pipeline are shipped — audio ingest/ASR/prosody (Stage 1) and the LLM ASL-plan stage (Stage 2). The remaining critical path is Stage 3 (retrieval + NMM motion synthesis, Phases 4–5), the avatar/SDK (Phases 6–7), and — above all — the corpus.

---

## 1.1 — The proposed architecture (formalized)

Restating the founder's idea precisely:

> Audio in → smart audio chunking → audio + chunked text fed to an AI model → AI guides a 3D avatar more deterministically than pure neural synthesis.

This is the right shape. The question is *what each box actually is*. Here is the proposed five-stage pipeline:

```
┌────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1   AUDIO INGEST + SEMANTIC CHUNKING                                │
│   • Whisper-large-v3 ASR (or Distil-Whisper for latency-critical streams)  │
│   • Streaming VAD (Silero) → utterance-boundary detection                  │
│   • Prosodic feature extraction: F0 contour, intensity, speaking-rate,      │
│     pause duration, emphasis stress (used later for NMM generation)        │
│   • Output: time-aligned text segments + prosodic envelope                 │
└────────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2   ENGLISH → ASL LINGUISTIC PLAN                                   │
│   • Fine-tuned LLM (7B class — Qwen/Llama-3.1)                             │
│   • Outputs: ASL gloss + topic/comment structure + classifier predicates   │
│     + role shifts + question/negation flags + emphasis markers             │
│   • Trained on: How2Sign + parallel ASL-English corpora + Deaf-curated     │
│     gold set (~10–20k sentences)                                           │
│   • Gloss is INTERNAL — never shown to the user                            │
└────────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3   MOTION SYNTHESIS  (the deterministic part)                      │
│                                                                             │
│   3a. DEFAULT — phrase-level continuous-clip retrieval:                    │
│       • Each clause/phrase → retrieve ONE continuous Deaf-signer clip      │
│         from the corpus (OpenASL primary; SignCLIP-style embedding)        │
│       • Preserves intra-phrase grammar + NMMs already in the recording     │
│       • Lexical secondary (ASL Citizen) covers phrases that miss           │
│                                                                             │
│   3b. FALLBACK — per-gloss stitching (last resort only):                  │
│       • WLASL per-gloss clips chained; tagged fidelity="stitched"          │
│         (or "degraded" if >50% of glosses miss)                            │
│                                                                             │
│   3c. Generative — transitions ONLY:                                       │
│       • Constrained in-between between retrieved anchors                    │
│       • Never originates a sign; only smooths timing between real ones     │
│                                                                             │
│   3d. NMM channel (parallel, augments the retrieved face):                │
│       • Prosody envelope → face-blendshape augmentation                    │
│       • Trained on Deaf-signer face capture (FACS / ARKit blendshapes)     │
│                                                                             │
│   Output: 30 fps VRM-compatible motion stream                              │
└────────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4   AVATAR RIGGING + RENDER                                         │
│   • Server-side: GLTF/VRM rigged human (~50k-poly), Mixamo-compatible      │
│   • WebGPU renderer in the browser SDK; server-side fallback (FFmpeg+GL)   │
│   • Photoreal option: Gaussian-splat or NeRF avatar (heavy, future)        │
│   • Customer-selectable: identity, skin tone, clothing                     │
└────────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5   DELIVERY                                                        │
│   • JS SDK: WebGL/WebGPU canvas overlay on any HTML5 <video> element       │
│   • Edge-cached pre-rendered MP4 fallback for low-end devices             │
│   • Adaptive sync: pause/seek/speed events on video propagate to avatar    │
└────────────────────────────────────────────────────────────────────────────┘
```

### Why this is more deterministic than pure neural

| Risk in pure neural avatar | How this pipeline addresses it |
|---|---|
| Hallucinated hand shapes (extra fingers, impossible joint angles) | Retrieval anchors every sign to a real Deaf-signer recording; generation only fills gaps |
| Lost grammatical structure (no topic-comment, no role shift) | Explicit linguistic plan stage encodes structure as discrete labels |
| Missing non-manual markers | NMMs are a separate generation channel with its own training signal (prosody → face) |
| Each rendering is non-reproducible | Hashing the linguistic plan + motion-token sequence allows caching and audit |
| Cannot explain why an output looks wrong | Each stage's intermediate is inspectable; QA can localize errors to a stage |

The **retrieval + constrained generation** pattern is the same architectural insight that made RAG win over pure-LLM in document QA. We are doing motion-RAG.

---

## 1.2 — What's achievable today: SOTA benchmarks

| Approach | Dataset | Metric | Result | Notes |
|---|---|---|---|---|
| Progressive Transformer ([Saunders et al. 2020](https://arxiv.org/pdf/2103.06982)) | PHOENIX14T | BLEU-4 | ~21.8 | First credible end-to-end SLP |
| SignDiff ([2023](https://arxiv.org/pdf/2308.16082)) | How2Sign | BLEU-4 | ~12.85 | Diffusion model; visual quality good |
| T2S-GPT ([2024](https://arxiv.org/html/2406.07119v1)) | PHOENIX14T | BLEU-4 | improved | Dynamic VQ-VAE + autoregressive |
| Sign-MExD ([2025](http://www.apsipa.org/proceedings/2025/papers/APSIPA2025_P422.pdf)) | How2Sign | BLEU-1 | 17.75 (+7.5) | Expert-infused diffusion |
| SLRTP 2025 Challenge ([arxiv](https://arxiv.org/html/2508.06951v1)) | PHOENIX14T | varied | XLM-R fine-tunes best | Field is maturing |
| Bengali speech-to-sign ([2025](https://www.researchgate.net/publication/396107638_An_End-to-End_Bengali_Speech-to-Sign_Language_Generation_Framework_Using_Fine-Tuned_Whisper_ASR_and_Grapheme-Level_Visual_Mapping)) | Custom | WER 35.4% | n/a | Whisper-based audio frontend works |

**Honest read:** Even SOTA BLEU-4 is in the teens — *not production quality* for stand-alone Deaf consumption. But the pipeline above is not "neural model → user." It is "neural model → retrieval anchor → Deaf-curated corpus → avatar." The user-facing fidelity is closer to the corpus quality than the model BLEU.

---

## 1.3 — Build cost (24-month MVP → production)

All figures USD, conservative midpoint of vendor ranges. Sources cited where applicable.

### A. Data acquisition — the biggest line item

| Component | Quantity | Unit cost | Total |
|---|---|---|---|
| **How2Sign + YouTube-SL-25** (license + clean) | 80 + 60 hours | $0 (public) + cleaning | **$30k** |
| **New ASL MoCap with Deaf signers** | 200 hours raw → ~150 usable | Studio $500–2000/hr ([MoCap Online](https://mocaponline.com/blogs/mocap-news/motion-capture-cost-guide)) + cleanup 2–8× at $75–150/hr | **$300k – $600k** |
| **Markerless capture alternative** (RGB + 3D pose estimation rig) | 200 hours | Capital ~$50k + Deaf-signer labor at $80–120/hr | **$70k – $90k** |
| **Facial / NMM capture** (ARKit, MetaHuman, or dedicated rig) | 50 hours | $500–2k/day premium | **$30k – $80k** |
| **Annotation + QA** (Deaf linguists verify gloss/NMMs) | ~1500 hours | $80–120/hr | **$120k – $180k** |

**Recommendation:** Markerless + facial capture + Deaf-linguist QA → **~$280k – $400k total data spend**. This is the realistic figure; we are not building Hollywood-grade VFX.

### B. Compute

| Phase | Resource | Duration | Cost |
|---|---|---|---|
| Initial training (motion VQ-VAE + T2S-GPT) | 8× H100 cloud at $3/hr ([IntuitionLabs](https://intuitionlabs.ai/articles/nvidia-ai-gpu-pricing-guide)) | ~30 days × 24h | **~$17k** |
| Diffusion variant + ablations | 8× H100 | 60 days | **~$35k** |
| Continual learning + monthly retrains (Y2 onwards) | 8× H100 | 5 days/mo | **~$3k/mo** |
| Inference at scale (per-platform) | 1× A10 or L4 per ~50 concurrent users | n/a | **~$0.01–0.05 per minute** |

**Total compute budget for 24 months: ~$120k.** Compute is *not* the constraint.

### C. People (the real cost)

| Role | Headcount | Avg loaded cost | Subtotal |
|---|---|---|---|
| ML researcher (sign-language + motion) | 2 | $220k | $440k |
| ML engineer (production, inference) | 1 | $200k | $200k |
| Senior frontend / WebGPU engineer | 1 | $200k | $200k |
| Backend / SDK engineer | 1 | $190k | $190k |
| Deaf community manager (full-time, Deaf hire) | 1 | $140k | $140k |
| Linguistics consultant (ASL PhD, part-time) | 0.5 | $90k | $90k |
| Product designer (accessibility specialist) | 1 | $170k | $170k |
| Founders | 2 | $150k | $300k |
| **Annual people cost** | **8.5 FTE** | | **~$1.73M / year** |

24-month people cost: **~$3.5M**.

### D. Total 24-month cost

| Bucket | $ |
|---|---|
| Data acquisition | $350k |
| Compute | $120k |
| People (24 mo) | $3.5M |
| Legal, SOC 2, infra, ops | $200k |
| Deaf advisory board (paid, 5 people × 2 yr) | $250k |
| Sales & marketing (modest, B2B-led) | $400k |
| Buffer (15%) | $720k |
| **TOTAL 24-mo capital required** | **~$5.5M** |

This maps to a **~$4M seed → $15M Series A** path (rather than the v1 plan's $1M pre-seed). The thesis must clear that higher bar to be venture-fundable.

---

## 1.4 — Timeline (24 months, gated)

```
M0 ─────────── M6 ─────────── M12 ─────────── M18 ─────────── M24
│              │              │               │               │
PHASE 1        PHASE 2        PHASE 3         PHASE 4         GA
Foundation     Linguistic     Generative      Production      Launch
& Data         Model          + Avatar        SDK             
```

### Phase 1 (M0–M6) — Foundation & data, $1.4M

**Goal:** Have a usable proprietary corpus and a working Stage 1+2 (audio → linguistic plan).

- Deaf advisory board operational + first contract on signed `Community Charter`
- Markerless capture rig stood up at studio partner (Gallaudet's Tech Access Program is the natural collaborator)
- 60h ASL captured (40h instructional, 20h conversational) — adds to the 80h How2Sign baseline
- Fine-tuned ASR+linguistic plan model live; demoable
- **Gate:** Deaf advisory board signs off on Phase 2 entry. If they don't, stop and reorganize.

### Phase 2 (M6–M12) — Linguistic + retrieval, $1.4M

- Motion library indexed (SignCLIP retrieval); BLEU-2 > 25 on internal eval
- Avatar v1 (WebGL, single character, basic NMMs)
- First closed beta with 2 friendly publishers (e.g., an EdTech LMS, a public-broadcaster web property)
- **Gate:** Deaf user-research panel rates intelligibility ≥ 3.5/5 on standardized scale.

### Phase 3 (M12–M18) — Generative + avatar polish, $1.4M

- Constrained transition synthesis in production for inter-anchor gaps only
- NMM channel trained on facial corpus; expressivity meaningfully present
- Avatar diversity (4+ identity options) launched
- SDK alpha; 3 paid pilot contracts ($25–50k ACV)
- **Gate:** SOC 2 Type I; reference-customer NPS ≥ 30.

### Phase 4 (M18–M24) — SDK & scale, $1.3M

- SDK GA; integrations for Brightcove, Kaltura, JW Player, Mux
- Compliance reporting v1 mapped to WCAG 2.2 + EAA + Section 508
- 10+ paid platform contracts; $2M ARR run-rate
- Series A close

---

## 1.5 — Determinism vs. expressivity (the core trade-off)

This is the **most important design decision** the team will make. Plot of options:

```
   FULL NEURAL          RETRIEVAL-AUGMENTED              FULL RETRIEVAL
     (SignDiff,          (COMMITTED — GenASL)            (per-gloss clip
      T2S-GPT,                                            stitching =
      Sorenson POC)                                       the fallback tier)

   ───────────────────────────●────────────────────────────────────
                              ↑
                  • DEFAULT: phrase-level continuous-clip retrieval
                  • Generated TRANSITIONS only (never originates a sign)
                  • Separate generative NMM channel on the retrieved face
                  • Per-gloss stitching is the tagged last resort
                  • Hash-cacheable; auditable

   Expressivity:  ★★★★★            ★★★★☆                ★★☆☆☆
   Determinism:   ★★☆☆☆            ★★★★☆                ★★★★★
   Compute cost:  $$$$              $$                    $
   QA tractable:  hard              moderate              easy
   Failure mode:  uncanny / wrong   sign gaps             stiff / missing grammar
```

**Why retrieval-augmented wins for a regulated B2B product:**

1. **Buyers buy paperwork.** A compliance officer needs to point at a defensible artifact when a Deaf advocacy group challenges output quality. "We are 80% Deaf-signer-recorded; the model only interpolates timing" is a defensible artifact. "It's all generated by a neural network" is not.

2. **Failure modes are bounded.** A retrieval miss produces a momentary gap or a slightly-off-context sign. A generative failure produces an *uncanny* output — a six-fingered hand, an unnatural face — which is reputationally catastrophic with the Deaf community.

3. **Corpus expansion has linear payoff.** Each new MoCap session directly improves coverage. Neural-only systems need orders of magnitude more data per quality jump.

4. **Audit is the moat.** A neural system can be reverse-engineered with public data. A 200h+ Deaf-signer corpus that you own, with explicit consent and royalty agreements, cannot be.

---

## 1.6 — Honest blockers

| Blocker | Severity | Mitigation |
|---|---|---|
| **Coverage of long-tail vocabulary** (medical, legal, technical) | High | Phase 4 onward, dedicated domain MoCap (medical alone is ~$50k for ~30h focused capture) |
| **Multi-signer style transfer** (so users can pick an avatar) | High | Either retarget motion across rigs (well-studied) or capture each identity (expensive). Recommend retarget. |
| **Real-time latency under 200ms** (for live streams) | Medium | Stage 1+2 are streamable; Stage 3 retrieval is O(1); Stage 4 rendering is the bottleneck. Edge-rendered MP4 fallback solves it. |
| **Idiomatic / classifier-heavy ASL** (which is fundamentally generative, not lexical) | High | Honestly disclose this in the product positioning; some content (poetry, narrative ASL) will remain out-of-scope for years. |
| **No standard evaluation for "good" generated ASL** | Medium | Run a quarterly Deaf-rater panel against fixed test sets; publish results. Treat this as the brand's most important transparency artifact. |

---

## 1.7 — Verdict on technology feasibility

**Buildable.** With ~$5.5M and 24 months, this team can ship a production-grade speech-to-3D-avatar ASL system that is *materially better* than the current PoC and *competitive with anything else on the market*.

**Buildable to what fidelity?**

- For instructional/expository content (news, education, corporate training, gov't service videos): **Yes — usable as the primary ASL track for many viewers, with the caveat that complex narrative remains hard.**
- For entertainment, narrative, poetic ASL: **No, not in this scope.** Position as out-of-scope.
- For live broadcast: **Yes with caveats** — latency budget is achievable with the proposed pipeline.

The technology is not the risk. **The data, the community trust, and the corpus consent flow are the risk.** Those are organizational and ethical questions, not engineering ones.
