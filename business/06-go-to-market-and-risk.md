# 6 — Go-to-Market, Risk & Decision

The operating plan: how the business gets built, who pays, what could break it, and the
explicit gates that decide whether to keep going.

---

## 6.1 — Distribution strategy

Platform-pays B2B is the motion. Three distribution surfaces compound rather than compete.

### Surface A — Platform direct (the revenue engine)

| | |
|---|---|
| **Reach** | ~500 mid-market platforms (EdTech, LMS, broadcasters, enterprise L&D) + ~50 strategic accounts |
| **Cost** | Founder-led sales for first 10; AE hire by year 2 |
| **Sales cycle** | 3–12 months |
| **Tactic** | Co-marketing with accessibility consultancies (Deque, Level Access, AudioEye); RFP-response templates targeting the 2027–28 Title II planning window; one strategic LOI before seed close |

### Surface B — Developer / SDK self-serve (PLG funnel)

| | |
|---|---|
| **Reach** | Any team with an HTML5 `<video>` player; long-tail platforms |
| **Cost** | Docs + free tier; developer-relations content |
| **Conversion** | Free 1,000 min/mo → Tier 1 paid → upsell to Tier 2 |
| **Tactic** | Public SDK, sample integrations (Brightcove, Kaltura, JW Player, Mux), accessibility-keyword SEO |

### Surface C — Chrome extension showcase (signal, not revenue)

| | |
|---|---|
| **Reach** | ~3.5B Chrome users; Deaf community + ASL educators + procurement evaluators |
| **Cost** | Listing free; ≤10% of engineering effort |
| **Tactic** | "Your competitor's site already loads ASL via our extension" demos for platform sales; Deaf-community feedback loop; partnerships with ASL creators (Bill Vicars, ASL Stew) |

### The flywheel

```
   Showcase extension demonstrates ASL on real platforms
              ↓
   Platform PM sees it on their own (or a competitor's) content
              ↓
   Platform integrates the SDK; pays per minute
              ↓
   Generated output + Deaf-rater feedback expands the corpus
              ↓
   Better corpus raises fidelity → easier next sale, more induced demand
              ↓ (back to top)
```

Every minute of generated output yields a *(text, motion, Deaf-rater feedback)* triple
that, with consent, improves the proprietary corpus — the compounding asset.

---

## 6.2 — 24-month operating plan (gated, mapped to pipeline phases)

### M0–M6 — Foundation & data (Phases 4–5) · ~$1.4M

- [ ] Recruit and pay 5-person Deaf advisory board; first non-founder hire is Deaf
- [ ] Index OpenASL + ASL Citizen for phrase-level retrieval (Phase 4)
- [ ] Stand up markerless capture with a studio/academic partner (Gallaudet/NTID); first proprietary session
- [ ] Motion synthesis + NMM channel (Phase 5); Avatar v1 demoable
- [ ] Publish "augmentation, not replacement" position statement
- [ ] Apply for SBIR Phase I, NIDILRR, Innovate-UK-style grants (~$200k non-dilutive)
- [ ] **Gate:** Deaf-rater panel intelligibility **≥ 3.5/5** → enter GTM

### M6–M12 — SDK + first contracts (Phases 6–7) · ~$1.4M

- [ ] Chrome extension (three.js + VRM, Phase 6); platform SDK + API (Phase 7)
- [ ] Compliance reporting v1 (WCAG 2.1 AA / EAA / Section 508 mapping)
- [ ] 2–3 friendly platform pilots; first paid contract (≥$25k ACV)
- [ ] Seed close (~$4–5M); ≥1 strategic platform LOI signed before close
- [ ] **Gate:** second Deaf-rater panel **≥ 3.8/5**; ≥3 pilots active

### M12–M18 — Production & polish · ~$1.4M

