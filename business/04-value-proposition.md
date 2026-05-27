# 4 — Value Proposition & Product Strategy

This section answers two questions:

1. **What does GenASL promise — to whom, in language they recognise?**
2. **What does the product become, over 24 months, to deliver on that promise?**

---

## 4.1 — The honest value proposition

Accessibility-AI marketing overclaims. GenASL does the opposite. Here is the *credible*
claim, phrased per buyer — and note that **the Deaf viewer is never a buyer.**

### For EdTech / LMS / MOOC platforms (primary B2B)

> **"An embeddable ASL track for your video library — no re-uploads, no human bottleneck."**
> Drop our SDK into your player; we render an ASL avatar in your learners' first language,
> anchored to real Deaf-signer recordings. Coverage and fidelity are reported per video for
> Section 508 and procurement. One integration reaches every learner you have.

### For government & public-sector portals (primary B2B)

> **"Make the Title II planning window count."**
> The deadline moved to 2027–2028 and the DOJ itself flagged that current AI can't
> remediate at scale. We are the ASL line item you can adopt now, with audit-grade
> coverage reports mapped to WCAG 2.1 AA, and a self-hosted option for data-residency rules.

### For streaming / media platforms (B2B)

> **"ASL parity, before your competitor ships it."**
> The EAA names sign-language interpretation for audiovisual media. We give you a
> platform-agnostic ASL overlay with per-minute pricing your accessibility budget already
> understands — and an avatar your viewers won't reject, because it's built *with* the
> Deaf community, not at it.

### For the Deaf community (non-monetary, non-negotiable)

> **"Augmentation, not replacement — and you are never billed for access."**
> GenASL puts an ASL track on the long tail of content that has *none* today, because no
> human interpreter is economically viable for it. Human interpretation remains the gold
> standard for live, high-stakes, nuanced settings. Corpus contributors are paid, with
> royalties. Deaf-led organisations use it free, forever.

---

## 4.2 — Jobs-to-be-done

| Buyer | Functional job | Emotional job | Social job |
|-------|----------------|---------------|------------|
| EdTech accessibility lead | "Cover the ASL line item across my whole library" | De-risk the legal review | Win the procurement narrative |
| Government webmaster | "Be ready for the 2027 Title II deadline" | Avoid being the headline | Show measurable progress |
| Media platform PM | "Match EAA expectations and competitor parity" | Confidence it won't be rejected by Deaf users | Be seen as genuinely inclusive |
| Enterprise L&D lead | "Make training accessible without per-video human cost" | Predictable budget | Brand as an inclusive employer |
| Deaf viewer (beneficiary, not buyer) | "Watch the content hearing people watch, in ASL" | Belonging, not afterthought | Participate in the same culture |

---

## 4.3 — Why retrieval-augmented is the defensible product (not word clips, not pure neural)

The product wedge *is* the architecture. Three properties make it sellable where the
alternatives aren't:

1. **Buyers buy paperwork.** A compliance officer challenged by a Deaf advocacy group needs
   a defensible artifact. *"Every segment is anchored to a Deaf-signer recording; the model
   only interpolates timing and NMMs"* is defensible. *"A neural net generated it"* is not.
2. **Failure modes are bounded.** A retrieval miss is a momentary gap or a slightly
   off-context sign (tagged `fidelity="stitched"`). A generative failure is an *uncanny*
   output — a six-fingered hand, a dead face — which is reputationally catastrophic with the
   Deaf community and is exactly the critique levelled at pure-neural avatars.
3. **Corpus expansion has linear, ownable payoff.** Each capture session directly improves
   coverage and *is owned*. Neural-only systems need orders of magnitude more data per
   quality jump and can be reverse-engineered from public sets.

This is **motion-RAG** — the same insight (retrieval beats free generation for
high-stakes, auditable output) that made RAG win in document QA. Detail in
[F1 §1.5](feasibility-study/01-technology-feasibility.md).

---

## 4.4 — Product roadmap (mapped to the actual pipeline phases)

The codebase has shipped **Phases 1–3** (audio backbone + interpreter brain). The business
roadmap is the remaining phases plus the data and trust work that gates them.

