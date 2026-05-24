# 2 — Market Analysis

This section sizes the opportunity from three angles: **who needs ASL**, **why someone will pay for it**, and **how big the addressable market actually is**.

---

## 2.1 — Population & demand: who actually uses ASL

Sign-language demographics are noisy because surveys conflate three different populations: people with hearing loss, people who are functionally Deaf, and people who use a signed language daily. The numbers below separate them.

### United States

| Population | Estimate | Notes |
|-----------|----------|-------|
| Adults reporting **some hearing loss** | **~48 million** | NIDCD; broadest definition |
| **Functionally Deaf** adults | **~2 million** | Cannot hear normal conversation |
| **Culturally Deaf** (capital-D, ASL-using community) | **~500,000 – 1,000,000** | Primary-language ASL users |
| Adults claiming **some sign-language knowledge** | **~6.4 – 7.0 million** | ACS 2014 extrapolation; ~83% hearing |
| **ASL learners** (high school + college + adult ed) | **~250,000 – 500,000 active learners/year** | ASL is the 3rd most-studied language in US universities |

Source: [NIDCD](https://www.nidcd.nih.gov/health/statistics/quick-statistics-hearing), [RIT InfoGuides](https://infoguides.rit.edu/c.php?g=380750&p=9393643), [ASL Bloom](https://www.aslbloom.com/blog/how-many-people-use-asl).

### Global

| Population | Estimate |
|-----------|----------|
| People with disabling hearing loss worldwide (WHO) | ~430 million |
| Deaf signers globally (WFD) | **~72 million** |
| Recognized national sign languages | 200+ (only ~82 with legal recognition as of 2025) |

Source: [WFD](https://wfdeaf.org/).

### What this means for GenASL

- **The "primary user" market is small but high-conviction.** ~1M ASL-first users in the US is a niche by mass-consumer standards, but they are highly engaged, advocacy-organized, and legally protected.
- **The "ASL-adjacent" market is 10–15× larger.** ASL learners, families of Deaf children (CODAs), interpreters in training, healthcare workers — these are the populations who will pay for an *imperfect* learning aid where Deaf-native users won't.
- **Globally, ASL is *one* of 200+ signed languages.** GenASL's English+gloss approach generalizes to BSL, AUSLAN, and PSE (Pidgin Signed English). Brazil's Hand Talk has shown that a regional signed-language SaaS can hit 10M+ downloads.

---

## 2.2 — Demand drivers: why someone will write a check

Three forces are pulling money into accessible video. GenASL must align with at least one.

### Driver A — Compliance & litigation

| Lever | Detail |
|-------|--------|
| **ADA Title II deadline** | April 24, 2026 — state and local government websites must meet WCAG 2.1 AA. Video content is in scope. |
| **ADA litigation volume** | 4,187 digital-accessibility lawsuits in 2024, pacing **+37% in 2025**. ~77% target companies with **< $25M revenue** — i.e. the mid-market is the litigation hotspot. |
| **Per-violation settlements** | Typically **$10,000 – $75,000**, plus remediation costs. |
| **EU Accessibility Act (EAA)** | Enforcement began June 28, 2025 across 27 member states. Audiovisual media services must offer captions, audio description, **and sign-language interpretation** for certain content types. |
| **Section 508 / CVAA** | US federal procurement requires accessible video; CVAA covers online video that previously aired on TV. |

Source: [Deque](https://www.deque.com/blog/companys-videos-sued-ada-noncompliance/), [3Play Media — EAA guide](https://www.3playmedia.com/blog/european-accessibility-act-eaa/).

### Driver B — Pure quality / UX gap

YouTube auto-captions still have a **~30% error rate** on real-world video. For Deaf viewers, that means **1 in 3 words is wrong**. AI transcription benchmarks at 80–95% accuracy — below the 99% threshold needed for accessibility-grade output ([Taption](https://www.taption.com/blog/en/video-accessibility-compliance-2025-en)). The captioning industry has not solved this; ASL adds an *additional* channel rather than fixing captions.

### Driver C — ASL is the next vertical for the captioning industry

The captioning market is consolidating around 3Play, Verbit, Rev, AI Media. ASL is the next product surface for these incumbents to upsell. GenASL is either:
- a **feature** they'll build internally (acquisition exit), or
- a **specialized layer** that integrates with their pipelines (partnership/SDK play).

Either way, demand for "ASL on top of existing captioning" is forming, not stagnant.

---

## 2.3 — Market sizing: TAM / SAM / SOM

### TAM — Total Addressable Market

The broadest credible frame is **video accessibility tooling**.

| Segment | 2025 size | Source |
|---------|-----------|--------|
| Closed captioning services (focused) | ~$370M – $2.5B (range across analysts) | [GlobalGrowthInsights](https://www.globalgrowthinsights.com/market-reports/captioning-and-subtitling-market-111936), [DataIntelo](https://dataintelo.com/report/global-closed-captioning-services-market) |
| Captioning + subtitling solutions (broad) | $32B (incl. media localization) | [MRFR](https://www.marketresearchfuture.com/reports/captioning-subtitling-solution-market-28263) |
| **Video accessibility tooling (our blended estimate)** | **~$3.0B in 2026, ~$8B by 2033 (~15% CAGR on focused captioning)** | Synthesis |

We use the **focused captioning + accessibility-services figure (~$3.0B in 2026)** as TAM because the $32B figure is dominated by localization (foreign-language subtitling), which is not GenASL's market.

### SAM — Serviceable Addressable Market

GenASL's near-term reachable market is **English-speaking, regulated digital video** in the US, UK, Canada, Australia, and Ireland.

**Derivation:**
- North America = ~40% of global captioning demand → ~$1.2B
- UK + AU + IE + CA add ~10% more → ~$1.5B addressable in English-speaking markets
- Of that, the **ASL/BSL slice** is a fraction. Today sign-language services are perhaps 5–8% of the accessibility budget in regulated buyers, but the EAA and ADA Title II are pulling that ratio up.

**SAM estimate: ~$650M in 2026, growing to ~$1.6B by 2030** as compliance demand expands sign-language line items.

### SOM — Realistic 5-year Capture

| Year | Segment | Capture | Revenue |
|------|---------|---------|---------|
| Y1 | Education (ASL learners, K-12 pilot) | 5k paid individuals + 3 districts | ~$700k |
| Y2 | + EdTech / LMS partnerships | 10 enterprise contracts | ~$2.4M |
| Y3 | + Mid-market enterprise (training, HR) | 30 contracts | ~$6M |
| Y4 | + Government / public sector | 50 contracts | ~$12M |
| Y5 | + Creator economy (Patreon-tier indie publishers) | Mature mix | **~$18 – $25M ARR** |

**SOM = ~$15–25M ARR by Year 5 = ~3–4% of SAM.** That is well below Hand Talk's traction in Brazil and consistent with what a focused EdTech/accessibility startup can capture in 5 years with a $5–10M cumulative raise.

---

## 2.4 — Customer segments ranked by willingness-to-pay

| Segment | Pain | WTP | Notes |
|---------|------|-----|-------|
| **K-12 / college ASL programs** | Need engaging media; ASL is the 3rd most-studied language; word-level gloss is pedagogically *correct* for learners | **High** ($) | Easiest first market; institutional purchasing |
| **Higher-ed LMS / MOOC platforms** | NAD vs. Harvard/MIT precedent; massive video libraries; compliance ROI | **Very high** ($$$) | Slow sales cycle; long pilots |
| **Government & public-sector portals** | ADA Title II deadline; explicit mandate | **Very high** ($$$) | Procurement friction high |
| **Mid-market corporate training / HR** | EEOC, internal accessibility commitments | **Medium** ($$) | Crowded; need clear ROI vs. 3Play |
| **YouTube creators (long-tail)** | Audience growth, viewer loyalty | **Low** ($) | Won't pay unless free-tier or ad-funded |
| **Deaf-native primary consumers** | Genuine need but Deaf community is rightly skeptical of avatars/synthetic ASL | **Very low** unless co-designed | Critical for credibility, not for revenue |

The takeaway: **revenue comes from publishers and institutions, not from Deaf end-users.** This is the same economic structure as captioning today.

---

## 2.5 — Market timing assessment

**It is a good moment to start, but a difficult moment to be late.**

| Tailwind | Headwind |
|----------|----------|
| ADA Title II deadline (April 2026) creating procurement urgency | LLM costs falling — incumbents may build in-house |
| EAA enforcement (June 2025) opening EU market | Big platforms (YouTube, TikTok) may ship native ASL features |
| Generative AI making sign-synthesis cheaper to prototype | Deaf-community skepticism is rising in tandem with hype |
| Signapse, Hand Talk raising capital → validation | Captioning incumbents (3Play, Verbit) will likely acquire-or-build |

**Conclusion: the window is ~24 months to establish credibility and a defensible corpus.** After that, distribution will be dominated by incumbents or platform-native features.