- [ ] Corpus expansion to 200 h+ proprietary, NMM-annotated, royalty-bearing
- [ ] Self-hosted appliance GA (Docker + Ollama + on-prem corpus)
- [ ] Avatar diversity via motion retargeting (4+ identities)
- [ ] 4+ Tier-2 contracts ($300k+ ARR); SOC 2 Type I
- [ ] **Gate:** reference-customer NPS ≥ 30; panel **≥ 4.0/5**

### M18–M24 — Scale · ~$1.3M

- [ ] SDK GA; integrations for Brightcove, Kaltura, JW Player, Mux
- [ ] 10+ paid platform contracts; ~$2M ARR run-rate
- [ ] First Tier-3 strategic in late-stage RFP; BSL/AUSLAN corpus pilot
- [ ] Series A close (~$15–25M)

---

## 6.3 — Fundraising path

| Round | Timing | Amount | Pre-money | Use of funds | Source |
|-------|--------|--------|-----------|-------------|--------|
| **Grants** | M0–6 | $200k | n/a | Validation + corpus | SBIR, NIDILRR, Innovate UK, Ford Foundation accessibility line |
| **Seed** | M9–12 | $4–5M | $12–20M | Data, model, SDK, Deaf-first team | Mission-aligned VC (accessibility/AI-for-good), EdTech vertical, accessibility angels |
| **Series A** | M24–30 | $15–25M | $80–120M | International (BSL/AUSLAN), domain corpora, GTM scale | EdTech/AI growth VC; possible strategic from a captioning/VRS ecosystem |

A $1M pre-seed with consumer-revenue-bridge ambitions is the **wrong shape** for this
product — the build needs the larger round on the larger thesis. Either raise it, or run
the research/open-source fallback where smaller capital fits.

---

## 6.4 — Hiring sequence (first 10)

1. **Deaf community manager** (paid advisory → permanent by M12) — the keystone hire
2. ML researcher (sign-language + motion retrieval)
3. ML/inference engineer (production pipeline)
4. Senior WebGPU / frontend engineer (extension + SDK)
5. Backend / SDK engineer
6. ASL linguistics consultant (part-time; corpus + QA)
7. Product designer (accessibility specialist)
8. Account executive (platform sales)
9. Customer success manager
10. Compliance / security lead (SOC 2)

A Deaf hire in the **first** slot — not as a token, as the keystone that makes every later
hire's work credible.

---

## 6.5 — Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|:--:|:--:|-----------|
| R1 | **Deaf-community rejection** of framing | High | Catastrophic | Pre-Phase-1 advisory; "augmentation, not replacement"; compensated contributors; quarterly Deaf-rater panel |
| R2 | **Incumbent (Sorenson) out-distributes** | **Medium-High** (now live) | High | Move first; 3+ platform logos by M18; differentiate on Deaf-trust + auditable corpus + media-overlay niche; acquisition is a valid outcome |
| R3 | **Platform ships native ASL** (YouTube/Netflix) | Low-Medium | Catastrophic to showcase; minor to B2B | EdTech/gov/enterprise revenue is platform-independent; pivot 100% to SDK/white-label |
| R4 | **Clean-corpus build slips** (data is the critical path) | Medium | High | Bootstrap on public sets (OpenASL/ASL Citizen); markerless capture; phrase-level retrieval degrades gracefully (tagged fidelity) |
| R5 | **Pure-neural overtakes the corpus moat** | Medium | High | Accelerate productisation; lean on Deaf-trust + integration lock-in, which a better model doesn't erase |
| R6 | **Long-tail / classifier-heavy coverage gaps** | Certain (bounded) | Medium | Domain capture in later phases; honest scope disclosure; never claim narrative/poetic ASL |
| R7 | **ADA litigation against GenASL's own output** | Low | High | Crisp disclaimers; "augmentation" positioning; never market as "ADA-compliant interpretation" |
| R8 | **LLM cost / API risk** | Low | Medium | Multi-provider; Ollama self-host path already in the codebase |
| R9 | **Corpus licensing / provenance ambiguity** | Medium | High | Legal review by M3; consented proprietary capture for the commercial tier |
| R10 | **Slow public-sector procurement** | High | Medium | EdTech + private-platform revenue covers burn while gov RFPs mature toward 2027–28 |

