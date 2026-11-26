---
name: core-engineering
description: Core coding standards and best practices for code review and generation. Provides KISS and measurable clean-code outcomes, guiding principles (DRY, YAGNI, SOLID), priority frameworks, tooling baselines, dependency management, and response formats. Use when reviewing code, generating code, asking about coding standards, or when the user needs general engineering guidance that applies across all languages.
---

# Core Engineering Standards

Mandatory universal gates are owned by the core rule (`${HANDBOOK_ROOT}/rules/100-core.mdc`). This skill owns review and generation procedures, examples, and decision support.

## Guiding Principles

- **Simplicity First:** Simple code is maintainable code. Apply DRY, KISS, YAGNI, and SOLID principles.
- **Minimal Changes:** Fix what's broken without refactoring what works. Preserve existing functionality.
- **Value-Driven:** Every suggestion must add clear value. Avoid over-engineering.
- **Production-Ready:** Include error handling, meaningful names, security-first approach, and appropriate documentation.
- **Operate at a Senior Principal / top-tier bar:** Use your judgement, think deeply, choose the simplest correct approach, make assumptions explicit, and optimize for long-term operability.
- **Constructive Collaboration:** Frame feedback respectfully, focus on code not author. Assume good intent.

## Non-Negotiable: KISS and Clean-Code Outcomes

Apply **KISS (Keep It Simple)** to every design, implementation, and review. Choose the simplest correct solution that meets current requirements and operational constraints. Do not add layers, patterns, dependencies, configuration, or extension points for hypothetical future needs.

Treat "clean code" as observable outcomes, not as an appeal to a particular book, author, or methodology. Generated or modified code MUST:

- use precise, domain-meaningful names and consistent conventions;
- keep functions, methods, classes, and modules cohesive and focused;
- keep control flow understandable and make errors, side effects, ownership, and resource lifecycles explicit;
- reduce meaningful duplication without forcing premature or misleading abstractions;
- separate concerns where doing so improves comprehension, testing, or change safety;
- avoid dead code, speculative generalization, clever shortcuts, hidden coupling, and comments that merely restate the code;
- preserve correctness, security, accessibility, performance, compatibility, and observability instead of sacrificing them for cosmetic simplicity.

Small code is not automatically simple code. When domain complexity is unavoidable, isolate it, document the reason, test the behavior, and keep it from spreading into unrelated components.

Write code that is impossible to misunderstand. The test: a competent engineer new to the code can tell what it does, why it does it, and how to change it safely, without asking the author.

Clean, cohesive, predictable code is also cheaper and safer for AI agents to read and modify: it reduces the context that must be loaded, lowers navigation and inference cost, and makes targeted changes less likely to affect unrelated behavior. Optimize for clarity, locality, explicit interfaces, and discoverable structure - not token count alone. Compressed code, excessive indirection, fragmented abstractions, and redundant documentation can increase agent cost even when individual files are short.

## Simplification Pass (On Request)

When the user asks to simplify, clean up, or refine code, including through Cursor's built-in `code-simplifier` subagent, run a behavior-preserving pass:

- Run it only when requested, and limit scope to code changed in the current task or paths the user names. Refactoring other code needs a separate request.
- Preserve behavior exactly: outputs, side effects, errors, public interfaces, and performance characteristics. Run existing tests before and after; when coverage is missing, add a characterization test first.
- Reduce nesting with guard clauses, remove redundant code and indirection, consolidate duplicated logic, and improve names.
- Prefer clarity over brevity: use `if`/`else` or `switch`/`match` instead of nested ternaries, and split dense one-liners.
- Keep abstractions that improve organization or testability, and do not merge unrelated concerns.
- Follow repository conventions and the relevant language skill rather than a generic house style.
- Remove comments that only restate code; keep comments that explain intent or constraints.
- Report what changed and how behavior preservation was verified.

## Sample and Reference Applications

A sample application exists to teach. Optimize it for the reader learning from it, not for feature coverage:

