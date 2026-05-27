# GenASL — Business & Market Plan

> **Prepared:** May 2026 · **Last revised:** 2026-05-27
> **Subject:** GenASL — a retrieval-augmented, grammar-aware ASL avatar layer for online video
> **Audience:** Founders, investors, accessibility partners, grant reviewers

This folder is the **single, current business plan** for **GenASL**: a platform-agnostic
SDK + Chrome extension that renders a **3D ASL interpreter avatar** over online video.
The avatar is driven by a pipeline that listens to audio, analyses prosody and emotion,
decides a signing strategy with an LLM, and produces motion that is **anchored to
Deaf-signer recordings** retrieved at the *phrase* level — not stitched word-by-word,
and not freely hallucinated by a neural net.

It answers one question:

> **Is GenASL feasible, innovative, and business-viable as a production-grade ASL
> system — and what is the credible path from working prototype to sustainable venture?**

---

## What changed (and why this plan was rewritten)

Earlier versions of this folder carried **two competing theses**: a v1 plan built around
a *word-level WLASL prototype* sold to ASL learners, and a v2 feasibility study arguing
for a *sentence-level, platform-pays* product. The project has since **committed to a
single approach** and moved past both:

- **No word-level output.** Word-level gloss survives only as an *internal* representation;
  it is never shown to a user. The old clip-stitching learner product is retired.
- **The "middle" of ASL.** Grammar-aware, phrase-level, with non-manual markers (NMMs) —
  real ASL, which requires clean data, compute, and Deaf-community partnership. Not a
  toy, and not a pure-neural moonshot.
- **Retrieval is the default, not the fallback.** Every output segment's motion comes
  from a Deaf-signer recording. The default tier is a *continuous clip retrieved at phrase
  level* from a real corpus ([OpenASL](https://arxiv.org/pdf/2205.12870), 288 h, 200+
  signers), with [ASL Citizen](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-description/)
  (2,731 signs) as a lexical secondary. Per-gloss WLASL stitching is the last resort,
  always tagged `fidelity="stitched"`/`"degraded"`. Generative steps fill *only*
  transitions and NMM augmentation on top of the retrieved face.
- **Platforms pay; end users never do.** Free for Deaf-led organisations, always.
- **Market expansion, not substitution.** GenASL serves content that has *no* ASL today
  because human interpretation isn't economically viable for it. Human interpreters
  remain the gold standard; broader ambient ASL grows demand for their work.

This document is now **one plan**, with a deeper technical/feasibility appendix.

---

## How to read this plan

### The plan — six documents

| # | Document | What's inside |
|---|----------|---------------|
| 1 | [Executive Summary](01-executive-summary.md) | Verdict, the committed approach, headline numbers, key risks, the pitch |
| 2 | [Market Analysis](02-market-analysis.md) | DHH demographics, regulatory drivers (post-deadline-extension), TAM/SAM/SOM, induced demand |
| 3 | [Competitive Landscape](03-competitive-landscape.md) | Technical families + companies (Sorenson/Hand Talk, Signapse), white-space map |
| 4 | [Value Proposition & Product Strategy](04-value-proposition.md) | Who pays, jobs-to-be-done, why retrieval-augmented is defensible, roadmap |
| 5 | [Pricing, Unit Economics & Build Cost](05-pricing-and-business-model.md) | Platform-pays pricing, unit economics, capital required, revenue scenario |
| 6 | [Go-to-Market, Risk & Decision](06-go-to-market-and-risk.md) | Distribution, 24-month plan, fundraising, risk register, exits, go/no-go gates |

### The appendix — technical & feasibility depth

[`feasibility-study/`](feasibility-study/) holds the detailed technical and feasibility
analysis the plan references: the pipeline architecture and build cost
([F1](feasibility-study/01-technology-feasibility.md)), the five-family technical
comparison ([F2](feasibility-study/02-competitive-tech-comparison.md)), the induced-demand
model ([F3](feasibility-study/03-market-expansion.md)), the platform-pays vs. consumer-pays
analysis ([F4](feasibility-study/04-pricing-strategy-comparison.md)), and the feasibility
verdict ([F5](feasibility-study/05-feasibility-verdict.md)). The body above is the plan;
the appendix is the evidence.

---

## The 60-second take

**Feasible?** Yes — under conditions. The technology is application of recent SOTA plus
careful systems engineering plus a proprietary, Deaf-curated corpus. The bottleneck is
**clean data and community trust, not models or compute**. With ~$5.5M and 24 months a
focused team can ship a production-grade speech-to-ASL-avatar system that is materially
better than any shipped competitor for instructional/expository video.

**Innovative?** Yes — in *architecture*, not components. No productised system today
combines (a) retrieval anchoring to real Deaf-signer recordings, (b) a parallel
prosody→NMM generation channel, (c) a platform-agnostic browser SDK, and (d) a B2B-only
"platforms pay" model. Each exists alone; together they are unmatched.

**Business sense?** Conditionally yes. The paying customer is the **platform / publisher**
legally exposed under ADA Title II, the EU Accessibility Act, Section 508, and CVAA — not
the Deaf viewer. The compliance runway just moved *toward* us: the ADA Title II deadline
was extended to **April 2027/2028**, and the DOJ's own rule cites current AI's inability
to remediate accessibility at scale. That is a 24-month build window with a buyer whose
deadline is real and ahead.

**The new urgency:** **Sorenson** — the incumbent with the largest US Deaf customer base —
[acquired Hand Talk and OmniBridge in January 2025](https://sorenson.com/newsroom/sorenson-acquires-omnibridge-and-hand-talk-to-develop-automated-sign-language-translation-capabilities/)
and [unveiled AI sign-language avatar POCs in April 2026](https://sorenson.com/newsroom/sorenson-communications-unveils-ai-sign-language-translation-ast-proofs-of-concept/).
The white space is real but the window is closing. Speed, Deaf-community trust, and a
corpus you own are the only durable moats.

See [01-executive-summary.md](01-executive-summary.md) for the full verdict.

---

## Methodology & caveats

- Market figures are synthesised from public industry reports (Research Nester, Verified
  Market Reports, MRFR, Business Research Insights, GlobalGrowthInsights) and primary
  statistics from NIDCD, WHO, WFD, MLA, and US Census ACS data, refreshed May 2026.
  Where analysts disagree by an order of magnitude (they do, on captioning), we say so and
  use the *focused* figure.
- Competitor data is from public sources (company newsrooms, Crunchbase, PitchBook, Slator)
  as of May 2026. Private revenue figures are estimates where noted.
- Unit economics use conservative assumptions documented in
  [05-pricing-and-business-model.md](05-pricing-and-business-model.md).
- **This is a strategic analysis, not investment advice.** No paid go-to-market step
  proceeds before the Deaf-community co-design gate in
  [06-go-to-market-and-risk.md](06-go-to-market-and-risk.md) is met.