### M0–M6 — Foundation & data (Phases 4–5 begin)

| Workstream | Deliverable | Why |
|-----------|-------------|-----|
| **Deaf community advisory** | 5-person paid board; first non-founder hire is Deaf | The gate everything depends on |
| **Corpus v1** | OpenASL + ASL Citizen indexed for phrase-level retrieval; first proprietary capture session | Phase 4 (retrieval) lands |
| **Motion synthesis** | Retrieval-driven motion + NMM channel from prosody | Phase 5 lands |
| **Closed demo** | Avatar v1 (VRM, single identity, basic NMMs) on instructional clips | Demoable for design partners |
| **Gate** | Deaf-rater panel intelligibility **≥ 3.5/5** | No paid GTM before this |

### M6–M12 — SDK + first contracts (Phases 6–7)

| Workstream | Deliverable |
|-----------|-------------|
| **Chrome extension** | Three.js + VRM overlay (Phase 6) — the showcase surface |
| **Platform SDK + API** | Embeddable on any HTML5 `<video>` (Phase 7); adaptive sync (pause/seek/speed) |
| **Compliance reporting v1** | Per-video coverage PDF mapped to WCAG 2.1 AA / EAA / Section 508 |
| **First pilots** | 2–3 friendly platforms (an EdTech LMS, a public-broadcaster property) |
| **Gate** | Second Deaf-rater panel **≥ 3.8/5**; ≥3 paid pilots active |

### M12–M18 — Production & polish

| Workstream | Deliverable |
|-----------|-------------|
| **Corpus expansion** | 200 h+ proprietary, NMM-annotated, royalty-bearing |
| **Avatar diversity** | 4+ identity options via motion retargeting (not re-capture) |
| **Self-hosted appliance** | Docker + on-prem LLM (Ollama) + on-prem corpus for regulated buyers |
| **Generative in-between** | Constrained transition synthesis for non-retrieval gaps only |
| **Gate** | SOC 2 Type I; reference-customer NPS ≥ 30 |

### M18–M24 — Scale

| Workstream | Deliverable |
|-----------|-------------|
| **SDK GA** | Integrations for Brightcove, Kaltura, JW Player, Mux |
| **10+ paid platform contracts** | ~$2M ARR run-rate |
| **BSL / AUSLAN** | Reuse the architecture on new-language corpora |
| **Series A readiness** | $15–25M raise on the corpus + integration moat |

---

## 4.5 — The non-negotiable: Deaf-community co-design

The strategy collapses if this is skipped, so it is stated explicitly.

**Before any paid GTM step:**

1. Hire (paid) Deaf advisors — NAD, NBDA, Gallaudet, NTID, ASLized are the channels.
2. Publish a position statement: *"GenASL is an ASL augmentation layer for content that
   otherwise has none. It does not replace interpreters, captions, or human-produced ASL
   for live, high-stakes, or nuanced settings."*
3. Compensate every corpus contributor (per-clip fee + royalty if commercialised).
4. Refuse contracts that frame GenASL as *replacing* interpreters — even at premium pricing.
   This is the single biggest reputation risk in the space.

History is unambiguous: products without Deaf endorsement (BBC avatar trials, the
discontinued Bonn airport signing avatar) draw concentrated public criticism that crushes
B2B sales cycles. Sorenson's avatar POC already
[drew expert concern](https://sorenson.com/newsroom/sorenson-communications-unveils-ai-sign-language-translation-ast-proofs-of-concept/);
GenASL's answer to that is structural, not cosmetic.

---

## 4.6 — The "why now" answer

> "The compliance runway just moved *toward* us — ADA Title II is now a 2027–2028 planning
> window, and the DOJ itself said current AI can't remediate accessibility at scale. The
> EAA is live and names sign language. The data exists (OpenASL, ASL Citizen) to bootstrap
> a retrieval corpus, and Phases 1–3 of the pipeline are shipped. And the incumbent
> (Sorenson) just signalled the market is real by acquiring its way in. The window to plant
> a Deaf-trust-and-corpus flag is ~24 months. After that, distribution belongs to whoever
> got there first."