- Demonstrate one concept, or a small connected set, with the fewest dependencies and files that show it faithfully.
- Prefer explicit, linear code over abstractions; a reader should follow the main path from entry point to result in one sitting.
- Provide a runnable quickstart with pinned versions, and verify it works exactly as written.
- Keep secure defaults. When a shortcut is unsafe for production, such as disabled authentication or a local-only secret, label it in the code and the README and state what production requires instead.
- Use comments to explain why a step exists and what to change for real use, not to narrate each line.
- Use synthetic `acme.com` data and never real credentials.

Follow the documentation standards skill (`${HANDBOOK_ROOT}/skills/documentation-standards/SKILL.md`) for the README.

## Priority Framework

Organize feedback by impact:

| Priority | Description | Examples |
|----------|-------------|----------|
| **Critical** | Security vulnerabilities, bugs that break functionality, data loss risks | Injection flaws, hardcoded secrets, unhandled exceptions |
| **Recommended** | Performance issues, maintainability problems, scalability concerns | N+1 queries, tight coupling, missing error handling |
| **Optional** | Style improvements, future-proofing, minor optimizations | Naming tweaks, code comments, minor refactors |

## Tooling Baseline

| Language | Linting/Formatting | Security |
|----------|-------------------|----------|
| Python | Python 3.14 + `uv`; `ruff` check/format; pylint (≥9.0) | `pip-audit` |
| Bash | `shfmt` + `shellcheck` | - |
| Go | `gofmt` + `golangci-lint` | `govulncheck` |
| JS/TS | `eslint --max-warnings=0` | `npm audit` |
| Terraform | `terraform fmt` + `tflint` | - |
| All | `ggshield` + `gitleaks` | Dependency scanning on PRs |

## Naming Conventions

- **Domain Names:** Use `acme.com` for examples (never `example.com`)
- **Company/Org:** Use `ACME` or `Acme`
- **Consistency:** Apply across code, docs, configs, and test data

## Code Review Essentials

1. Identify main issues first before diving into details
2. Provide specific, actionable suggestions with working code examples
3. Explain the "why" - what benefit does the change provide?
4. Suggest incremental refactoring over big-bang rewrites
5. Preserve existing code - no placeholders or incomplete sections

**Evaluation Areas:** Security, Error Handling, Testing, Observability, Resource Management, Concurrency, Performance

For detailed review patterns and formats, see code review reference (`${HANDBOOK_ROOT}/skills/core-engineering/references/code-review.md`).

## Algorithmic Complexity Contract

When input size can grow or performance is material:

- Define what each variable represents, such as `n` records and `m` lookup keys. Do not write `O(n)` without naming the input.
- Analyze worst-case time and auxiliary space by default. State average, expected, amortized, or output-sensitive complexity only when that qualification matters and its assumptions hold.
- Account for nested and sequential work correctly: nested independent inputs are commonly `O(n * m)`, while sequential phases are `O(n + m)`.
- Include sorting, copying, allocation, hashing, serialization, database calls, network calls, and produced output when they dominate the operation.
- Distinguish expected hash-table lookup from guaranteed worst-case behavior. Do not claim unconditional `O(1)`.
- Compare alternatives using both time and space. A faster lookup may require `O(n)` auxiliary memory.
- Treat Big O as a growth model, not a benchmark. Constants, cache locality, allocation, I/O, bounded inputs, and realistic distributions still require measurement.
- Do not optimize a clear, bounded path solely to improve notation. Require a bottleneck hypothesis and measurement plan before making performance-driven changes.

Use the algorithmic complexity reference (`${HANDBOOK_ROOT}/skills/core-engineering/references/algorithmic-complexity.md`) for analysis procedure, common operations, and review examples.

## Code Generation Essentials

1. Handle ambiguity proactively - proceed with minimal assumptions, list ≤3 targeted questions
2. Design clean architecture - easy to test, maintain, and extend
3. Provide complete, runnable code - no TODOs or placeholders
4. Include practical examples - usage examples or basic test cases
5. Document appropriately - inline comments for complex logic only

**What to Include:** Error handling, logging, type hints, externalized configuration, docstrings

**What NOT to Include:** Over-engineered abstractions, premature optimization, extensive test suites, complex frameworks when stdlib suffices

For detailed generation patterns, see code generation reference (`${HANDBOOK_ROOT}/skills/core-engineering/references/code-generation.md`).

