# F4 — Pricing Strategy: Platform-Pays vs. Consumer-Pays

> **Question:** You've said you don't want to charge end users — platforms should pay. How does that compare with the consumer-pays approach, and which actually wins?
> **Short answer:** **Platform-pays wins on every dimension that matters for an accessibility tool** *except* speed-to-first-revenue. Run platform-pays as the primary motion; keep a tiny consumer surface alive only as a product showcase and a Deaf-community free benefit.

---

## 4.1 — What "platform-pays" actually means

Platform-pays is **B2B-only** monetization where the entity that *owns the video inventory* pays GenASL on behalf of all its viewers. Three categorical buyer groups:

| Buyer category | Examples | Why they pay |
|---|---|---|
| **Streaming + UGC platforms** | YouTube, TikTok, Vimeo, Twitch, Mux | Compliance + engagement + competitive parity once one of them ships ASL |
| **Education / EdTech platforms** | Coursera, Khan Academy, Canvas, Brightspace, Udemy, Pluralsight | Accessibility line item; Section 508; institutional procurement requirements |
| **Enterprise + public-sector publishers** | Government portals, banks, healthcare networks, news broadcasters, BBC iPlayer–class media | ADA Title II / EAA compliance; brand and reputational risk |

In each case, the *end-user is not billed*. The platform integrates the GenASL SDK or API and pays per-minute, per-stream, or via committed annual contract.

---

## 4.2 — Side-by-side comparison

| Dimension | **Platform-pays (B2B)** | Consumer-pays (B2C) |
|---|---|---|
| Who you sell to | ~500 mid-market platforms + ~50 strategic accounts | ~5M+ individuals + schools |
| Sales motion | Founder-led / inside sales; long cycles | Self-serve; performance marketing |
| Avg contract value | **$30k – $300k+ ACV** | $72/yr (Pro), $400 min (Education) |
| # of contracts to hit $10M ARR | ~80 platform contracts | ~140k Pro subscribers |
| Sales cycle | 3–12 months | minutes |
| Customer concentration risk | High (top 10 = >50% revenue) | Low |
| LTV / CAC ratio | 5–15× when it works | 2–5× when it works |
| Time to first $1M ARR | ~18 months | ~9 months |
| Time to $10M ARR | ~30 months | ~36 months (with paid marketing) |
| Time to $50M ARR | ~5 yr (plausible) | ~7+ yr (compounding consumer churn) |
| Margin profile | **78–85% gross** | 75–82% gross |
| Defensibility / moat | **Strong** — integrations stick | Weak — apps churn |
| Deaf-community alignment | **Strong** — users not billed for accessibility | Weak — charging Deaf-related access feels off-brand |
| Compliance ROI to buyer | **Clear** — line item against ADA/EAA risk | n/a |
| Platform-build risk | **Real** — platforms could build internally | Low |
| Captures induced demand from [F3](03-market-expansion.md) | **Yes** — value flows match where it's created | No — most users wouldn't pay |
| Regulatory tailwinds | Strong — ADA Title II + EAA target operators of digital services | None |
| Brand fit with mission | **High** | Mixed |
| Quality bar required | High — enterprise procurement scrutiny | Medium — consumer tolerance for imperfection |
| **Verdict** | **Primary motion** | **Showcase / charity-tier only** |

---

## 4.3 — Why platform-pays is the right answer for *this* product

Eight reasons, ordered by importance:

1. **Value capture should follow value creation.** [F3](03-market-expansion.md) showed most induced value flows to platforms (engagement, compliance risk reduction). Pricing should follow.

2. **Deaf users should not pay for access.** This is a non-negotiable position with the community. Charging Deaf users to access content that hearing users access free is the opposite of accessibility. A consumer-pays primary motion forces uncomfortable tier design or undercuts community trust.

