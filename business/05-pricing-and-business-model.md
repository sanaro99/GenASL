# 5 — Pricing, Unit Economics & Build Cost

This section sets the commercial model (**platforms pay, end users never do**), the unit
economics, the capital required to build the committed product, and a 5-year revenue
scenario. Assumptions are conservative and documented.

---

## 5.1 — Why platform-pays (the model decision)

The monetisation model is settled and is an invariant of the project, not a tactic. The
entity that *owns the video inventory* pays GenASL on behalf of all its viewers; the
viewer is never billed. Eight reasons, ordered by importance (full comparison in
[F4](feasibility-study/04-pricing-strategy-comparison.md)):

1. **Value capture should follow value creation.** Most induced value
   ([F3](feasibility-study/03-market-expansion.md)) flows to platforms — engagement,
   compliance-risk reduction, brand. Pricing follows the value.
2. **Deaf users must not pay for access.** Charging Deaf viewers to reach content hearing
   viewers get free is the opposite of accessibility, and a non-negotiable position with
   the community.
3. **The compliance gun points at the platform, not the viewer.** ADA/EAA exposure — and
   therefore budget — sits with the operator.
4. **Integration moat > feature moat.** A platform that has embedded the SDK in its player
   and compliance pipeline faces a multi-month project to switch out.
5. **One contract = millions of viewers.** A single LMS integration reaches ~100M learners;
   consumer scale is 1:1.
6. **Per-minute pricing matches the existing budget vocabulary.** Procurement already buys
   "per-minute captioning"; "per-minute ASL" is a line item, not a new category.
7. **It never competes with itself for the Deaf market.** B2B is unambiguous: platform pays,
   users get access free.
8. **Strategic acquirers want enterprise ARR.** 3Play, Verbit, Sorenson all price on
   enterprise multiples.

A small consumer **showcase** (free Chrome extension; an optional learner web tool) exists
for product demo, Deaf-community benefit, and partner recruiting — capped at **≤10% of
engineering effort** and **<5% of revenue**. It is signal, not P&L.

---

## 5.2 — Pricing structure (three platform tiers)

### Tier 1 — Developer / SDK (self-serve, PLG)

| | |
|---|---|
| **Price** | Free up to 1,000 min/month; **$1.20/min** above |
| **Includes** | SDK + API; basic compliance log; community support |
| **Purpose** | Remove friction for technical evaluators; funnel into Tier 2 |
| **Motion** | Self-serve, no salesperson |

### Tier 2 — Platform (mid-market)

| | |
|---|---|
| **Price** | **$2,500 – $15,000/mo** committed; effective **~$0.60–0.90/min** at volume |
| **Includes** | Production SLA (99.5%); WCAG/EAA/508 compliance reports; custom avatar; account manager |
| **Comparable** | 3Play Pro-tier; Verbit education contracts |
| **Target** | EdTech platforms, mid-market LMSes, regional broadcasters, large enterprise L&D |

### Tier 3 — Strategic (enterprise / platform-scale)

| | |
|---|---|
| **Price** | **$150k – $1M+ ACV** with volume commitment + custom terms |
| **Includes** | Tier 2 + self-hosted appliance; custom Deaf-signer corpus; SOC 2 Type II; DPA; named avatar; co-marketing |
| **Target** | Big-tech streaming, top-5 broadcasters, federal/national governments, top-50 universities |

### Pricing principles

- **Per-minute is the unit** — the buyer mental model already exists.
- **Volume curve**: $1.20/min self-serve → ~$0.30/min at 1M+ min/yr committed. The bracket
  sits **1–3× over commodity captioning** ($0.25–0.95/min) — correct for a premium specialty
  add-on, well under human ASL ($300–800/min).
- **Self-hosted is the up-sell**, not the floor: regulated buyers (gov, health, finance)
  demand on-prem; charge for it.
- **Always free for Deaf-led organisations** — NAD, NBDA, Gallaudet, recognised state
  associations. Trivial cost, large reputational and feedback gain.

---

## 5.3 — Build cost: what the committed product actually requires

The "middle of ASL" is a real build — clean data, compute, and people. This is why the
plan needs a **seed (~$4–5M)**, not a pre-seed bridge. Figures USD, conservative midpoints
(detail in [F1 §1.3](feasibility-study/01-technology-feasibility.md)).

### A. Data — the biggest strategic line item

| Component | Approach | Cost |
|---|---|---|
| Public corpora (OpenASL, ASL Citizen, YouTube-ASL) | License + clean | **~$30k** |
| Proprietary capture (Deaf signers, ~200 h) | **Markerless** RGB + 3D pose + Deaf-signer labor | **$70k – $90k** |
| Facial / NMM capture | ARKit/MetaHuman-class | **$30k – $80k** |
| Annotation + QA (Deaf linguists verify gloss/NMMs) | ~1,500 h | **$120k – $180k** |
| **Realistic data spend** | Markerless + facial + Deaf QA | **~$280k – $400k** |

### B. Compute (not the constraint)