For end-to-end architecture, capacity planning, SLOs, service/data boundaries, failure design, and migration strategy, use the system design skill (`${HANDBOOK_ROOT}/skills/system-design/SKILL.md`). This skill remains focused on code-level engineering.

## AI-Assisted Coding

The agent (an LLM in Cursor / Claude / Codex / etc.) is a fast, persuasive, partly-informed pair programmer. Treat its output the way you'd treat a confident junior engineer's PR: take what's good, edit what's wrong, never let it cross a security or correctness boundary unreviewed.

**Where AI consistently helps:**

- Boilerplate (test fixtures, CRUD scaffolds, type stubs)
- Mechanical transformations (rename, reformat, port between languages)
- Drafting (commit messages, docstrings, release notes, ADR first drafts)
- "What's the canonical way to X?" research
- Reading code you didn't write (summarize, find call sites, explain a regex)

**Where AI consistently misleads:**

- Library versions and APIs - fabricates signatures, hallucinates deprecated methods, invents flags. Verify with `gh release view`, the actual `--help`, or the docs.
- Current state of the world - "as of 2026" claims about pricing, SLAs, regulatory text, deprecation timelines. Verify or omit.
- Domain reasoning - anything requiring business context the model wasn't trained on.
- Security boundaries - auth, crypto, IAM policies, SQL with dynamic input, shell with user input. Read line-by-line, not skimmed.
- File paths, commit hashes, line numbers, CVE ids. Verify before quoting.

**Rules:**

1. **Read the diff before the summary.** Summaries embellish; the diff is the source of truth.
2. **Verify every external reference.** Library version, API signature, CVE id, CHANGELOG line, citation. Half of fabrications are confident-sounding but wrong.
3. **Ask for a counterexample.** If the agent claims X is always true and can't produce a case where it isn't, the claim is suspect.
4. **Bound the autonomy.** Long-running agent tasks need HITL gates before destructive or irreversible steps. See zero-trust skill / hitl-gates (`${HANDBOOK_ROOT}/skills/zero-trust/references/hitl-gates.md`).
5. **The "would a senior engineer have written this" test.** If the answer is no, edit before merging.

### Current vendor docs are mandatory

For vendor, cloud, SDK, API, CLI, IaC provider, runtime, security, or auth behavior, do **not** rely on model memory alone. Verify current official docs, release notes, provider schemas, CLI `--help`, repository releases, or installed tool output before recommending syntax, defaults, versions, limits, or architecture patterns.

Use this especially for:

- Cloud and data platforms: AWS, Azure, GCP, Cloudflare, Databricks, Snowflake, Okta
- IaC/provider APIs: Terraform, Pulumi, CloudFormation, Kubernetes, Helm
- Runtimes and package managers: Python, Node.js, Go, Rust, Java, pnpm/npm/uv
- CI/CD surfaces: GitHub Actions versions, setup actions, OIDC/auth patterns
- Security/auth/IAM behavior: OAuth/OIDC/SAML, workload identity, IAM, API gateways
- Renamed or fast-moving products: e.g., DLT -> Lakeflow, Databricks Asset Bundles -> Declarative Automation Bundles

If legacy guidance is intentionally retained, label it as **legacy**, explain when it still applies, and keep the current pattern nearby.

**Slop smells in agent output (cut on sight):**

- Words like "robust", "leverage", "seamless", "comprehensive", "best-of-breed" → almost always filler.
- Lists where items paraphrase each other → padded; the agent didn't have N points.
- Confident claim that something is "best practice" without a source → ask for the source.
- Cites a library version when the user didn't mention one → check the version.
- Pep-talk sentences ("It's important to note that...", "When designing X, one must consider...") → delete.

## Dependency Management

Adding a dependency is a long-term commitment. **Prefer stdlib or existing dependencies.**

Use the latest supported stable release compatible with the repository and deployment target. Do not interpret "latest" as permission to select prereleases, invent aliases, ignore support matrices, or bundle an unrelated major migration. Verify the exact release/ref, preserve reproducible pins and lockfiles, review breaking and security changes, and time-box exceptions.

Follow the dependency and toolchain currency workflow (`${HANDBOOK_ROOT}/skills/core-engineering/references/dependency-and-toolchain-currency.md`).

