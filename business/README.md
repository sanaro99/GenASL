# GenASL — Business & Market Analysis

> **Prepared:** May 2026
> **Subject:** GenASL — AI-powered Generative ASL overlay for online video
> **Audience:** Founders, investors, accessibility partners, grant reviewers

This folder contains a complete market and business analysis for the **GenASL** project: a Chrome extension + backend that generates American Sign Language (ASL) video overlays for YouTube content using an LLM-driven English→gloss translator and a curated WLASL clip library.

The goal of this analysis is to answer one question:

> **Is GenASL a feasible, innovative, business-viable product — and what is the most credible path from proof-of-concept to a sustainable venture?**

---

## How to read this analysis

This folder contains **two related but distinct documents**:

### 📘 The original market analysis (v1) — six documents

Treats GenASL as it exists today (word-level WLASL prototype) and asks how to turn it into a business under that constraint.

| # | Document | What's inside |
|---|----------|---------------|
| 1 | [Executive Summary](01-executive-summary.md) | Verdict, headline numbers, key risks, one-page pitch |
| 2 | [Market Analysis](02-market-analysis.md) | DHH demographics, regulatory drivers, accessibility tech market sizing (TAM/SAM/SOM) |
| 3 | [Competitive Landscape](03-competitive-landscape.md) | Signapse, Hand Talk, SignAll, Sorenson, captioning incumbents, positioning map |
| 4 | [Value Proposition & Product Strategy](04-value-proposition.md) | Who we serve, jobs-to-be-done, product wedge, roadmap to a real product |
| 5 | [Pricing & Business Model](05-pricing-and-business-model.md) | Three-tier pricing, unit economics, revenue scenarios |
| 6 | [Go-to-Market & Risk](06-go-to-market-and-risk.md) | Distribution, 24-month plan, fundraising path, risk register |

### 📗 The feasibility study (v2) — five documents — **recommended primary read**

Asks the harder question: *if we drop the word-level constraint and build the right product (sentence-level, NMMs, platform-agnostic, platform-pays), is it feasible?* Includes a full technology design for the proposed audio→3D-avatar pipeline.

| # | Document | What's inside |
|---|----------|---------------|
| F0 | [Feasibility Study README](feasibility-study/README.md) | New thesis + what changed from v1 |
| F1 | [Technology Feasibility](feasibility-study/01-technology-feasibility.md) | Proposed audio→3D-avatar architecture; build cost; 24-month timeline |
| F2 | [Competitive Tech Comparison](feasibility-study/02-competitive-tech-comparison.md) | 5 technical families compared; efficiency tables; white-space map |
| F3 | [Market Expansion & Induced Demand](feasibility-study/03-market-expansion.md) | Does this tool *grow* the ASL market? Quantified |
| F4 | [Pricing: Platform-Pays vs Consumer-Pays](feasibility-study/04-pricing-strategy-comparison.md) | Side-by-side comparison; recommended commercial model |
| F5 | [Feasibility Verdict](feasibility-study/05-feasibility-verdict.md) | Go/no-go conditions; decision card |

---

## The 60-second take

**Feasible?** Yes, but only with a sharp narrowing of scope. The current word-level WLASL pipeline is not a product Deaf-native users will accept as "ASL." It *is* a viable wedge for **enterprise accessibility augmentation** (an extra layer on top of captions) and **K-12/early-learner ASL education**, where word-level gloss is pedagogically acceptable.

**Innovative?** Yes — three things make the project distinctive:
1. **Generative + retrieval hybrid** (LLM gloss + clip library) rather than pure neural synthesis; cheaper to run and easier to QA.
2. **Browser-side overlay** on existing video, not a separate destination — this is the only credible distribution model for an accessibility layer.
3. **Open architecture** (Ollama-compatible) lets enterprises self-host, which directly addresses the data-residency objection that has stalled enterprise adoption of accessibility AI.

**Business sense?** Conditionally yes. The consumer market alone will not sustain it — the *paying* customer is the **content publisher, LMS, or government portal** legally obligated under ADA, Section 508, CVAA, and the EU Accessibility Act. The market is real (closed-captioning alone is a $2.5B+ market growing 15% CAGR), but GenASL must compete by being *additive*, not by replacing captions.

See [01-executive-summary.md](01-executive-summary.md) for the full verdict and the recommended 24-month path.

---

## Methodology & caveats

- Market figures are synthesized from public industry reports (3Play Media, Verified Market Reports, Data Insights Market, GlobalGrowthInsights) and primary statistics from NIDCD, WHO, WFD, and US Census ACS data.
- Competitor data is from public sources (Crunchbase, PitchBook, company websites) as of May 2026. Private revenue figures are estimates where noted.
- Unit economics use conservative assumptions documented in [05-pricing-and-business-model.md](05-pricing-and-business-model.md).
- **This is a strategic analysis, not investment advice.** Before any go-to-market step, the product must be validated with the Deaf community — see the explicit gate in [04-value-proposition.md](04-value-proposition.md).