3. **The buyer with the compliance gun pointed at them is the platform, not the viewer.** ADA lawsuits target operators, not consumers ([Deque](https://www.deque.com/blog/companys-videos-sued-ada-noncompliance/)). EAA fines target service providers. Procurement budgets follow legal exposure. That budget *exists* — it's spent on captioning today and ASL tomorrow.

4. **Integration moat dominates feature moat.** Once a platform has integrated a GenASL SDK into their player and their compliance pipeline, switching is a multi-month engineering project. That is a far more durable moat than a consumer app.

5. **One platform contract = millions of viewers reached.** A single integration with Coursera reaches ~100M learners; one with Mux or JW Player powers tens of thousands of broadcasters. Consumer scale is 1:1 — platform scale is 1:millions.

6. **Per-minute pricing aligns with the existing accessibility budget vocabulary.** Procurement officers know how to buy "per-minute captioning." Adding "per-minute ASL" is a budget line, not a category-creation conversation. Consumer pricing requires educating each individual.

7. **It's the only model that doesn't compete with itself for the Deaf market.** A B2C ASL app for learners is a competitor to itself if it also serves Deaf primary users — different jobs, different acceptable fidelities. A B2B model is unambiguous: the platform pays; users get access free.

8. **Strategic exits prefer enterprise revenue.** 3Play, Verbit, Sorenson — all likely future acquirers — are enterprise companies. They want enterprise ARR multiples, not consumer multiples.

---

## 4.4 — Where consumer-pays still helps (a small, deliberate role)

Even with platform-pays primary, **two small consumer surfaces should exist:**

| Surface | Why keep it | What NOT to do |
|---|---|---|
| **Free Chrome extension showcase** | Product demo; recruiting platform partners ("look, your competitor's site loads ASL via our extension"); recruiting Deaf community feedback | Do not paywall it; do not collect viewer data for ads |
| **Educator + Learner web app (small paid tier)** | Validates Channel B (learner growth from [F3](03-market-expansion.md)); brings teachers' voice into product feedback | Do not over-invest; cap engineering at ~10% of total effort; don't let it dilute focus |

Total revenue contribution of these consumer surfaces in steady state: **<5%.** Their value is brand and signal, not P&L.

---

## 4.5 — Recommended pricing structure (platform-pays)

Three commercial tiers covering the buyer spectrum:

### Tier 1 — Developer / SDK (self-serve)

| | |
|---|---|
| **Price** | Free up to 1,000 minutes/month; **$1.20/min** above that |
| **Includes** | SDK + API; basic compliance log; community support |
| **Purpose** | PLG funnel for mid-market platforms; remove friction for technical evaluators |
| **Sales motion** | Self-serve; no salesperson required |

### Tier 2 — Platform (mid-market)

| | |
|---|---|
| **Price** | **$2,500 – $15,000/mo** committed; effective per-minute ~$0.60 – $0.90 at volume |
| **Includes** | Production SLA (99.5%); compliance reports with WCAG/EAA/Section 508 mapping; custom avatar; account manager |
| **Comparable** | 3Play Pro-tier captioning; Verbit education contracts |
| **Target buyers** | EdTech platforms, mid-market LMSes, regional broadcasters, large enterprise L&D |

### Tier 3 — Strategic (enterprise / platform-scale)

| | |
|---|---|
| **Price** | **$150k – $1M+ ACV** with volume commitment + custom terms |
| **Includes** | Tier 2 + self-hosted appliance option; custom Deaf-signer corpus; SOC 2 Type II; DPA; named avatar; co-marketing |
| **Target buyers** | Big-tech streaming, top-5 broadcasters, federal/national governments, top 50 universities |

### Pricing principles

- **Per-minute as the unit**: matches how every captioning incumbent prices, so the buyer mental model exists.
- **Volume discount curve**: starts at $1.20/min self-serve, falls to $0.30/min at 1M+ min/yr committed. This *bracket* sits 1–3× over captioning ($0.50–$0.95/min commodity), which is correct because ASL is positioned as the premium specialty add-on.
- **Self-hosted as the up-sell, not the bottom**: regulated buyers (gov, health, finance) demand on-prem; charge for the privilege.
- **Always free for Deaf community organizations**: NAD, NBDA, Gallaudet, recognized state associations. Trivial revenue cost, large reputational and feedback gain.

---

## 4.6 — Revised 5-year revenue projection (platform-pays primary)

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---:|---:|---:|---:|---:|
| Platforms — Tier 1 (self-serve) | 5 paid | 30 | 150 | 400 | 800 |
| Tier 1 ARR | $30k | $200k | $900k | $2.4M | $4.8M |
| Platforms — Tier 2 | 0 | 4 | 15 | 35 | 70 |
| Tier 2 ARR | $0 | $300k | $1.4M | $3.5M | $7.0M |
| Platforms — Tier 3 | 0 | 1 | 4 | 10 | 20 |
| Tier 3 ARR | $0 | $300k | $1.5M | $4.0M | $10.0M |
| Consumer / Education (showcase) | n/a | n/a | $100k | $300k | $600k |
| **TOTAL ARR** | **$30k** | **$800k** | **$3.9M** | **$10.2M** | **$22.4M** |
| Blended gross margin | 60% | 70% | 76% | 80% | 82% |

This lands at the same year-5 ARR as the v1 mixed model (~$22M), but with **15× fewer customers, much stronger gross margin, and a defensible enterprise revenue base for acquisition or Series B.** It is the better-quality revenue.

---

## 4.7 — Comparative honest scorecard

| Criterion | Platform-pays | Consumer-pays | Hybrid (v1 plan) |
|---|:--:|:--:|:--:|
| Speed to first $100k ARR | ⚠️ slow (6–12 mo) | ✅ fast (3 mo) | ✅ fast |
| Total addressable revenue at Y5 | ✅ $22M | ⚠️ ~$8–10M | ✅ ~$22M |
| Concentration risk | ⚠️ high | ✅ low | medium |
| Margin quality | ✅ high | medium | medium |
| Defensibility | ✅ high | low | medium |
| Mission / ethics fit | ✅ excellent | ⚠️ awkward | medium |
| Deaf-community alignment | ✅ strong | ⚠️ weak | medium |
| Captures induced demand | ✅ yes | ⚠️ no | partial |
| Vulnerable to platform-build | ⚠️ real risk | ✅ no | partial |
| Acquisition multiple at exit | ✅ 6–10× ARR | ⚠️ 3–6× | 4–7× |
| **Recommended primary motion** | ✅ **YES** | ❌ | ❌ |

---

## 4.8 — The harder question: what about consumer-pays as a *bridge*?

A founder could reasonably ask: *should we run consumer-pays for 6–12 months to generate revenue while we build the platform sales motion?* This is a tactical, not strategic, question.

**My honest read:**
- **No, if you can raise.** The $5.5M seed budgeted in [F1 §1.3](01-technology-feasibility.md) buys you 24 months without needing bridge revenue. Use that time. Consumer-pays right now would distract a 3-ML-engineer team for marginal cash.
- **Yes, if you can't raise.** If pre-seed is the only option, a free + cheap-Pro Chrome extension generates a tiny revenue trickle (~$300–700k/yr) that buys time. But then you have *two* products to maintain, and the v1 trade-offs apply.

Bridge if you must. Don't bridge if you don't.

---

## 4.9 — Bottom line

**Platform-pays is the right primary motion** for a serious, ethical, defensible production GenASL. Consumer surfaces should exist for showcase and Deaf-community benefit, not for primary revenue. The revenue model below the line is unambiguous:

> Per-minute B2B pricing, 1–3× the captioning-incumbent rate, with volume discount, self-hosted up-sell, and a free tier for Deaf-led organizations and small developers. End users are never billed for access to ASL.
