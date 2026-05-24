# 4 — Value Proposition & Product Strategy

This section answers two questions:

1. **What exactly does GenASL promise — to whom, in language they recognize?**
2. **What does the product become, in 24 months, to deliver on that promise?**

---

## 4.1 — The honest value proposition

Most accessibility AI marketing overclaims. GenASL must do the opposite. Here is the *credible* value claim — phrased differently for each buyer.

### For ASL learners (B2C)

> **"Practice ASL on the videos you already watch."**
> Pause any YouTube video and see word-level ASL signs overlaid in time with the spoken English. It's not a substitute for a teacher — it's a millions-of-hours-richer-than-Duolingo flashcard built into every educational video on the internet.

### For school districts and ASL programs (B2B education)

> **"A free CALL (Computer-Assisted Language Learning) tool for ASL classrooms."**
> Word-level gloss matches how ASL I/II curricula already teach. Students get sign exposure on TED-Ed, Crash Course, Khan Academy, and any teacher-assigned YouTube video. Schools get usage analytics and a centrally-managed extension deployment.

### For LMS / EdTech / corporate L&D (B2B mid-market)

> **"An ASL augmentation layer for your existing video library — without re-uploading."**
> Plug our SDK into your video player; we generate aligned ASL clips on the fly. Compliance reports document coverage. Self-hosted option available for data-residency-sensitive buyers.

### For Deaf-community partners (non-monetary)

> **"A pre-production tool, not a replacement for human interpretation."**
> GenASL produces *gloss-level scaffolding* a Deaf editor can refine into a polished sign-language track. The product is built *with* Deaf collaborators and pays them for the corpus.

---

## 4.2 — Jobs-to-be-done

| Buyer | Functional job | Emotional job | Social job |
|-------|----------------|---------------|------------|
| ASL learner | "Help me practice on real content, not flashcards" | Feel like progress is happening | Identify as a serious learner |
| ASL teacher | "Give my students homework on authentic media" | Confidence the tool reinforces what I teach | Be seen as innovative |
| EdTech accessibility lead | "Cover ASL line item in WCAG compliance plan" | De-risk the legal review | Win the procurement narrative |
| Government webmaster | "Get the Title II deadline off my desk" | Avoid being on the news | Show measurable progress |
| Creator (long-tail YouTuber) | "Be the accessible channel in my niche" | Pride in inclusive content | Audience differentiation |

---

## 4.3 — The product wedge: what to actually build first

Given the competing options, here is the recommended wedge.

```
   ┌─────────────────────────────────────────────────┐
   │  WEDGE: "ASL Practice Mode" for YouTube         │
   │                                                 │
   │  • Chrome extension, freemium                   │
   │  • Pause-on-sign learning mode (key UX twist)   │
   │  • Vocabulary tracker / streaks (light gamify)  │
   │  • Teacher-friendly classroom mode (B2B hook)   │
   └─────────────────────────────────────────────────┘
```

**Why "ASL Practice Mode" beats "ASL Captions for the Deaf" as a wedge:**

1. **Word-level gloss is actually correct for learners.** It matches ASL I curriculum. It's wrong for native consumption — but learners need exactly this granularity.
2. **B2C learner traction → B2B education sales.** Once teachers see students using it on their own, district pilots get easy.
3. **It defers the cultural-acceptability question** until the product has earned standing to enter the conversation.
4. **It generates the data flywheel** — usage logs of which words confuse learners feed corpus prioritization.

The existing GenASL codebase already does ~80% of what this wedge requires. The remaining 20% is UX polish, gamification, and a learner-mode toggle.

---

## 4.4 — Product roadmap (24 months)

### Phase 1 — Months 0–6: Validation & wedge launch

| Workstream | Deliverable | Why |
|-----------|-------------|-----|
| **Deaf community advisory** | 5-person paid advisory board (Gallaudet alumni network is the obvious starting place) | Cannot be skipped; everything else depends on this |
| **Privacy & ToS hardening** | Replace `youtube-transcript-api` with official Data API + caption upload pipeline | Eliminate the single biggest fragility |
| **Learner UX** | Pause-on-sign mode; per-sign confidence indicator; "I don't know this sign" feedback button | The wedge product |
| **Chrome Web Store launch** | Public extension, freemium tier | Distribution begins |
| **K-12 pilot** | 3 schools, free 1-year pilot with feedback contract | Reference customers |

### Phase 2 — Months 6–12: Education GTM

| Workstream | Deliverable |
|-----------|-------------|
| **Pricing live** | $9/mo individual; $4/seat/yr education | First revenue |
| **LMS integrations** | Canvas + Brightspace add-ons (read-only assignments mode) | EdTech beachhead |
| **Corpus expansion** | 2,000 → 4,000 glosses; signed by paid Deaf signers, with non-manual markers captured | Quality differentiator |
| **Compliance reporting v1** | Coverage report PDF per video for procurement teams | Enterprise prep |

### Phase 3 — Months 12–18: Enterprise wedge

| Workstream | Deliverable |
|-----------|-------------|
| **Browser SDK** | Embeddable on any HTML5 video player, not only YouTube | Removes platform risk |
| **Self-hosted appliance** | Docker image; on-prem LLM (Ollama); offline mode | Sells into regulated buyers |
| **First 5 paid enterprise contracts** | $30–60k ACV; LMS / training / public sector | Validate ACV model |
| **Sentence-level synthesis R&D** | Pilot research project with Gallaudet / Boston U. | Future moat |

### Phase 4 — Months 18–24: Platform

| Workstream | Deliverable |
|-----------|-------------|
| **Sentence-level ASL** | Beta of grammar-aware synthesis (topic-comment, classifiers, NMMs) | Real ASL, not gloss |
| **BSL + AUSLAN** | Extend corpus & translator | UK/AU revenue |
| **Partner channel** | 3Play / Verbit reseller pilots | Distribution flywheel |
| **Series A readiness** | $15–20M raise at $80–120M post | Scaling capital |

---

## 4.5 — The non-negotiable: Deaf-community co-design

This must be stated explicitly because the rest of the strategy collapses if it's skipped.

**Before any paid GTM step:**

1. Hire (paid) Deaf advisors. NAD, NBDA, Gallaudet career office, ASLized are the channels.
2. Publish a public position statement: *"GenASL is an ASL augmentation tool for learners and supplementary access. It does not replace interpreters, captions, or human-produced ASL content for Deaf-native consumption."*
3. Compensate every signer who contributes to the corpus (per-sign fee schedule + royalty if commercialized).
4. Refuse contracts that position GenASL as "replacing" interpreters — even when the buyer offers premium pricing for that framing. This is the single biggest reputation risk in the space.

This is a strategic decision, not just an ethical one. The history of the field (Apple's animojis, BBC's avatar trials, Bonn airport signing avatar) shows that products without Deaf endorsement get loud public criticism that crushes B2B sales cycles.

---

## 4.6 — The "why now" answer

> "Three things converged in 2025–2026: ADA Title II deadlines force public-sector procurement; LLMs made gloss-translation cheap enough to render in real time in the browser; and the captioning industry has commoditized to the point where buyers want a next compliance line item to budget for. ASL is that line item."
