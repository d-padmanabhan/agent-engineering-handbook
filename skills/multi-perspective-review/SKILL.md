---
name: multi-perspective-review
description: Structured multi-advisor review of an architecture, vendor, strategy, or design decision. Each advisor (data, architecture, business value, operations, risk, executive sponsor, etc.) gives a position vote, a one-sentence pro and con, and the sharp question they would ask. Every assertion carries a "what worked" and "horror story" industry-precedent pair. A weighted scoring model lets the user influence outcomes via emphasis profiles (balanced, value-first, risk-averse, platform-forward, ops-heavy, data-forward, executive-sponsor, custom). Use when the user wants stakeholder perspectives, panel review, pro/con across multiple lenses, weighted recommendation, or wants to re-weight an existing analysis with a different strategic emphasis.
---

# Multi-Perspective Review

A structured panel review framework for any architecture, vendor, strategy, or design decision. Embeds 5-7 expert perspectives, attaches industry-precedent evidence to every assertion, and uses a weighted scoring model so the user can influence outcomes by adjusting how much emphasis each advisor receives.

**Companion rules:**

- `100-core.mdc` - core engineering principles
- `015-context-engineering.mdc` - prompt packing, retrieval, compaction

---

## When to invoke

Use when the user asks for:

- "Panel review" / "stakeholder perspectives" / "advisory panel"
- "Pro/con analysis across multiple lenses"
- "Weighted recommendation" / "strategic review"
- "What would my CTO / Security / Finance say about this?"
- Re-weighting an existing review with a different emphasis
- A structured architecture / vendor / strategy decision that has multiple valid framings

Do *not* use for:

- Single-lens reviews (just call the right specialist skill)
- Decisions where one perspective dominates by mandate (compliance verdict, security veto)
- Quick judgement calls that do not need a structured trade-off

---

## The Six Golden Rules

1. **Every advisor has a coherent lens.** Not "what should we do" but "what is this decision *as seen through this lens*".
2. **Every assertion carries an industry-precedent pair.** What worked elsewhere; what blew up elsewhere.
3. **Weights always sum to 100%.** Force the user to make trade-offs explicit.
4. **Votes are bounded** (typically -2..+2). No infinite scales; no abstentions.
5. **Contested decisions** (within ~0.15 of a band boundary) are flagged - the outcome is sensitive to re-weighting.
6. **Never silently use the default profile.** Always prompt; defaulting to balanced hides bias.

---

## The advisor roster (default)

A 6-advisor roster works for most technology decisions. Adjust per domain - mortgage decisions might add a `LEGAL` advisor; AI/ML decisions might add a `MODEL_RISK` advisor.

| Code | Advisor | Lens |
|---|---|---|
| `DS` | Chief Data & Analytics Strategist | Data value chain: ingest -> integrate -> quality -> store -> analyze -> act -> feedback |
| `ARCH` | Enterprise Technology Architect | Reversible vs irreversible decisions; platform leverage; exit optionality |
| `BV` | Business Value & Transformation Leader | Value-first sequencing - each phase must name the metric that moves |
| `OPS` | Operations & Reliability Strategist | Reliability, efficiency, evolvability - can we run it? |
| `RISK` | Risk, Security & Governance Advisor | Trust as infrastructure - security, privacy, compliance designed in |
| `EXEC` | Executive Sponsor (CTO / Senior Partner) | Board-level narrative; pattern recognition across industries; calm authority under ambiguity |

For each advisor, the panel emits:

- **Vote** in `{-2, -1, 0, +1, +2}`
- **One-sentence pro** (why this advisor would back the decision)
- **One-sentence con** (why this advisor would resist)
- **Sharp question** the advisor would ask before approving

---

## Industry-precedent pairs

Every assertion (per product, per cross-cutting decision, per architecture choice) carries:

| Field | Content |
|---|---|
| `what_worked` | One-sentence positive industry precedent showing the assertion has been delivered successfully at comparable firms |
| `horror_story` | One-sentence cautionary precedent (failure mode or tripwire) observed on the same assertion at peer firms |