| Phase | Cost |
|---|---|
| Initial training (motion VQ-VAE + transition model) | ~$17k |
| Diffusion/ablations + NMM channel | ~$35k |
| Continual retrains (Y2+) | ~$3k/mo |
| Inference at scale | **~$0.01–0.05/min** |
| **24-month compute budget** | **~$120k** |

### C. People (the real cost)

~8.5 FTE — 2 ML researchers, 1 ML/inference engineer, 1 WebGPU/frontend, 1 backend/SDK,
1 Deaf community manager (Deaf hire), 0.5 ASL-linguistics consultant, 1 product designer,
2 founders → **~$1.73M/year, ~$3.5M over 24 months.**

### D. Total 24-month capital

| Bucket | $ |
|---|---|
| Data acquisition | $350k |
| Compute | $120k |
| People (24 mo) | $3.5M |
| Legal, SOC 2, infra, ops | $200k |
| Deaf advisory board (5 × 2 yr, paid) | $250k |
| Sales & marketing (modest, B2B-led) | $400k |
| Buffer (15%) | $720k |
| **TOTAL** | **~$5.5M** |

→ a **~$4M seed → ~$15M Series A** path. The thesis must clear that bar to be
venture-fundable; if it can't raise the round, the right move is the research/open-source
fallback, not a thin consumer bridge.

---

## 5.4 — Unit economics (per-customer, steady-state)

### Tier 2 platform — per $90k ACV contract

| Line item | $ | Notes |
|-----------|---|-------|
| ACV | **+$90,000** | ~$7.5k/mo committed |
| Inference (retrieval + NMM synth) | -$3,000 | ~$0.03/min × ~100k min/yr |
| Infra, storage, CDN | -$4,000 | Aggressive caching; per-stage disk cache |
| CSM / support amortised | -$9,000 | |
| **Gross profit** | **+$74,000** | **~82% gross margin** |
| Sales cost amortised | -$18,000 | ~20% S&M |
| Implementation (Y1 only) | -$8,000 | |
| **Year-1 contribution** | **+$48,000** | |
| **Year-2+ contribution** | **+$56,000** | Implementation falls off |

### Tier 1 self-serve — annual

| Line item | $ | Notes |
|-----------|---|-------|
| ARPA | **+$6,000** | ~$500/mo modest usage above free tier |
| Inference + infra | -$900 | |
| Payment + self-serve support | -$300 | |
| **Gross profit** | **+$4,800** | **~80% margin** |
| CAC (PLG, content-led) | -$600 | |
| **Contribution after CAC** | **+$4,200** | |

---

## 5.5 — Revenue scenario (5-year, platform-pays primary)

Conservative case, USD, rounded.

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---:|---:|---:|---:|---:|
| Tier 1 (self-serve) — paid | 5 | 30 | 150 | 400 | 800 |
| Tier 1 ARR | $30k | $200k | $900k | $2.4M | $4.8M |
| Tier 2 — contracts | 0 | 4 | 15 | 35 | 70 |
| Tier 2 ARR | $0 | $300k | $1.4M | $3.5M | $7.0M |
| Tier 3 — contracts | 0 | 1 | 4 | 10 | 20 |
| Tier 3 ARR | $0 | $300k | $1.5M | $4.0M | $10.0M |
| Consumer/education (showcase) | n/a | n/a | $100k | $300k | $600k |
| **TOTAL ARR** | **$30k** | **$800k** | **$3.9M** | **$10.2M** | **$22.4M** |
| Blended gross margin | 60% | 70% | 76% | 80% | 82% |

This lands ~$22M Y5 ARR with **~90 platform contracts** — 15× fewer customers than a
consumer model at the same revenue, with stronger margins and a defensible enterprise base
for acquisition or Series B.

---

## 5.6 — What we deliberately do NOT charge for

- **Deaf-native access.** Free forever; verified Deaf-led orgs get full free use.
- **The Chrome extension.** Always free to install; it's a showcase, not a gate.
- **The open-source core pipeline.** Self-hosting the code is permitted; we monetise hosted
  infra, the curated proprietary corpus, compliance reporting, and support — *not the code*.

---

## 5.7 — Sensitivity & risks to the model

| Sensitivity | Effect |
|------------|--------|
| **Tier 1 self-serve underperforms** | Y5 ARR drops ~$5M; Tier 2/3 still carry a ~$17M business |
| **Tier 3 ACV falls 50%** | Y5 ARR drops ~$5M; signals acquire-or-roll-up rather than independent scale |
| **Inference cost rises 3×** | Tier 2 margin falls 82% → ~76% — still healthy |
| **A platform ships native ASL** | Showcase tier obsolete; enterprise/gov/EdTech contracts unaffected → 100% B2B focus |
| **Sorenson out-executes on distribution** | Compete on Deaf-trust + auditable corpus + media-overlay niche; or pursue acquisition at 5–8× ARR |
| **Acquisition by incumbent** | Plausible Y3–Y5 at 5–8× ARR ($200–500M outcome range) |

The model's largest single dependency is **Tier 2/3 platform ACV.** If platform sales
don't land by month 18, that — not engineering velocity — is the signal to pivot to a
Signapse-style focused-vertical service business or to the research/open-source fallback.
