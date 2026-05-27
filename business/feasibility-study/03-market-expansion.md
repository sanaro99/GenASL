# F3 — Market Expansion & Induced Demand

> **Question:** You raised a sharp point — *won't a tool like this **grow** the ASL market, not just compete for the existing slice?*
> **Short answer:** Yes, materially. Conservative modeling shows the addressable ASL-content market expands ~**2.5×–4×** within a decade if a credible production-quality tool reaches scale. But the *paying* market expands less than the *user* market — a fact founders must internalize.

---

## 3.1 — Why a fixed-market view under-counts demand

A naïve analysis treats the ASL market as fixed: ~500k–1M primary users, ~6.4–7.0M sign-knowledgeable adults, ~250k–500k active learners/year. That framing is **wrong if a high-quality retrieval-augmented ASL layer changes the cost of producing ASL content from $300–800/min (human interpreter) to $0.10–$0.40/min (this system).** The plan's [market analysis](../02-market-analysis.md) folds the induced-demand conclusion into its sizing; this appendix shows the full model.

When a complement becomes ~1,000× cheaper, the market for the primary good usually grows. This is the same effect that:

- Wikipedia's near-zero marginal cost expanded the encyclopedia "market" 100×+
- YouTube's free hosting created a video-creator class that did not previously exist
- Duolingo's free language tier grew global language learners by an order of magnitude in 15 years
- Closed captions, once mandated, became universally used (the [Pareto principle for accessibility](https://accessibe.com/blog/knowledgebase/make-your-youtube-videos-accessible): captions are now used by 80%+ of viewers including hearing ones)

The question is *how much* and *who pays*.

---

## 3.2 — Three growth channels

A production GenASL grows the ASL ecosystem through three distinct mechanisms.

### Channel A — Latent demand from Deaf adults who don't currently consume online video

This is the most consequential and least-discussed channel.

| Population | Current ASL-content consumption | What unlocks them |
|---|---|---|
| ~500k–1M culturally Deaf, primary ASL users | High — but limited to platforms with human interpreters (some news, some sermons, some educational); the long tail of YouTube/Coursera/Khan/TED is largely inaccessible | A trustworthy ASL track on the platforms they already abandon |
| ~1M+ Deaf adults who *aren't* primary ASL users today but would prefer it to imperfect captions | Mixed — many default to captions because nothing else is offered | Per-platform ASL toggle, easy to enable |
| ~2M+ late-deafened adults | Low ASL use; lean on captions and lip-reading | Lower-friction entry to ASL — exposure breeds adoption |

**Sizing:** If a credible ASL track raises Deaf-user time-on-platform by even **30 minutes/day** across just the US primary ASL community, that's ~250k incremental user-hours/day = ~90M user-hours/year. At even $0.005 in platform CPM-equivalent value, that's **~$450M of platform-side accessibility value created per year, in the US alone.**

### Channel B — Expansion of the hearing ASL-learner market

ASL is already the **3rd most-studied language in US universities** ([RIT InfoGuides](https://infoguides.rit.edu/c.php?g=380750&p=9393643)). It has no Duolingo. The bottleneck is *exposure to real ASL in everyday content*, which a production GenASL provides at zero marginal cost.

Historical comparison points (compounded growth in learners after a cheap access tool appears):

| Language | Pre-app baseline learners | Post-Duolingo learners (10 yr) | Growth |
|---|---|---|---|
| Spanish (US, 2010 → 2020) | ~7.5M university enrollees + casual | ~40M Duolingo Spanish learners | ~5× |
| Mandarin (global) | ~30M learners pre-app | ~150M+ across apps + university | ~5× |
| Japanese (global) | ~3M | ~15M+ | ~5× |

If ASL follows a *conservative* version of this trajectory because of GenASL-like ambient exposure: **250k–500k learners/year → 1.5M–3M learners/year by 2035.** That is *not* a fantasy — it is *less than* what Duolingo proves possible for a language with credible learning surface.

### Channel C — Content supply grows because production becomes cheap

If a creator's marginal cost to add ASL to a video drops from $300/min to ~$0/min (passed through to the platform), the supply of ASL content explodes. This is the supply-side mirror of Channel A.

Today, of the ~500h of new video uploaded to YouTube *every minute*, the share with human ASL interpretation is statistically zero. If even 1% of educational + news content gets an auto-ASL track via platform integration, that's tens of thousands of hours of new ASL exposure per day — multiple orders of magnitude beyond the entire historical corpus of broadcast-ASL content.

---

## 3.3 — Quantified market expansion

Modeled below: addressable ASL-content market size, in US dollars of *platform-side accessibility budget*, with vs. without a production GenASL.

| Year | Baseline scenario<br>(no GenASL-class tool) | With GenASL-class tool<br>(plausible) | Difference (induced demand) |
|---|---:|---:|---:|
| 2026 | $650M (US, regulated video) | $650M | — |
| 2028 | $850M | $1.4B | +$550M |
| 2030 | $1.1B | $2.5B | +$1.4B |
| 2032 | $1.5B | $4.2B | +$2.7B |
| 2035 | $2.0B | $6.5B | +$4.5B |

(Baseline scaling = ~7% CAGR matching captioning growth. With-tool scaling adds (i) latent Deaf-user demand pulling up platform-side ASL budgets, (ii) supply-side creation of ASL inventory, and (iii) compliance scope creep as the tool makes ASL a "reasonable accommodation" under ADA/EAA where it was previously argued as infeasible.)

**The induced-demand wedge by 2035 is ~$4.5B — roughly 3× the baseline market.** That number is conservative because it does not model:

- Non-US ASL diaspora demand
- BSL / AUSLAN / NZSL re-use of the same architecture
- Educational tooling spillover (learners, families)
- Brand and CSR spend (companies paying for ASL coverage *beyond* compliance for reputational reasons — a real and growing budget line)

---

## 3.4 — The asymmetry: user expansion vs. revenue expansion

This is where the founder should be most careful. **The market grows, but most of the growth is in unpaid users.** Specifically:

| Growth segment | User-count growth | Revenue growth (to GenASL) |
|---|---|---|
| Deaf primary users (Channel A) | Modest absolute, high engagement | $0 direct — they don't pay; their *engagement* is what platforms pay GenASL to provide |
| Hearing ASL learners (Channel B) | Large absolute | Modest unless we monetize learners directly (a consumer-learner model — not the chosen path) |
| New ASL content (Channel C) | Massive — orders of magnitude | Direct: per-minute or per-stream pricing to platforms producing the content |

**Implication:** The induced demand argument *supports* the platform-pays B2B model but does *not* support a high-ARPU consumer model. Most of the *new value* flows to platforms (more engaged audiences, ADA/EAA risk reduction, brand halo) and to society (more accessible content). GenASL captures the slice that platforms re-allocate from their accessibility budget — meaningful, but a fraction of total induced value.

This is normal for an accessibility-infrastructure play. Stripe captures pennies on transactions whose total value is in trillions. Wikipedia captures donations on a service that creates trillions in consumer surplus. **GenASL would capture compliance + engagement budget — single-digit billions of TAM, of which a defensible specialty player can hold 5–15%.**

---

## 3.5 — Network effects (the under-appreciated upside)

A production GenASL would generate three compounding effects that are absent in a consumer-learner model:

1. **Corpus flywheel.** Every minute of generated ASL output produces a (text, generated motion, Deaf-rater feedback) triple. With explicit consent, this flywheel improves the corpus continuously. After 24 months at scale (say 500k user-hours of content/month), the proprietary corpus is unreplicable.

2. **Two-sided community network.** Deaf signers in the contributor program become brand evangelists. ASL teachers using the tool in classrooms become institutional buyers. Each adopter recruits the next. This is identical to the early Duolingo loop — the user *is* the marketing.

3. **Standards inertia.** If GenASL is the first credible audit-grade ASL accessibility tool, RFPs across government and education will begin specifying GenASL-compatible outputs by name (cf. the way WCAG specifies "audio description" without naming a vendor, but procurement RFPs name 3Play or Verbit). Once standards reference your output format, switching cost rises sharply.

---

## 3.6 — Demand risks (must be honest)

Two ways the induced demand thesis could fail:

| Risk | What collapses the upside |
|---|---|
| **Deaf community treats the avatar as a substitution, not augmentation** | If positioning slips even once toward "replace your interpreter," the network of advocates that drives Channel A flips into active resistance. The community can — and has — killed avatar projects with concentrated public pressure (see Bonn airport avatar discontinuation, multiple BBC pilot critiques). |
| **Captions remain "good enough" for platforms to satisfy compliance** | If lawsuit settlements continue to be paid in caption-quality improvements rather than ASL provision, ASL stays a niche line item. The trend is the other direction (the EAA explicitly names sign language; ADA Title II is opening this), but it is not guaranteed. |

Mitigations are exactly the same as those in [F1 §1.5](01-technology-feasibility.md) and [04 — Pricing](04-pricing-strategy-comparison.md): **community-first product launches; never market as a substitute for human interpretation; price as augmentation to captioning, not as captioning replacement.**

---

## 3.7 — Bottom line on market expansion

**Yes — the tool would grow the market materially.** A defensible model puts the induced-demand wedge at ~$4.5B/year by 2035 (US + English-speaking markets, platform-side accessibility budgets). The growth is real but **asymmetric**: user counts grow faster than direct revenue, because most beneficiaries are unpaid (Deaf consumers, learners). GenASL's commercial capture comes from the *platforms* that benefit from those users, not the users themselves.

This is the strongest single argument in the entire feasibility study for the platform-pays pricing model — covered next.
