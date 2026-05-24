# GenASL — Feasibility Study (v2)

> **Prepared:** May 2026
> **Scope:** A *production* GenASL — not the current word-level prototype.
> **Premise (set by founders, not analysts):**
> - **No word-level ASL.** Sentence-level, grammar-aware, with non-manual markers.
> - **Platform-agnostic** from day one. Not tied to YouTube.
> - **Platforms pay, not end users.** Compare against consumer-pays as a sanity check.
> - **Architecture under evaluation:** audio → smart chunking → guided AI model → **3D avatar**, weighted toward determinism.

This study answers four questions in order:

| Document | Question it answers |
|----------|---------------------|
| [01 — Technology Feasibility](01-technology-feasibility.md) | *Can the proposed audio→3D avatar pipeline be built? What does it cost, how long, what's the risk?* |
| [02 — Competitive Tech Landscape](02-competitive-tech-comparison.md) | *What approaches exist today, and how does each one's efficiency compare? Where is the white space?* |
| [03 — Market Expansion & Induced Demand](03-market-expansion.md) | *Does a tool like this **grow** the ASL market, or just compete for the existing slice?* |
| [04 — Pricing: Platform-Pays vs Consumer-Pays](04-pricing-strategy-comparison.md) | *Which model wins? What does each look like in revenue, leverage, and risk?* |
| [05 — Feasibility Verdict](05-feasibility-verdict.md) | *Synthesis. Build? Don't build? Under what conditions?* |

---

## The new thesis in one paragraph

A production GenASL is a **multimodal generative system** that ingests speech, semantically chunks it on prosody and clause boundaries, translates to ASL with a grammar-aware neural model (gloss is an *internal* representation, never a user-facing surface), and drives a rigged 3D avatar with both manual signs (retrieved from a Deaf-signer motion library) and non-manual markers (generated from prosodic features). The result is an **embeddable, platform-agnostic ASL track** — a JavaScript SDK any video player can include, delivered to the platform under a B2B per-minute commercial agreement. End users never pay.

This is technically feasible today. The 18-month critical path is **dataset + community**, not models or compute.

---

## What changed from v1

The original analysis ([../README.md](../README.md)) treated word-level WLASL as the product wedge. This study explicitly rejects that and re-evaluates feasibility for the higher target. Key shifts:

| | v1 (prototype-as-product) | v2 (proper product, this study) |
|---|---|---|
| Target ASL fidelity | Word-level gloss | Sentence-level, grammar + NMMs |
| Distribution | Chrome extension on YouTube | Platform-agnostic SDK + extension |
| Who pays | Consumer (Pro), school | Platform / publisher (per-minute B2B) |
| Defensible asset | Curated WLASL bundle | Proprietary 200–500h ASL motion corpus with NMMs |
| 3-year ARR ceiling | ~$4M (mixed B2C+B2B) | **~$8–15M** (platform-only, fewer logos, larger ACV) |
| Capital required | Pre-seed $1M → seed $4–6M | **Seed $4M → Series A $15–25M** |
| Time to defensibility | 12 mo | **18–24 mo** |
| Cultural-acceptability risk | High | Lower (Deaf-led co-design budgeted from day 0) |

The v1 documents remain useful as the **B2C learner option**; they are not deleted. They represent a fallback strategy if the platform B2B motion fails to land. The feasibility study below is the recommended primary path.