Vetting criteria for new dependencies:

- [ ] **Justification:** Truly necessary? Solves complex problem?
- [ ] **Maintenance:** Actively maintained? Recent commits?
- [ ] **Security:** Audited? Known CVEs?
- [ ] **License:** Compatible (MIT, Apache 2.0)?
- [ ] **Community:** Good docs and clear API?

## Error Handling Philosophy

Three responses to an error. Default to the first.

| Mode | When | How |
|---|---|---|
| **Wrap with context and propagate** | Default | Add what *this layer knows* (request id, operation, key inputs) and re-raise |
| **Handle locally** | This layer is the boundary that knows what to do (retry, fallback, return default) | Handle, log the decision, do not re-raise |
| **Swallow** | Rare; only when the error is truly irrelevant (best-effort cleanup) | Log + comment justifying the swallow + monitor the swallow rate |

**Rules:**

- Never log *and* re-raise from the same layer. Pick one. Double-logging makes incident triage worse.
- Retry only transient classes: network timeout, 429, 5xx, connection reset. Never retry a 4xx; never retry a logic bug.
- Bound every retry: max attempts, max total time, exponential backoff with jitter.
- Fail fast on invariant violation. Corrupted state is worse than a crash.
- Errors crossing a process boundary need a stable representation: typed enum + message + correlation id. Stack traces are debug data, not API surface.

**Anti-patterns:**

- `try: ... except: pass` without a comment explaining why. Always wrong.
- Catching the base exception class to "make it robust". You've buried the cause.
- Wrapping every error in a generic "operation failed" string. Strip context, lose the ability to debug.
- Logging the same error at three layers as it propagates. The audit log fills with duplicates and the root cause is harder to find.
- Retrying a write without an idempotency key. Duplicates the write on the inevitable second attempt.

## Time, Numbers, Unicode

The three categories that bite every engineer. Get them right at boundaries.

**Time:**

- UTC at rest, always. Render in user TZ at the edge.
- Never compare wall-clock times for **durations** - use a monotonic clock. Wall clock jumps backward (NTP, leap seconds, manual change).
- Always specify TZ when parsing. `2026-05-17 14:00` is ambiguous; `2026-05-17T14:00Z` is not.
- Store as a typed instant: Postgres `timestamptz`, Python `datetime` with `tzinfo`, Go `time.Time`. Never as a string or epoch-ms without a comment naming the timezone.
- Schedules cross DST. Document whether "every day at 09:00" means wall clock or UTC.

**Numbers:**

