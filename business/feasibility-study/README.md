# GenASL — Technical & Feasibility Appendix

> **Prepared:** May 2026 · **Last revised:** 2026-05-27
> **Role:** Supporting evidence for the [business plan](../README.md). The six numbered
> docs in `business/` are the plan; this folder is the depth behind it.

This appendix backs the plan's claims with technical and feasibility detail that doesn't
belong in a business-plan body: the pipeline architecture and build cost, the five-family
technical comparison, the induced-demand model, the platform-pays analysis, and the
go/no-go verdict.

> **Note on history.** Earlier, this folder was a "v2 feasibility study" arguing *against*
> a separate "v1" word-level-learner plan. That split is gone. The project committed to a
> single approach — **retrieval-augmented, grammar-aware, phrase-level, platform-pays** —
> and the business plan was rewritten around it. References below to "the old word-level
> PoC" mean the retired prototype, not a live alternative.

| Document | Question it answers |
|----------|---------------------|
| [F1 — Technology Feasibility](01-technology-feasibility.md) | *Can the audio→3D-avatar pipeline be built? Cost, timeline, risk? What's already shipped?* |
| [F2 — Competitive Tech Landscape](02-competitive-tech-comparison.md) | *What approaches exist, how do they compare, where is the white space?* |
| [F3 — Market Expansion & Induced Demand](03-market-expansion.md) | *Does the tool **grow** the ASL market, or just compete for the existing slice?* |
| [F4 — Pricing: Platform-Pays vs Consumer-Pays](04-pricing-strategy-comparison.md) | *Which model wins, and why platform-pays?* |
| [F5 — Feasibility Verdict](05-feasibility-verdict.md) | *Synthesis. Build? Under what conditions?* |

---

## The thesis in one paragraph

A production GenASL is a **multimodal system** that ingests speech, semantically chunks it
on prosody and clause boundaries, translates to an ASL *plan* with a grammar-aware LLM
(gloss is an *internal* representation, never user-facing), and drives a rigged VRM avatar
whose motion is **anchored to Deaf-signer recordings retrieved at the phrase level**, with
generative steps filling *only* transitions and a parallel prosody→NMM channel. The result
is an **embeddable, platform-agnostic ASL track** — a JS SDK any video player includes,
delivered under a B2B per-minute agreement. **End users never pay.**

This is technically feasible today. **Phases 1–3 of the pipeline (audio backbone +
interpreter brain) are shipped.** The 18–24-month critical path is **clean data + Deaf
community**, not models or compute.
