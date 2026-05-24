# 5 — Pricing & Business Model

This section proposes a concrete pricing structure, unit economics, and revenue scenarios. All assumptions are conservative and documented.

---

## 5.1 — Pricing structure

GenASL needs **three pricing surfaces** because the buyer segments differ in size, sales motion, and willingness to pay.

### Tier 1 — Free (Learner)

| | |
|---|---|
| **Price** | $0 |
| **Limits** | 5 videos / day; 20-min max video length; gloss overlay only; no offline mode |
| **Purpose** | Top-of-funnel; corpus feedback; community goodwill |
| **Conversion target** | 3% to Pro |

### Tier 2 — Pro (Learner)

| | |
|---|---|
| **Price** | **$9 / month** or **$72 / year** (~33% annual discount) |
| **Includes** | Unlimited videos; pause-on-sign learning mode; per-sign mastery tracking; vocab builder; offline favorites; one device + mobile add-on at $3 |
| **Purpose** | Sustain consumer funnel; cover its own infra cost |
| **Comparable** | Lingvano ($12/mo), Duolingo Super ($14/mo), Memrise ($9/mo) |

### Tier 3 — Education (B2B)

| | |
|---|---|
| **Price** | **$4 / student-seat / year**, 100-seat minimum (= $400 min ACV); free for Title I schools |
| **Includes** | Centrally-managed extension deployment via Google Admin / GPO; teacher dashboard; assignment mode (assign a YouTube URL → see student progress); SSO; usage reports |
| **Purpose** | Education beachhead; reference customers |
| **Comparable** | Quizlet Plus for Schools ($4.99/student); Newsela ($18/student) — we are deliberately at the low end |

### Tier 4 — Enterprise (B2B)

Two metering options because regulated buyers prefer predictability while EdTech buyers prefer variability.

#### 4a) Per-minute (transactional)

| | |
|---|---|
| **Price** | **$1.50 / minute** of video processed; volume discounts to $0.80/min at 100k+ min/yr |
| **Includes** | API + SDK; coverage reporting per video; web dashboard; SOC 2 attestation |
| **Comparable** | 3Play captioning ~$0.90/min; Verbit ~$0.95/min — we price at ~1.5× because ASL is a premium add-on |

#### 4b) Annual platform (committed)

