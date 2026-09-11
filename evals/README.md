# Agent Skills Evaluations

This directory contains the vendor-neutral evaluation harness for the handbook's Agent Skills. It validates every skill and compares selected tasks with and without a skill through an external agent adapter.

The eval files follow the portable Agent Skills conventions documented by [agentskills.io](https://agentskills.io/skill-creation/evaluating-skills): each evaluated skill owns an `evals/evals.json` file with prompts, expected behavior, and optional fixtures. The local `checks` field is a documented extension for deterministic scoring.

## What the Harness Measures

- Skill metadata and directory-name correctness
- Eval schema and fixture integrity
- Deterministic output and artifact requirements
- With-skill pass rate versus the same baseline cases without the skill
- Paired win rate, median/p95 duration, and optional adapter-reported token/cost usage
- Observed skill activation when an agent runtime emits a `skill_loaded` event

The harness does not treat answer similarity, self-report, or reading `SKILL.md` as proof that a skill loaded. Automatic activation is runtime-specific and requires an authoritative runtime event. Cursor's current SDK does not expose that event, so Cursor benchmarks report `activation_telemetry_supported: false` and `activation_rate: null` while still measuring behavioral lift.

## Coverage

The harness currently discovers 32 behavioral suites across 54 skills. The [root README](../README.md#skill-evaluation) contains the authoritative suite inventory.

Coverage is intentionally risk-driven rather than uniform. Current suites emphasize security boundaries, identity, API and data contracts, infrastructure behavior, runtime correctness, reliability, and documentation artifacts. Skills without suites still receive metadata and schema validation.

The fixtures contain only synthetic, public-safe examples. Do not add customer data, production configuration, credentials, private incident details, or proprietary source code.

## Requirements

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/) for Python and development-tool management
- No package dependencies for deterministic validation
- The optional `eval` dependency group for Cursor SDK model-backed runs
- An executable adapter only for model-backed runs

## Validate Skills and Evals

Run the dependency-free checks used in pull-request CI:

```bash
uv run python -m evals.skill_eval validate
uv run python -m unittest discover -s evals/tests -v
```

Validation covers all immediate directories under [`skills/`](../skills/), including skills that do not yet have an eval suite.

## Eval File Contract

Each evaluated skill contains:

```text
skills/<skill-name>/
├── SKILL.md
└── evals/
    ├── evals.json
    └── fixtures/
```

The JSON shape is:

```json
{
  "skill_name": "sample-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "Perform the task.",
      "expected_output": "Describe the required behavior.",
      "assertions": ["The response performs the required behavior."],
      "files": ["evals/fixtures/input.txt"],
      "checks": [
        {
          "id": "required-behavior",
          "type": "contains",
          "value": "required phrase"
        }
      ]
    }
  ]
}
```

Fixture paths are relative to the skill root, matching the published convention. Standard `assertions` are preserved as human or judge rubrics. The local `checks` extension is optional and supports:

- `contains`: output contains one value
- `contains_all`: output contains every listed value
- `contains_any`: output contains at least one listed value
- `not_contains`: output excludes one value
- `regex`: output matches a Python regular expression
- `not_regex`: output does not match a Python regular expression
- `file_exists`: the adapter created a workspace-relative file
- `loaded_skill`: adapter events prove that a named skill loaded

Checks are case-insensitive by default. Set `"case_sensitive": true` when exact casing is behaviorally important. Set `"required": false` for diagnostic checks that should not fail a run.

Deterministic phrase checks are intentionally narrow. Use multiple behavioral cases instead of encoding prose style. `expected_output` and `assertions` remain grader-side rubrics and are never sent to the execution adapter.

Portable assertion-only suites pass schema validation, but this harness will not execute them without deterministic `checks`. Assertions need a future judge adapter; treating an ungraded assertion as passed would produce misleading results.

## Adapter Protocol

The runner invokes an executable directly with `shell=False`. The executable reads one request object from standard input and writes one response object to standard output. Diagnostics belong on standard error.

Request:

```json
{
  "protocol_version": 1,
  "mode": "with_skill",
  "skill": {
    "name": "sample-skill",
    "path": "/temporary/workspace/skills/sample-skill"
  },
  "prompt": "Perform the task.",
  "files": [
    {
      "path": "inputs/evals/fixtures/input.txt",
      "sha256": "..."
    }
  ],
  "workspace": "/temporary/workspace"
}
```

For `without_skill`, `skill` is `null`. Both modes receive fresh workspaces containing byte-identical fixtures. The adapter must not reuse conversation state between requests.

Response:

```json
{
  "output": "Final agent response",
  "events": [
    {
      "type": "skill_loaded",
      "name": "sample-skill"
    }
  ],
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 350,
    "cost_usd": 0.01
  }
}
```

Only `output` is required. `events` and `usage` may be empty. Usage values must be numeric. Events accept only `type` and optional `name`. Unknown response or event fields are rejected so adapters cannot accidentally persist hidden traces or undocumented data.

Adapters that cannot observe activation may emit `{"type":"activation_telemetry_unavailable","name":"<runtime>"}` for diagnostic clarity. This event does not satisfy `loaded_skill` and does not produce an activation rate.

An adapter is responsible for:

1. Starting a clean agent session.
2. Exposing the temporary workspace to the agent.
3. Installing or explicitly loading the supplied skill only in `with_skill` mode.
4. Capturing the final output and real activation events.
5. Returning no credentials, hidden prompts, or private chain-of-thought.

Do not implement adapters by concatenating untrusted input into a shell command. Pass arguments as an array and keep shell interpretation disabled.

## Run Model-Backed Comparisons

```bash
uv run python -m evals.skill_eval run \
  --adapter /absolute/path/to/agent-adapter \
  --skill core-engineering \
  --skill iam-security-advisor \
  --iterations 1 \
  --timeout-seconds 120 \
  --minimum-lift 0.1
```

Adapter arguments can be passed without a shell:

```bash
uv run python -m evals.skill_eval run \
  --adapter /usr/bin/python3 \
  --adapter-arg /absolute/path/to/adapter.py \
  --skill cloudflare-waf-author
```

### Cursor SDK adapter

The repository adapter uses a fresh local agent, project-only settings, and the read-only `read`, `grep`, `glob`, and `ls` tool allowlist. It stages the with-skill copy under `.cursor/skills/<name>` and leaves the baseline workspace without that skill.

```bash
export CURSOR_API_KEY="set-outside-shell-history"
export CURSOR_EVAL_MODEL="a-model-id-returned-for-your-account"

uv run --group eval python -m evals.skill_eval run \
  --adapter /usr/bin/env \
  --adapter-arg python3 \
  --adapter-arg "$PWD/evals/adapters/cursor_sdk_adapter.py" \
  --skill core-engineering \
  --iterations 1
```

Use at least three iterations before treating lift as stable. The adapter reports token usage and settled billed cost when available. It deliberately emits no `skill_loaded` event because the Cursor SDK does not provide authoritative automatic skill or rule activation telemetry.

The command exits:

- `0` when every required with-skill check passes and any configured minimum lift is met
- `1` when a with-skill behavior check fails
- `2` for invalid configuration, adapter errors, or timeouts

A positive lift is useful evidence, but it is not sufficient by itself. Without `--minimum-lift`, required with-skill behavior is the exit-code gate and zero or negative lift produces a warning. Review failed checks, outputs, and artifacts before changing a skill.

## Artifacts

Artifacts are written under the ignored path `tmp/skills-eval/<run-id>/`:

```text
tmp/skills-eval/<run-id>/<skill>/
├── benchmark.json
└── iteration-1/
    └── eval-1/
        ├── case.json
        ├── with_skill/
        │   ├── grading.json
        │   ├── output.txt
        │   ├── response.json
        │   └── timing.json
        └── without_skill/
            └── ...
```

Common bearer tokens, secret assignments, sensitive dictionary keys, and private-key blocks are redacted before persistence. Redaction is defense in depth, not permission to use sensitive inputs. Keep artifacts local or upload them with restricted access and short retention.

## Cost and Safety Limits

The defaults are:

- one iteration
- 120-second timeout per adapter call
- 1 MiB enforced limit for standard output and standard error each, captured in temporary files rather than process memory
- sequential execution
- no paid or credentialed model runs in pull-request CI

Use at least three iterations before treating a variable model result as a regression. Agent adapters should additionally enforce token, tool-call, concurrency, and suite-cost budgets supported by their runtime.

External side effects are outside eval scope. Adapters must use isolated fixtures and read-only or mocked tools. Never point a skill eval at production cloud accounts, databases, Git remotes, or customer systems.

## Adding Another Skill

1. Identify behavior the skill should improve over the baseline.
2. Add positive, near-miss, and safe-stop cases.
3. Prefer deterministic assertions for security boundaries, required artifacts, and prohibited behavior.
4. Keep fixtures synthetic and identical across modes.
5. Run validation and at least one model-backed comparison.
6. Review pass-rate lift, output quality, token use, and latency.
7. Add runtime-specific trigger cases only when the adapter can report actual skill loads.

Expand beyond the pilots after the harness produces stable, actionable findings without excessive false failures.
