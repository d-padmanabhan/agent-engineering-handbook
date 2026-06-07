---
name: skills-continuous-improvement
description: Biweekly maintenance workflow for improving Agent Skills and matching rules in this handbook. Use when the user asks to review, refresh, audit, improve, harden, or update skills/rules, or when doing a scheduled every-2-weeks quality pass over skills. Finds drift between rules and skills, stale examples, unsafe snippets, broken/clickability issues, duplicated guidance, and missing non-negotiables; applies high-confidence fixes and reports larger follow-ups.
---

# Skills Continuous Improvement

Use this skill for the recurring **two-week quality pass** over this repository's skills and the rules they pair with.

The goal is not churn. The goal is to keep the handbook current, safe, and useful for code generation.

## Cadence

Run every two weeks, or sooner when:

- A rule changes and its companion skill may now be stale.
- A new skill is added.
- A user reports that agents still generate weak code despite existing guidance.
- A vendor/runtime changes defaults, versions, APIs, or best practices.
- Pre-commit, lint, or security checks reveal repeated issues.

## Scope

Review both layers:

- **Rules** (`rules/*.mdc`) - concise non-negotiables and file-scoped policy.
- **Skills** (`skills/*/SKILL.md` plus one-level `references/*.md`) - workflow and examples.

Prioritize skills with paired rules first:

- [Python rule](../../rules/200-python.mdc) ↔ [Python skill](../python-development/)
- [Go rule](../../rules/210-go.mdc) ↔ [Go/Rust skill](../go-rust-systems/)
- [JavaScript rule](../../rules/230-javascript.mdc) / [TypeScript rule](../../rules/240-typescript.mdc) ↔ [TypeScript/JavaScript skill](../typescript-javascript/)
- [Bash rule](../../rules/140-bash.mdc) ↔ [Bash skill](../bash-shell-scripting/) and [scripting automation skill](../scripting-automation/)
- [Cloudflare rule](../../rules/400-cloudflare.mdc) / [Cloudflare Workers rule](../../rules/401-cloudflare-workers.mdc) / [Cloudflare WAF rule](../../rules/405-cloudflare-waf-rules.mdc) ↔ Cloudflare skills
- [Kubernetes rule](../../rules/450-kubernetes.mdc) / [Helm rule](../../rules/460-helm.mdc) ↔ [Kubernetes containers skill](../kubernetes-containers/)

## Review Workflow

### 1. Inventory

List changed or likely-stale areas:

```bash
git status --short
git log --oneline --since="2 weeks ago" -- rules skills
```

Then map rule/skill pairs manually. Do not assume every skill has a rule or every rule has a skill.

### 2. Drift Check

For each rule/skill pair, verify:

- Non-negotiables in the rule are mirrored in the skill summary.
- Skill examples do not contradict the rule.
- Reference files demonstrate the current preferred pattern.
- README skill index still lists new skills.
- Cross-links are clickable Markdown links, not backticked paths, when intended for navigation.

### 3. Unsafe Example Scan

Search for code examples that teach weak or outdated patterns.

Use targeted scans, not broad rewrites. Examples:

```bash
rg -n "context\\.TODO\\(|cfg, _|http\\.ListenAndServe\\(|FROM alpine:latest" rules skills
rg -n "JSON\\.parse\\([^\\n]+\\) as|await response\\.json\\(\\) as|skipLibCheck\\\": true" rules skills
rg -n "echo -e|echo .*\\| tee|for .* in \\$\\(|set -x\\s*$" rules skills
rg -n "privileged: true|hostPID: true|allowPrivilegeEscalation: true" rules skills
rg -n "python:3\\.1[0-3]|python-version: ['\\\"]3\\.1[0-3]" rules skills
```

Treat matches as findings only when the surrounding prose is **teaching** the pattern. Do not "fix" reject-list examples that intentionally show bad code.

### 4. Freshness Check

For fast-moving ecosystems, verify current docs before changing standards:

- Cloudflare Workers / Wrangler / Vitest pool workers
- GitHub Actions versions
- Python / Go / Node current runtime baselines
- Kubernetes Pod Security Standards and admission behavior
- AWS IAM / EKS / workload identity patterns

Use official docs or the repo's existing web-research workflow. Cite URLs in the commit message or PR summary when the update depends on current external facts.

### 5. Apply Only High-Confidence Fixes

Apply immediately when:

- An example contradicts an existing rule.
- A skill is missing a rule's non-negotiable.
- A stale version is clearly below the repo's stated baseline.
- A path intended for navigation is not clickable.
- A security-sensitive example is unsafe without being labeled as bad.

Do **not** apply broad rewrites when:

- The correct choice is architectural or context-dependent.
- The source docs are ambiguous.
- The change would churn many files without clear behavior improvement.
- A skill's scope may need product-owner input.

Capture those as TODOs instead.

### 6. Validation

Run targeted checks for touched files:

```bash
git diff --check
pre-commit run --files <changed-files>
```

If broad pre-commit is too large or noisy, run targeted hooks and clearly report any skipped checks.

## Output Report

End every pass with a short report:

```markdown
## Skills Continuous Improvement Report - YYYY-MM-DD

### Changed

- <file or skill>: <what changed and why>

### Findings Fixed

- <issue>: <fix>

### Deferred Follow-ups

- <follow-up>: <why deferred>

### Validation

- <checks run>
- <known residual warnings, if any>
```

## Guardrails

- Prefer small, reviewable commits grouped by domain.
- Do not "modernize" examples unless they conflict with current rules or current official docs.
- Preserve intentional BAD/GOOD examples; make the label clear instead of deleting the BAD example.
- Do not change unrelated user edits in a dirty tree.
- Do not add always-on behavior to skills. If guidance must always load, put the principle in a rule and keep the workflow in a skill.