| | |
|---|---|
| **Price** | **$30k – $120k ACV**, tiered by minute commitment + premium support |
| **Includes** | Self-hosted appliance option (Docker + Ollama); on-prem corpus; dedicated CSM; SLA; custom corpus add-ons |
| **Purpose** | Predictable enterprise revenue; sticky logos |
| **Comparable** | 3Play average enterprise spend ~$117k/yr per [Vendr](https://www.vendr.com/buyer-guides/3play-media) |

---

## 5.2 — Unit economics (per-customer, steady-state assumptions)

### Pro (B2C) — annual

| Line item | $ | Notes |
|-----------|---|-------|
| ARPU | **+$72** | Annual plan modeled |
| LLM inference (gloss translation) | -$4 | ~$0.005 per minute × ~800 min/yr avg usage |
| Storage + bandwidth (chained clips) | -$2 | Aggressive caching |
| Payment processing | -$3 | ~4% |
| Customer support amortized | -$2 | Mostly self-serve |
| **Gross profit** | **+$61** | **84% gross margin** |
| CAC (organic + small paid) | -$15 | Education content marketing led |
| **Contribution after CAC** | **+$46** | LTV/CAC ≈ 4.9 at 2-yr retention |

### Education — per district pilot (300-student school)

| Line item | $ | Notes |
|-----------|---|-------|
| ARR | **+$1,200** | 300 × $4 |
| Service delivery (onboarding, support) | -$200 | Mostly automated |
| Infrastructure | -$100 | |
| **Gross profit** | **+$900** | **75% gross margin** |
| Sales cost amortized | -$300 | Inside-sales rep, low-touch |
| **Net contribution** | **+$600** | Education is thin on margin but a credibility play |

### Enterprise — per $60k ACV contract

| Line item | $ | Notes |
|-----------|---|-------|
| ACV | **+$60,000** | |
| Service delivery, CSM amortized | -$8,000 | |
| Infrastructure (incl. self-host support) | -$3,000 | |
| Implementation engineer time | -$5,000 | First-year only |
| **Year-1 gross profit** | **+$44,000** | **73% gross margin** |
| Sales cost | -$15,000 | ~25% S&M ratio |
| **Year-1 contribution** | **+$29,000** | |
| **Year-2+ contribution** | **+$44,000** | Implementation cost falls off |

---

## 5.3 — Revenue scenario (5-year)

Conservative case. All numbers in USD, rounded.

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---:|---:|---:|---:|---:|
| **Pro subscribers (paid)** | 2,000 | 8,000 | 20,000 | 40,000 | 70,000 |
| **Pro ARR** | $144k | $576k | $1.4M | $2.9M | $5.0M |
| **Education ARR** | $50k | $400k | $1.2M | $2.4M | $4.0M |
| **Enterprise contracts** | 0 | 3 | 12 | 30 | 60 |
| **Enterprise ARR** | $0 | $180k | $720k | $1.8M | $3.6M |
| **Per-minute API ARR** | $0 | $50k | $400k | $1.5M | $5.0M |
| **Government / public sector** | $0 | $0 | $250k | $1.5M | $4.0M |
| **TOTAL ARR** | **$194k** | **$1.2M** | **$4.0M** | **$10.1M** | **$21.6M** |
| **Blended gross margin** | ~70% | ~73% | ~76% | ~78% | ~80% |

This puts year-5 revenue inside the SOM band derived in [02-market-analysis.md](02-market-analysis.md). It is comparable to where Signapse should be in ~3 years from its 2024 seed, and below Hand Talk's regional scale.

---

## 5.4 — Why this pricing works

| Decision | Rationale |
|----------|-----------|
| **Freemium consumer tier** | Build the corpus and brand without paid acquisition; learners are forgiving of an imperfect product |
| **Education priced 50% below Quizlet** | Buying ASL access is a moral as well as financial decision; low friction matters more than ARPU |
| **Per-minute API at ~1.5× captioning rates** | Anchors against the buyer's existing accessibility budget; ASL is positioned as a *complement to* captions, not a replacement |
| **Self-hosted enterprise option** | Differentiates from Signapse/Hand Talk cloud-only models; opens regulated buyers (gov, health, finance) |
| **Title I schools free** | Reputational + community-trust dividend; trivially small revenue forgone |

---

## 5.5 — What we're deliberately NOT charging for (yet)

- **Deaf-native consumer use.** A "Community Free" tier for verified Deaf community members (Gallaudet email, NAD member ID) costs us almost nothing in infra and is the right answer regardless of revenue.
- **Open-source self-host of the core pipeline.** The current GPLv3 license means anyone can self-host the pipeline themselves; we monetize support, hosted infra, the curated corpus, and compliance reporting — not the code.
- **The Chrome extension itself.** Always free to install; gates are inside the app.

---

## 5.6 — Sensitivity & risks to the model

| Sensitivity | Effect |
|------------|--------|
| **Pro conversion drops 3% → 1.5%** | Year-5 Pro ARR halves to ~$2.5M; total ARR still ~$19M because enterprise dominates |
| **Enterprise ACV falls 50%** | Year-5 ARR drops ~$5M; signals we need to be acquired or roll up |
| **LLM costs rise 3×** | Pro gross margin falls 84% → 76% — still very healthy |
| **YouTube ships native ASL** | Pro tier obsolete overnight; enterprise/education unaffected → pivot 100% to B2B |
| **Acquisition by 3Play / Verbit** | Year 3–4 plausible at ~5× ARR ($20–50M exit on $4–10M ARR) |

The model is robust to the failure of any single channel because each segment has a different decision-maker and different motivator. The largest single dependency is **enterprise ACV** — if that breaks, the business is venture-fundable only as an education startup, not a true accessibility-tech company.