---

## 6.6 — The conditions that must hold (decision gates)

These are sequential; a failure at any prior condition invalidates the next. Full rationale
in [F5](feasibility-study/05-feasibility-verdict.md).

**Condition 1 — Deaf partnership is real, not performative.** Paid advisory board + signed
agreements by M3; first non-founder hire Deaf by M4; public position statement with NAD-class
endorsement; contributors compensated; first Deaf-rater panel by M8. *If any fail: restructure
as research/open-source, not a venture.*

**Condition 2 — Seed, not bridge.** ~$4–5M raised by M12; ≥1 platform LOI before close; ≥1
academic/Deaf-institution data MoU (Gallaudet/BU/NTID).

**Condition 3 — Milestones gated by trust, not engineering.** Closed beta only at panel
≥3.5/5; public beta at ≥3 paid pilots + panel ≥3.8/5; GA at SOC 2 Type I + ≥10 contracts +
panel ≥4.0/5.

**Condition 4 — Platform-pays is the primary motion.** First paid platform by M12; 4+ Tier-2
by M18; Tier-3 pipeline by M24; consumer surfaces ≤10% of engineering effort. *If platform
sales don't land by M18, pivot to a focused-vertical service business or the fallback.*

---

## 6.7 — Strategic exit options

| Exit | Timing | Acquirer profile | Likely range |
|------|--------|------------------|--------------|
| **Captioning incumbent** | Y3–5 | 3Play, Verbit, AI Media | 4–8× ARR; $20–80M |
| **Sign-language / VRS incumbent** | Y3–5 | **Sorenson**, accessibility platforms | 5–8× ARR; $40–200M |
| **Accessibility platform** | Y4–6 | AudioEye, Level Access, Deque | 5–10× ARR; $40–120M |
| **Independent growth** | Y5+ | n/a | $20M+ ARR profitable specialty SaaS |

This is **not** a winner-take-all market and **not a unicorn**. A realistic best case is a
**$200–500M outcome at Y5–7**, most plausibly via acquisition by Sorenson or a captioning
incumbent that wants the corpus + Deaf-community standing it can't build internally. A
profitable $30M-ARR independent is also a perfectly good landing state.

---

## 6.8 — The decision call

| Lens | Verdict |
|------|---------|
| **Feasibility** | ✅ Buildable in 24 months at ~$5.5M; Phases 1–3 shipped; corpus reproducible from public sets + capture |
| **Innovation** | ✅ The *combination* — retrieval-anchored + parallel-NMM + SDK + platform-pays + Deaf-sourced data — is unmatched |
| **Market exists** | ✅ Regulated demand real and growing (extended Title II, live EAA); sign-language tech 8–20% CAGR |
| **Market grows** | ✅ Tool induces ~3× market expansion by 2035 |
| **Business case** | ⚠️ Conditional — platform-pays works at ~$22M Y5 ARR, but needs a real seed and depends on Tier-2/3 landing |
| **Ethics & community fit** | ⚠️ Conditional — collapses without Deaf-first co-design |
| **Incumbent timing** | ⚠️ Window narrowed — Sorenson is moving; ~24 months to plant the flag |

**Recommended posture: Proceed to a 6-month Phase-1 gate.** If by M6 the team has (a) a paid
Deaf advisory board, (b) a working retrieval + NMM demo rated ≥3.5/5 by a Deaf panel, (c) ≥1
platform pilot or strategic LOI, and (d) a public position statement, then raise the seed
and continue. **If any of the four is missing, pause monetisation and reorganise as a
research / open-source contribution to the field.**

That gate matters more than any chart in this plan.