These are item-level (not per-advisor) - industry precedents apply to the decision as a whole. They live next to the per-advisor pro/con, not interleaved with them.

**Why both, always:** sales decks show only `what_worked`; risk reports show only `horror_story`. A real review needs both, side by side, on every claim. If you cannot supply both, mark the missing one as REVIEW.

---

## Weight profiles

Seven presets plus Custom. Always sum to 100. Reweight as needed for a 5- or 7-advisor roster.

| Profile | DS | ARCH | BV | OPS | RISK | EXEC | When to use |
|---|---|---|---|---|---|---|---|
| `balanced` | 17 | 17 | 17 | 17 | 16 | 16 | Default - no strategic bias warranted |
| `value-first` | 15 | 15 | 30 | 15 | 15 | 10 | Business-outcome pressure - ROI and adoption first |
| `risk-averse` | 15 | 15 | 15 | 15 | 30 | 10 | Regulated / high-change environments |
| `platform-forward` | 15 | 30 | 15 | 15 | 10 | 15 | Architecture-driven; reduce sprawl aggressively |
| `ops-heavy` | 15 | 15 | 15 | 30 | 15 | 10 | Operations under pressure; FinOps and reliability lead |
| `data-forward` | 30 | 15 | 15 | 15 | 15 | 10 | Analytics / AI strategy leading the investment case |
| `executive-sponsor` | 15 | 15 | 20 | 10 | 10 | 30 | C-suite counsel bias - board-level narrative dominates |
| `custom` | -- | -- | -- | -- | -- | -- | User-supplied; must sum to 100 |

---

## Scoring

For each item, each advisor has a vote `v in {-2, +2}`. Weighted score:

```
S = sum( (weight_percent / 100) * vote_advisor )
```

Decision bands:

| Score | Decision |
|---|---|
| `S >= +1.20` | RETAIN & EXPAND / GO |
| `+0.40..+1.19` | RETAIN / PROCEED |
| `-0.39..+0.39` | RETAIN (SCOPED) / CONDITIONAL |
| `-0.40..-1.19` | PHASE OUT / DEFER |
| `S <= -1.20` | DECOMMISSION / NO-GO |

A score within **+/-0.15 of a band boundary** is flagged **contested** - the outcome is sensitive to re-weighting. Surface this prominently; offer to run the same review under another profile to test.

---

## Workflow

1. **Determine the weight profile.** Use `AskQuestion`. Do not silently default. Accept:
   - One of the preset names
   - Custom: ask for the percentages in `DS,ARCH,BV,OPS,RISK,EXEC` order
   - Reject anything that does not sum to 100
2. **Enumerate items.** Decisions, products, architecture choices - whatever the user is deciding among.
3. **For each item, populate the panel:**
   - Industry-precedent pair (`what_worked` + `horror_story`)
   - Per advisor: vote, pro, con, sharp question
4. **Score.** Compute `S` per item. Compare against any baseline; flag contested ones.
5. **Report.** Structured response with the precedent pair on top, per-advisor rows below, weighted outcome at the bottom. If multiple items, end with a summary table sorted by score.
6. **Offer to re-weight.** If a decision is contested or the user signals dissatisfaction, suggest running again with a different profile (typically the opposite of whatever was chosen first).

---

## Output format

```markdown
## <Item>: <one-line decision>

**EVIDENCE**
- WHAT WORKED: <one-sentence positive industry precedent>
- HORROR STORY: <one-sentence cautionary precedent>

| Advisor | Vote | Pro | Con | Sharp question |
|---|---|---|---|---|
| DS  | +1 | ... | ... | ... |
| ARCH | +2 | ... | ... | ... |
| BV  | -1 | ... | ... | ... |
| OPS | 0  | ... | ... | ... |
| RISK | +1 | ... | ... | ... |
| EXEC | +2 | ... | ... | ... |

**Weighted score (profile: <name>):** S = +0.83 -> **RETAIN / PROCEED**
**Contested?** No (band boundary at +0.40 / +1.20; nearest is 0.37 away)
```

