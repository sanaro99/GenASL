# 6 — Go-to-Market & Risk

This final section is the operating plan: how the business actually gets built, who pays for it, and what could break it.

---

## 6.1 — Distribution strategy

GenASL has the rare advantage of **three viable distribution surfaces** that compound rather than compete.

### Surface A — Chrome Web Store (consumer learner GTM)

| | |
|---|---|
| **Reach** | ~3.5B Chrome users globally |
| **Cost** | Listing free; ASO via accessibility keywords; mid-funnel content marketing |
| **Conversion** | Freemium → Pro at ~3% target; ARPU $72/yr |
| **Tactic** | Partnerships with ASL YouTube creators (Bill Vicars, ASL Stew, Sign Duo) for organic reviews |

### Surface B — Education channel (district sales)

| | |
|---|---|
| **Reach** | ~17,000 US school districts; ~700 with ASL programs |
| **Cost** | One inside-sales rep; conference presence (ACTFL, ASL Teachers Association) |
| **Sales cycle** | 3–6 months |
| **Tactic** | Free 1-year pilot for first 25 districts; case-study-led inbound thereafter |

### Surface C — Enterprise direct (compliance buyers)

| | |
|---|---|
| **Reach** | ~500 mid-market enterprises with significant video libraries + compliance pressure |
| **Cost** | Founder-led sales for first 10; AE hire by year 2 |
| **Sales cycle** | 6–12 months |
| **Tactic** | Co-marketing with accessibility consultancies (Deque, Level Access, Karl Groves); RFP-response template targeting ADA Title II procurement |

### A flywheel between the three

```
   Consumer learners use it on YouTube
              ↓
   ASL teachers see students using it
              ↓
   Teachers ask districts to license it
              ↓
   District deployment generates compliance reports
              ↓
   Compliance reports become enterprise procurement evidence
              ↓
   Enterprise deployment generates revenue + corpus expansion
              ↓
   Better corpus improves consumer experience  ←──── back to top
```

This flywheel is the strategic centerpiece. Each surface feeds the next; the consumer free tier is the corpus + brand engine, not a revenue engine.

---

## 6.2 — 24-month operating plan

### Quarters 1–2 — Foundation (target spend: ~$200k)

- [ ] Recruit and pay 5-person Deaf advisory board
- [ ] Replace `youtube-transcript-api` with official Data API caption endpoints + user-upload fallback
- [ ] Ship "Practice Mode" UX in Chrome extension
- [ ] Launch on Chrome Web Store with freemium tier
- [ ] Recruit 3 pilot school districts (free, 1-year, feedback contract)
- [ ] Apply for SBIR Phase I, NIDILRR, and Innovate-UK-style grants (~$200k non-dilutive potential)

### Quarters 3–4 — Education revenue (target spend: ~$400k)

- [ ] Education tier live ($4/seat/yr) with Google Admin + GPO managed deploy
- [ ] Canvas + Brightspace add-ons published
- [ ] Corpus expansion: 2,000 → 4,000 glosses with NMMs (paid Deaf signers)
- [ ] First $250k ARR
- [ ] Pre-seed close (~$1M at $5–8M post)

### Quarters 5–6 — Enterprise pilot (target spend: ~$600k)

- [ ] Browser SDK released (any HTML5 video player)
- [ ] First 3 paid enterprise contracts ($60k ACV avg)
- [ ] Coverage-report PDF + WCAG mapping live
- [ ] Hire: 1 AE, 1 ML engineer, 1 Deaf community manager
- [ ] $1M ARR mark

### Quarters 7–8 — Compliance flagship (target spend: ~$800k)

- [ ] Self-hosted appliance GA (Docker + Ollama + on-prem corpus)
- [ ] First public-sector contract (state government or federal agency)
- [ ] SOC 2 Type I in progress
- [ ] Sentence-level synthesis pilot with academic partner
- [ ] $2.5M ARR mark
- [ ] Seed extension or Series A prep (~$8–15M)

---

## 6.3 — Fundraising path

| Round | Timing | Amount | Pre-money | Use of funds | Source |
|-------|--------|--------|-----------|-------------|--------|
| **Grants** | Months 0–6 | $200k | n/a | Validation + corpus | SBIR, NIDILRR, Innovate UK, Ford Foundation accessibility line |
| **Pre-seed** | Month 9 | $1.0M | $5–8M | Education channel + 1 AE | Mission-aligned VC (Empirical, AI for Good fund), accessibility angels |
| **Seed** | Month 18 | $4–6M | $20–30M | Enterprise sales, SDK, SOC 2 | Generalist seed VC + EdTech vertical fund |
| **Series A** | Month 24–30 | $15–20M | $80–120M | International expansion, sentence-level R&D | EdTech-focused growth VC; possible strategic from 3Play / Verbit ecosystem |

