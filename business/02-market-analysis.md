# 2 — Market Analysis

This section sizes the opportunity from four angles: **who needs ASL**, **why someone
will pay for it**, **how big the addressable market is**, and — the question the old plan
under-counted — **how much a credible tool *grows* that market**.

---

## 2.1 — Population & demand: who actually uses ASL

Sign-language demographics are noisy because surveys conflate three populations: people
with hearing loss, people who are functionally Deaf, and people who use a signed language
daily. The numbers below separate them and are refreshed to May 2026.

### United States

| Population | Estimate | Notes |
|-----------|----------|-------|
| Adults reporting **some hearing loss** | **~48 million** | NIDCD; broadest definition |
| **Functionally Deaf** adults | **~2 million** | Cannot hear normal conversation |
| **Culturally Deaf** (capital-D, ASL-using community) | **~500,000 – 1,000,000** | Primary-language ASL users |
| Adults using **some sign language** | **~6.4 – 7.0 million** | ~2.8% of US adults; ~83% hearing |
| **ASL learners** (HS + college + adult ed) | **~250,000 – 500,000 active/year** | ASL is the **3rd most-studied language** in US universities |

Sources: [NIDCD](https://www.nidcd.nih.gov/health/statistics/quick-statistics-hearing),
[ASL Bloom](https://www.aslbloom.com/blog/how-many-people-use-asl),
[RIT InfoGuides](https://infoguides.rit.edu/c.php?g=380750&p=9393643).

### Global

| Population | Estimate |
|-----------|----------|
| People with disabling hearing loss worldwide (WHO) | ~430 million |
| Deaf signers globally (WFD) | **~70 million** |
| Sign languages in use | 300+ (only ~82 with legal recognition) |

Source: [WFD](https://wfdeaf.org/).

### What this means for GenASL

- **The primary-user market is small but high-conviction.** ~1M ASL-first users in the US
  is a niche by mass-consumer standards, but they are highly engaged, advocacy-organised,
  and legally protected. *They are not the customer — they are the reason the customer pays.*
- **ASL is a growth language.** In the most recent MLA census, ASL was one of only three
  languages (with Korean and biblical Hebrew) whose US university enrolments *grew*
  (~108k enrolees, 487 programmes). The learner market is expanding while most language
  study contracts.
- **The architecture generalises.** English→ASL-plan→retrieval generalises to BSL, AUSLAN,
  and other signed languages with their own corpora — a reuse path, not a rebuild.

---

## 2.2 — Demand drivers: why a platform writes a check

Three forces pull money into accessible video. GenASL must align with at least one; it
aligns with all three.

### Driver A — Compliance & litigation (refreshed)

| Lever | Detail (May 2026) |
|-------|--------------------|
| **ADA Title II — deadline *extended*** | The web/mobile accessibility deadline moved from April 24, 2026 to **April 26, 2027** (entities ≥50k pop.) and **April 26, 2028** (smaller / special districts), via a DOJ interim final rule effective April 20, 2026. The rule explicitly cites *the limits of current technology, including generative AI, to automate accessibility remediation at scale* — a buying signal as much as a delay. ([Federal Register](https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web)) |
| **ADA litigation volume** | After dipping in 2023–24, filings **rebounded to ~3,900 in 2025 (+24% YoY)**; H1 2025 was +37% vs. H1 2024. Settlements run **$10k–$75k per violation** plus remediation. ([EcomBack](https://www.ecomback.com/annual-2025-ada-website-accessibility-lawsuit-report)) |
| **EU Accessibility Act (EAA)** | Live across all 27 member states since **June 28, 2025**. Audiovisual media services must provide captions, audio description, and — where appropriate — **sign-language interpretation**. Penalties vary (Italy: up to 5% of turnover; Germany: up to €100k). ([3Play — EAA](https://www.3playmedia.com/blog/european-accessibility-act-eaa/)) |
| **Section 508 / CVAA** | US federal procurement requires accessible video; CVAA covers online video previously aired on TV. |

**Why the extension *helps* GenASL.** A deadline already in the past creates remediation
panic that favours quick caption fixes. A deadline in **2027–2028** creates a procurement
*planning* window — exactly the horizon on which a buyer can adopt a new ASL line item, and
exactly the 24 months GenASL needs to ship a defensible product. The DOJ itself flagging
that current AI can't remediate at scale is an invitation to the vendor who can.

### Driver B — The quality / UX gap captions don't close

YouTube auto-captions still carry a **~30% error rate** on real-world video; AI
transcription benchmarks at 80–95%, below the 99% accessibility threshold
([Taption](https://www.taption.com/blog/en/video-accessibility-compliance-2025-en)). ASL
is not a better caption — it is a *different channel*, and for ~1M primary ASL users it is
the channel in their first language. Captions and ASL are complements, not substitutes.

### Driver C — ASL is the next vertical for the accessibility industry

The captioning market is consolidating around 3Play, Verbit, Rev, and AI Media; ASL is
the next surface to upsell. The defining 2025–26 event proves it: **Sorenson** — the
incumbent VRS provider — [acquired Hand Talk and OmniBridge](https://sorenson.com/newsroom/sorenson-acquires-omnibridge-and-hand-talk-to-develop-automated-sign-language-translation-capabilities/)
and is [demoing AI ASL avatars](https://sorenson.com/newsroom/sorenson-communications-unveils-ai-sign-language-translation-ast-proofs-of-concept/).
Demand for "ASL on top of existing access services" is forming, not stagnant — which makes
GenASL either a feature an incumbent builds (acquisition exit) or a specialised layer that
integrates with their pipelines (partnership/SDK play).

---

## 2.3 — Market sizing: TAM / SAM / SOM

Analyst figures for "captioning" disagree by an order of magnitude because some scope
*media localisation* (foreign-language subtitling, ~$30B+) and some scope *focused
accessibility captioning* (hundreds of millions to low billions). We use the **focused**
frame and triangulate against **sign-language-specific** reports, which are smaller but
more honest about GenASL's actual market.

### TAM — Total Addressable Market

| Segment | 2026 size | Source |
|---------|-----------|--------|
| Closed-captioning *services* (focused) | ~$0.6B–$2.5B (analyst range), growing ~10–12% CAGR | [Research Nester](https://www.researchnester.com/reports/captioning-and-subtitling-solutions-market/6638), [Verified Market Reports](https://www.verifiedmarketreports.com/product/closed-captioning-services-market/) |
| Captioning + subtitling *solutions* (broad, incl. localisation) | ~$6B in 2026 → ~$66B by 2035 (6.8% CAGR) | [MRFR](https://www.openpr.com/news/4400913/captioning-subtitling-solution-market-is-estimated-to-grow-usd) |
| Sign-language interpretation *services* | ~$0.89B (2026) → $1.72B (2034), 8.5% CAGR | [Business Research Insights](https://www.businessresearchinsights.com/market-reports/sign-language-interpretation-services-market-112737) |
| Sign-language translation *software/tech* | ~$0.5B–$1.2B (2025–26) → $2.5B–$4.5B (2033), 8–20% CAGR | [DataInsights](https://www.datainsightsmarket.com/reports/sign-language-translation-software-1956596) |
| **Video-accessibility tooling (our blended TAM)** | **~$3.5–4B in 2026, ~$8–10B by early 2030s** | Synthesis |

We anchor TAM on **focused video-accessibility tooling (~$3.5–4B)** because the $30B+
localisation figure is not GenASL's market, and the pure sign-language-tech figures
(~$1–1.5B) under-count the captioning budget GenASL prices *against*.

### SAM — Serviceable Addressable Market

GenASL's near-term reachable market is **English-speaking, regulated digital video** in
the US, UK, Canada, Australia, and Ireland.

- North America ≈ ~40% of global captioning demand → ~$1.4B
- UK + AU + IE + CA add ~10% → ~$1.7B addressable in English-speaking markets
- The **ASL/BSL slice** is ~5–8% of accessibility budgets today, but ADA Title II and the
  EAA (which *names* sign language) are pulling that ratio up.

**SAM estimate: ~$750M in 2026, growing to ~$1.8B by 2030** as compliance demand expands
sign-language line items.

### SOM — Realistic 5-year capture (platform-pays)

| Year | Mix | Revenue |
|------|-----|--------:|
| Y1 | First self-serve SDK pilots | ~$30k |
| Y2 | + first mid-market platform contracts | ~$0.8M |
| Y3 | + Tier-2 platforms scale; first Tier-3 strategic | ~$3.9M |
| Y4 | + public-sector & strategic accounts | ~$10.2M |
| Y5 | Mature platform mix | **~$22M ARR** |

**SOM ≈ $22M ARR by Year 5 ≈ 3–5% of SAM** — achievable with ~90 platform contracts on a
$4M seed → $15M Series A path. Full model in
[05-pricing-and-business-model.md](05-pricing-and-business-model.md).

---

## 2.4 — Induced demand: the tool grows the market

The biggest correction to the old analysis: the ASL-content market is **not fixed**. When
the marginal cost of adding ASL to a video drops from **$300–800/min** (human interpreter)
to **~$0.10–0.40/min** (retrieval-augmented pipeline), the market for the complement grows —
the same dynamic that expanded encyclopaedias (Wikipedia), video (YouTube hosting), and
language learning (Duolingo) by orders of magnitude.

Three growth channels (full model in [F3](feasibility-study/03-market-expansion.md)):

- **A — Latent Deaf demand.** ~1M US primary ASL users abandon the long tail of
  YouTube/Coursera/Khan/TED today because nothing offers ASL. A trustworthy track unlocks
  them. Even +30 min/day of engagement ≈ ~90M incremental user-hours/year in the US alone.
- **B — Hearing learners.** ASL has no Duolingo; the bottleneck is exposure to real ASL in
  everyday content. Conservative Duolingo-style trajectories imply learners growing from
  ~250–500k/yr to ~1.5–3M/yr by 2035.
- **C — Content supply.** If creators' marginal cost to add ASL drops to ~$0, ASL inventory
  explodes — tens of thousands of hours/day if even 1% of educational/news content gets a
  track.

**Modelled induced-demand wedge: ~+$4.5B/yr by 2035, ~3× the baseline market.** The catch,
which founders must internalise: **user counts grow faster than direct revenue**, because
most new beneficiaries (Deaf viewers, learners) don't pay. GenASL captures the slice
*platforms* reallocate from compliance + engagement budgets. This is the central argument
for platform-pays ([F4](feasibility-study/04-pricing-strategy-comparison.md)).

---

## 2.5 — Customer segments ranked by willingness-to-pay

| Segment | Pain | WTP | Notes |
|---------|------|-----|-------|
| **EdTech / LMS / MOOC platforms** | Massive video libraries; Section 508; institutional procurement | **Very high** ($$$) | One integration reaches millions of learners |
| **Government & public-sector portals** | ADA Title II (2027/28); explicit mandate | **Very high** ($$$) | Procurement friction high; deadline now a planning horizon |
| **Streaming / UGC / media platforms** | EAA names sign language; engagement + brand | **High** ($$$) | Competitive parity once one ships ASL |
| **Enterprise publishers (banks, health, training)** | EEOC, brand, internal accessibility | **Medium-High** ($$) | Self-hosted option unlocks regulated buyers |
| **YouTube creators (long-tail)** | Audience growth | **Low** | Reached *through* platform integrations, not billed directly |
| **Deaf-native primary consumers** | Genuine need; rightly skeptical of avatars | **N/A — never billed** | Critical for credibility, not revenue; free forever |

The takeaway, unchanged but sharpened: **revenue comes from platforms and publishers,
never from Deaf end-users.** This is the same economic structure as captioning today.

---

## 2.6 — Market timing assessment

**A good moment to start; a dangerous moment to be late.**

| Tailwind | Headwind |
|----------|----------|
| ADA Title II extended to 2027/28 → a real *planning* window for new line items | LLM/synthesis costs falling — incumbents can build in-house |
| EAA live since June 2025, explicitly naming sign language | Sorenson (post-Hand-Talk) shipping ASL avatars with a huge Deaf customer base |
| Sign-language-tech markets growing 8–20% CAGR | A platform (YouTube/Netflix) could ship native ASL |
| DOJ on record that current AI can't remediate at scale → vendor opening | Deaf-community skepticism rises with hype |

**Conclusion: the window is ~24 months** to establish Deaf-community trust and a defensible
corpus. After that, distribution will be dominated by incumbents (Sorenson) or
platform-native features. The corpus and the community relationships are the only assets
that don't evaporate when a better model ships.