---

## Integration with downstream skills

This skill composes well with:

- **An analysis skill** (e.g., `technology-consolidation-analysis`) - the analysis skill auto-detects this skill and adds `Advisory Panel` + `Weighted Recommendations` tabs to its workbook output.
- **A dashboard skill** - the dashboard renders per-item advisor views with green "what worked" and red "horror story" callouts under the item selector.
- **A decision-record skill** (ADRs) - the panel review becomes the "alternatives considered + rationale" section of the ADR.

When composing, see `skills/skills-composition` for HITL gates between phases and graceful degradation when an optional sibling is absent.

---

## Authoring guidance

### Writing the per-advisor view for a decision

The trap: writing the pro/con as "this advisor would say <generic argument>". The point is the **specific** argument this advisor cares about.

Bad (`OPS` for "adopt managed Postgres"):

- Pro: "Reduces infrastructure burden."

Good:

- Pro: "Patching, replication, and PITR move from the SRE rotation to the cloud provider; SRE time freed up for app reliability work."

### Writing the precedent pair

Be specific. Vague precedents read as filler.

Bad: "Most companies have done this successfully."

Good: "Spotify migrated 1,200 services to managed Postgres in 18 months with zero data loss; the SRE rotation shrank by 30%."

If you do not have a specific precedent, mark REVIEW. Do not invent.

### Writing the sharp question

The question the advisor would ask before approving. Forces clarity in the design.

Examples:

- DS: "What is the data quality SLO and who owns the dead-letter queue?"
- ARCH: "What is the exit path if the vendor doubles their price next year?"
- RISK: "Where does the audit log live and how long is retention?"
- EXEC: "What is the headline result the board will hear in 12 months?"

---

## Anti-patterns

1. **Default to balanced silently.** Always prompt; defaulting hides bias.
2. **Generic pro/con.** Each advisor must speak from their lens, not produce a general argument.
3. **Missing precedent.** Drops the discipline that distinguishes this skill from a feel-good panel.
4. **Single source for `what_worked` / `horror_story`.** At least one industry-public reference; mark REVIEW if not available.
5. **Hidden weight changes.** If you re-run with different weights, surface that explicitly.
6. **Skipping contested-flag annotations.** Contested decisions are the most useful output of the framework.
7. **Voting +/-3 or beyond.** Bounded scale; out-of-bounds votes are noise.
8. **Letting one advisor dominate via vote magnitude.** All votes are bounded; influence comes from weights, not vote inflation.

---

## When NOT to use

- **Single-lens decisions** - if only one perspective matters, do not pretend.
- **Compliance / safety vetoes** - if RISK has a hard veto, the panel is theatre. Surface the veto first.
- **Personal-preference decisions** (which IDE? which font?) - the framework adds friction without adding signal.
- **Quick exploratory choices** - reserve for decisions worth 30+ minutes.

---

## Extending the skill

- **Add an advisor** - update the roster table and redistribute weights to sum to 100. Default new advisor to the lowest weight in `balanced`.
- **Domain-specific roster** (e.g., for FinTech: `LEGAL`, `COMPLIANCE`, `MARKET_RISK`) - swap or supplement the default 6.
- **Domain-specific profile** (e.g., `regulated-financial-services`) - new preset summing to 100.
- **Voting scale** - the default is integer `[-2, +2]`. For finer-grained reviews, allow halves; for binary calls, restrict to `{-1, +1}`. Document the scale in the report header.

---

## Related

- Rule: `100-core.mdc` - SOLID / DRY / KISS
- Rule: `015-context-engineering.mdc` - prompt packing
- Skill: `skills-composition` - patterns for chaining this with analysis skills
- Skill: `agent-workflow` - workflow patterns for complex multi-step tasks

## Attribution

Pattern adapted from a six-advisor consulting-toolkit framework that combines per-advisor pro/con/question views with industry-precedent pairs and weighted scoring. The discipline of "every assertion carries both `what_worked` and `horror_story`" cuts through analysis paralysis and over-confidence in equal measure.