Total dilution to Series A: ~35–40%. Tight for an accessibility-tech company but possible because gross margins are SaaS-grade.

---

## 6.4 — Hiring sequence (first 10 hires)

1. Deaf community manager (paid advisory board → permanent hire by month 12)
2. ASL curriculum specialist (part-time, content + corpus)
3. ML engineer (translation pipeline + sentence-level R&D)
4. Senior frontend engineer (extension + SDK)
5. Account executive (education + enterprise)
6. Product designer (accessibility-specialist)
7. Customer success manager
8. DevRel / partnerships (LMS integrations)
9. Compliance / security lead (SOC 2)
10. ML researcher (sentence-level ASL synthesis)

Notably: a Deaf hire in the *first* slot. Not as token; as the keystone that makes every later hire's work credible.

---

## 6.5 — Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|:--:|:--:|-----------|
| R1 | **Deaf-community rejection** of the product framing | High | Catastrophic | Pre-Phase-1 advisory; explicit "augmentation, not replacement" positioning; compensated corpus contributors |
| R2 | **YouTube ToS change or transcript API removal** | Medium | High | Replace with official Data API + caption-upload + multi-platform SDK by month 12 |
| R3 | **WLASL coverage ceiling** (gloss vocab ~2k) | Certain | Medium | Paid corpus expansion plan; learner-mode is more forgiving of coverage gaps |
| R4 | **Incumbents (3Play, Verbit) ship ASL** | Medium | High | Move first; secure 3+ enterprise reference logos by month 18; consider being acquired-by rather than competing-with |
| R5 | **Platforms ship native ASL** (YouTube, TikTok) | Low-Medium | Catastrophic to consumer tier; minor to enterprise | Education + enterprise revenue is platform-independent |
| R6 | **LLM cost or API risk** | Low | Medium | Multi-provider; Ollama self-host path already in place; tested fallback chain |
| R7 | **ADA litigation against GenASL itself** for inaccessible output | Low | High | Crisp disclaimers; positioning as augmentation; do not market as "ADA-compliant ASL interpretation" |
| R8 | **Founder/team accessibility-domain inexperience** | Medium | Medium | Deaf advisory + Deaf community manager hire |
| R9 | **WLASL licensing / data provenance ambiguity** | Medium | High | Legal review of corpus by month 3; transition to internally-recorded clips for commercial tier |
| R10 | **Slow public-sector procurement** | High | Medium | Education + private enterprise revenue covers cash burn |

---

## 6.6 — Strategic exit options

A founder should know all three before raising.

| Exit | Timing | Acquirer profile | Likely range |
|------|--------|------------------|--------------|
| **Acquired by captioning incumbent** | Year 3–5 | 3Play, Verbit, AI Media | 4–8× ARR; $20–80M |
| **Acquired by accessibility platform** | Year 4–6 | Deque, Level Access, AudioEye | 5–10× ARR; $40–120M |
| **Acquired by EdTech platform** | Year 3–5 | Canvas (Instructure), Duolingo, Coursera | Education revenue × multiplier; $30–80M |
| **Continued independent growth** | Year 5+ | n/a | $20M+ ARR profitable specialty SaaS |

The market is **not** a winner-take-all market. A focused profitable $30M ARR specialty SaaS is a perfectly good landing state — and is materially more achievable than chasing a $1B unicorn outcome.

---

## 6.7 — The decision call

**Is this project feasible, innovative, and business-viable?**

| Lens | Verdict |
|------|---------|
| **Feasibility** | ✅ Technical path is clear; codebase is real; corpus is reproducible |
| **Innovation** | ✅ Browser overlay + retrieval-augmented architecture is genuinely novel in this space |
| **Market exists** | ✅ Regulated demand is real, large, and growing — captioning is $2.5B+ at 15% CAGR; ASL is the next add-on |
| **Business case** | ⚠️ Conditionally. Consumer alone won't fund it; B2B education and enterprise compliance are the actual business. |
| **Ethics & community fit** | ⚠️ Requires Deaf-first co-design or the entire thesis collapses |
| **Founder fit** | ❓ Cannot assess from this analysis; the team must honestly answer whether they want to spend the next 5 years inside an accessibility-tech company, not just a generative-AI demo. |

**Recommended posture:** Proceed to a 6-month "Phase 1" milestone gate. If by month 6 the team has (a) a paid Deaf advisory board operational, (b) ≥1,000 active Chrome extension users, (c) ≥1 signed school pilot, and (d) a public Deaf-community position statement, then continue and raise pre-seed. If any of those four are missing, the right move is to pause monetization and reorganize the project as a research / open-source contribution to the field rather than a venture-backed startup.

That gate is more important than any market chart in this document.