- **Never `float` for money.** Use decimal: `decimal.Decimal` (Python), `BigDecimal` (Java/Kotlin), Postgres `numeric`, `pgx.Numeric` (Go). Float arithmetic silently produces `0.30000000000000004`.
- Round at the boundary you display, not at intermediate steps. Be explicit about the rounding mode (banker's vs round-half-up).
- Comparing floats with `==` is a bug. Use `abs(a - b) < epsilon` with a chosen epsilon, or stay in decimal.
- Mind integer overflow on 32-bit types. Counters, byte sizes, durations in ns - use 64-bit.

**Unicode:**

- UTF-8 default everywhere. Verify DB columns: Postgres `UTF8`, MySQL `utf8mb4` (plain `utf8` in MySQL is 3-byte and breaks emoji).
- Normalize (NFC) before comparing strings. `é` and `é` (combining vs precomposed) compare unequal until normalized.
- Case-folding ≠ lowercase for non-ASCII. The Turkish `İ` / `i` mismatch is the canonical bug.
- Locale-aware sorting only when output is user-facing. For storage and indexing, use byte order or explicit Unicode collation.
- Trust no input: length in bytes ≠ length in code points ≠ length in grapheme clusters.

## Comments & Documentation

The cost of a comment is the maintenance burden when the code drifts. The benefit is intent that the code can't express.

- Code says *what*. Comments say *why*.
- No narration. `// increment counter` is noise; the code is already saying that.
- Public APIs need docstrings. Private functions need them only when intent is non-obvious from the signature.
- For multi-step decisions, use ADRs (architecture decision records) over scattered comments. One file you can search beats ten comments you can't.
- Update the doc in the **same commit** as the code. A doc-only PR a week later is a guarantee they'll diverge again.
- When you delete code, delete the comments referencing it. Stale comments cost more than absent ones.
- TODOs need an owner and a date. `// TODO` alone is a wish. `// TODO(devesh, 2026-Q3): replace once X ships` is a commitment.

## Versioning & Deprecation

SemVer discipline:

- **Major** - breaking. Removed/renamed fields, changed types, changed defaults, changed error shapes, removed routes, performance regressions beyond a documented budget.
- **Minor** - additive. New fields, new methods, new routes, new error codes (well-behaved downstream callers ignore unknown).
- **Patch** - fix. No surface change.

What counts as breaking that you might miss:

- Tightening validation (input that used to be accepted is now rejected).
- Changing default behavior even when the API surface is unchanged.
- Reducing response payload (consumers depending on a field).
- Changing the **shape** of an error (consumers parsing the message).
- Changing the order of items in a paginated response.

Deprecation:

- Mark deprecated at version N. Remove at N+1 major. One full major window for migration.
- Emit a deprecation warning at runtime (log + response header), not just in docs.
- Document the **migration path** in CHANGELOG, not just release notes.
- If you must break in patch (CVE, data corruption), say so prominently and tag the release.

## Observability Baseline

Every production service must expose enough evidence to answer its critical
operational and reliability questions. Select logs, metrics, traces, and
profiles by purpose rather than requiring every signal mechanically.

- Use structured events with bounded fields, stable names, redaction, and
  propagated trace context.
- Use metrics for user-visible outcomes, rates, errors, latency distributions,
  saturation, and bounded resource budgets.
- Use traces for cross-service and asynchronous paths where request-level
  causality or latency matters.
- Keep required security audit events separate when integrity, access,
  completeness, or retention differs from application logging.
- Bound telemetry volume, cardinality, queues, retries, retention, and cost.

For deeper guidance, use the observability skill
(`${HANDBOOK_ROOT}/skills/observability/SKILL.md`), the Go rule
(`${HANDBOOK_ROOT}/rules/210-go.mdc`) for Go logging integration, and the Zero
Trust rule (`${HANDBOOK_ROOT}/rules/316-zero-trust.mdc`) for append-only audit
requirements.

## Testing Baseline

The cheapest test catches the most bugs. The expensive test catches the few that matter.

- Pyramid shape: many unit, fewer integration, fewer still e2e.
- Test the **contract** (inputs → outputs, public surface), not the implementation (private internals will refactor).
- Every bug fix gets one regression test before the fix lands. Otherwise it returns.
- Tests need to fail before they pass. Write a failing test first whenever the change is non-trivial.
- Determinism matters. Tests that pass 99% of the time block CI 1% of the time.

For framework-specific patterns: `rules/300-testing.mdc` and the `security-testing` skill (OWASP test patterns, taint analysis, DAST validation).

## Self-Validation Checklist

Before delivering code or feedback:

- [ ] Addresses the actual problem
- [ ] Simplest viable solution
- [ ] No new bugs introduced
- [ ] Working code examples
- [ ] Clear explanations (the "why")
- [ ] Appropriate scope
- [ ] Preserves existing code
- [ ] Evidence-based recommendations

## Security Checklist

- [ ] No hardcoded secrets, API keys, passwords
- [ ] Secrets not logged or exposed in errors
- [ ] Dependencies scanned for CVEs
- [ ] OWASP Top 10 considered
- [ ] Input validation and sanitization
- [ ] Principle of least privilege applied

## Git & Version Control

Use the dedicated Git workflow skill (`${HANDBOOK_ROOT}/skills/git-workflow/SKILL.md`) for commit standards, branches, worktrees, signing, recovery, and remote synchronization.

## Quick Reference: Language Best Practices

| Language | Key Practices |
|----------|--------------|
| Python | Type hints, PEP 8, context managers, prefer stdlib |
| Go | Handle all errors, use `defer`, small interfaces |
| JS/TS | async/await, destructuring, strict mode |
| Bash | `set -euo pipefail`, quote variables, use functions |
| Docker | Multi-stage builds, non-root user, pinned versions |

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry
