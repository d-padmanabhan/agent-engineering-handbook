# Agent Engineering Handbook

> Rules, Agent Skills, commands, hooks, evaluation tooling, and an MCP server for AI-assisted software engineering.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/license/MIT)

This repository contains 52 Cursor rule files, 54 Agent Skills, 19 custom Cursor commands, and 32 behavioral eval suites covering software design, languages, cloud platforms, infrastructure, security, identity, data, AI systems, and documentation.

The content is organized for progressive disclosure:

- **Rules** provide concise mandatory gates that apply automatically, by file scope, or when selected.
- **Skills** provide detailed workflows, examples, references, and verification procedures.
- **Commands** provide manually invoked Cursor workflows.
- **Hooks** provide deterministic checks around agent activity.
- **Evals** measure whether skills improve behavior.
- **The MCP server** exposes handbook rules through the Model Context Protocol.

## Contents

- [Start Here](#start-here)
- [Rules and Skills](#rules-and-skills)
- [Install for Cursor](#install-for-cursor)
- [Custom Commands](#custom-commands)
- [Hooks](#hooks)
- [MCP Server](#mcp-server)
- [Rule Highlights](#rule-highlights)
- [Skill Catalog](#skill-catalog)
- [Skill Evaluation](#skill-evaluation)
- [Repository Utilities](#repository-utilities)
- [Contributing](#contributing)
- [License](#license)

## Start Here

1. Clone or update this repository.
2. Resolve the checkout's absolute path.
3. Link each handbook surface into its matching Cursor user directory.
4. Run the repository's setup or validation commands.
5. Keep project-specific exceptions in the target repository rather than modifying shared handbook policy.

From the handbook checkout, resolve the absolute source path:

```bash
cd "/absolute/path/to/agent-engineering-handbook"
export HANDBOOK_ROOT="$(pwd -P)"
mkdir -p "${HOME}/.cursor"
```

On a new Cursor installation, link each repository directory to the corresponding Cursor user path:

```bash
ln -s "${HANDBOOK_ROOT}/rules" "${HOME}/.cursor/rules"
ln -s "${HANDBOOK_ROOT}/skills" "${HOME}/.cursor/skills"
ln -s "${HANDBOOK_ROOT}/commands" "${HOME}/.cursor/commands"
ln -s "${HANDBOOK_ROOT}" "${HOME}/.cursor/agent-engineering-handbook"
```

The first three links make rules, skills, and commands discoverable in their actual Cursor home locations. The final stable-root link supports portable `${HANDBOOK_ROOT}/...` references used inside handbook content. Before running these commands, confirm that none of the destination paths already contains user configuration. Use the merge-safe installation below when a destination already exists.

## Rules and Skills

Cursor project rules live under `.cursor/rules/`. Current rule activation fields are `description`, `globs`, and `alwaysApply`. This repository also uses `title` and numeric `priority` as catalog metadata; do not assume Cursor uses them for activation order.

Cursor project skills live in `.cursor/skills/` or `.agents/skills/`; user skills live in `~/.cursor/skills/` or `~/.agents/skills/`. Cursor also discovers compatible skill directories used by Claude Code and Codex. This repository's portable skill contract requires `name` and `description`.

| Concern | Rules | Skills |
| --- | --- | --- |
| Purpose | Mandatory constraints and routing | Workflows, examples, references, and procedures |
| Typical location | `.cursor/rules/*.mdc` | `.cursor/skills/*/SKILL.md` or `.agents/skills/*/SKILL.md` |
| Selection | `alwaysApply`, `globs`, description-based selection, or explicit use | Automatic selection or `/skill-name` |
| Context cost | Keep concise, especially when always applied | Load only when the task matches |
| Repository policy | One canonical owner for each mandatory gate | Route to the owning rule instead of duplicating policy |

Other supported instruction surfaces include:

- root or nested `AGENTS.md` files;
- local User Rules under `~/.cursor/rules`;
- account-synced User Rules configured in Cursor;
- Team Rules managed through the Cursor dashboard.

The legacy `.cursorrules` file is still recognized during migration but is marked for deprecation. Do not use the undocumented `rulesDirectory` or `rules:` YAML shapes previously shown by this README. Migrate legacy content to `.cursor/rules/*.mdc`, `AGENTS.md`, or Agent Skills.

Current Cursor references:

- [Rules](https://cursor.com/docs/rules.md)
- [Agent Skills](https://cursor.com/docs/skills.md)
- [Customize Cursor](https://cursor.com/docs/customize-cursor.md)

## Install for Cursor

### Merge-Safe User Installation

If `~/.cursor/rules`, `~/.cursor/skills`, or `~/.cursor/commands` already exists, preserve it and link individual handbook entries:

```bash
cd "/absolute/path/to/agent-engineering-handbook"
export HANDBOOK_ROOT="$(pwd -P)"
mkdir -p "${HOME}/.cursor/rules" \
  "${HOME}/.cursor/skills" \
  "${HOME}/.cursor/commands"
shopt -s nullglob

for source in "${HANDBOOK_ROOT}"/rules/*.mdc; do
  destination="${HOME}/.cursor/rules/$(basename "${source}")"
  test -e "${destination}" || test -L "${destination}" || ln -s "${source}" "${destination}"
done

for source in "${HANDBOOK_ROOT}"/skills/*; do
  if [[ ! -f "${source}/SKILL.md" ]]; then
    continue
  fi
  destination="${HOME}/.cursor/skills/$(basename "${source}")"
  test -e "${destination}" || test -L "${destination}" || ln -s "${source}" "${destination}"
done

for source in "${HANDBOOK_ROOT}"/commands/*.md; do
  if [[ "$(basename "${source}")" == "README.md" ]]; then
    continue
  fi
  destination="${HOME}/.cursor/commands/$(basename "${source}")"
  test -e "${destination}" || test -L "${destination}" || ln -s "${source}" "${destination}"
done
```

Existing destinations are left unchanged. Review any skipped name collision manually; do not overwrite unrelated user configuration.

### Bootstrap a Project Workspace

The setup script creates workspace context files and can link the repository's rule directory into a target workspace:

```bash
"${HANDBOOK_ROOT}/setup-workspace.sh" \
  --symlink-all \
  --lightweight \
  --ensure-gitignore \
  .
```

This symlink layout is a handbook convention for local workspaces. Cursor documentation explicitly supports skill discovery through symlinked directories, but does not guarantee every rule-symlink topology. If rule discovery does not work in the installed Cursor version, use the copy fallback below.

### Option 2: Copy Rules into a Project

Copy all rules:

```bash
mkdir -p .cursor/rules
cp "${HANDBOOK_ROOT}/rules/"*.mdc .cursor/rules/
```

Or copy only the rules required by the project:

```bash
mkdir -p .cursor/rules
cp "${HANDBOOK_ROOT}/rules/100-core.mdc" .cursor/rules/
cp "${HANDBOOK_ROOT}/rules/200-python.mdc" .cursor/rules/
cp "${HANDBOOK_ROOT}/rules/310-security.mdc" .cursor/rules/
```

Copy the files again when the handbook changes, or automate a reviewed synchronization process.

### Install Skills

The Cursor CLI changelog documents skill discovery through symlinked directories:

```bash
mkdir -p .cursor
ln -s "${HANDBOOK_ROOT}/skills" .cursor/skills
```

Copying is the portable fallback:

```bash
mkdir -p .cursor/skills
cp -R "${HANDBOOK_ROOT}/skills/." .cursor/skills/
```

For Codex-native project discovery, use `.agents/skills/`. Claude Code commonly uses `.claude/skills/`. Verify client-specific installation and precedence against current vendor documentation.

### Create a Project Rule

Use supported file-scoped frontmatter:

```markdown
---
description: Python API conventions for this project
globs:
  - "src/api/**/*.py"
alwaysApply: false
---

# Python API Conventions

- Validate request data before policy or business logic.
- Keep project-specific exceptions narrow and documented.
```

Place the file under `.cursor/rules/`, for example `.cursor/rules/python-api.mdc`.

## Custom Commands

The `commands/` directory contains 19 Cursor custom command files. Copy them only when command-based workflows are desired:

```bash
mkdir -p .cursor
cp -R "${HANDBOOK_ROOT}/commands" .cursor/commands
```

Cursor still supports `.cursor/commands`, but reusable commands can be migrated to manually invoked Agent Skills with `/migrate-to-skills`. Names such as `/plan` and `/review` can collide with Cursor built-ins; confirm the selected command in the UI or rename the local file.

| Command | Purpose |
| --- | --- |
| `/init` | Initialize work and classify complexity |
| `/plan` | Design an implementation before editing |
| `/creative` | Explore alternatives for complex design decisions |
| `/qa` | Validate dependencies, configuration, and environment |
| `/build` | Implement an approved plan |
| `/review` | Review completed implementation |
| `/self-review` | Review local branch changes against the base |
| `/quick-review` | Run a focused critical-issue review |
| `/check-progress` | Fix clear issues and summarize progress |
| `/code-commit` | Run the controlled commit and push workflow with approval gates |
| `/archive` | Record lessons and archive completed complex work |
| `/aws` | Apply AWS guidance |
| `/bash` | Apply Bash guidance |
| `/gha` | Apply GitHub Actions guidance |
| `/go` | Apply Go guidance |
| `/javascript` | Apply JavaScript and TypeScript guidance |
| `/markdown` | Apply Markdown guidance |
| `/python` | Apply Python guidance |
| `/terraform` | Apply Terraform guidance |

Typical workflow:

```text
Simple:  /init -> /build -> /review
Planned: /init -> /plan -> /qa -> /build -> /review
Complex: /init -> /plan -> /creative -> /qa -> /build -> /review -> /archive
```

See the [command reference](commands/README.md) for installation details and command-specific behavior.

## Hooks

Cursor hook configuration locations include:

- project hooks: `.cursor/hooks.json`;
- user hooks: `~/.cursor/hooks.json`.

Install the optional local hook pack:

```bash
./scripts/cursor-hooks-install.sh --project .
```

The hook pack gates selected destructive shell behavior and records bounded audit events. Review the generated configuration and scripts before enabling them in another repository.

See the [hooks guide](docs/HOOKS.md) and [Cursor hook pack](hooks/cursor/).

## MCP Server

The repository includes a local stdio MCP server that exposes handbook rules. Build and link it:

```bash
cd mcp/cursor-rules-mcp
npm install
npm run build
npm link
```

Configure Cursor in `.cursor/mcp.json` or `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agent-engineering-handbook": {
      "command": "cursor-rules-mcp",
      "env": {
        "CURSOR_RULES_PATH": "/absolute/path/to/agent-engineering-handbook/rules"
      }
    }
  }
}
```

Claude Desktop uses the same server definition inside `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agent-engineering-handbook": {
      "command": "cursor-rules-mcp",
      "env": {
        "CURSOR_RULES_PATH": "/absolute/path/to/agent-engineering-handbook/rules"
      }
    }
  }
}
```

The server currently uses a maintained topic map rather than automatic filesystem discovery. Update and test that map when rules are added or renamed.

See the [MCP server reference](mcp/cursor-rules-mcp/README.md) for tools, development commands, and troubleshooting.

## Rule Highlights

The repository currently contains 52 `.mdc` rule files. The following list highlights common entry points; the [rule index](rules/INDEX.md) is authoritative.

### Workflow and Core Engineering

- [Workflow](rules/010-workflow.mdc)
- [Context engineering](rules/015-context-engineering.mdc)
- [Agent audit](rules/020-agent-audit.mdc)
- [Core engineering](rules/100-core.mdc)
- [Configuration](rules/110-configuration.mdc)
- [Utilities](rules/120-utilities.mdc)
- [Git](rules/130-git.mdc)

### Languages and Application Design

- [Bash](rules/140-bash.mdc)
- [Python](rules/200-python.mdc)
- [Go](rules/210-go.mdc)
- [Rust](rules/220-rust.mdc)
- [JavaScript and TypeScript](rules/225-javascript-typescript.mdc)
- [Frontend](rules/260-frontend.mdc)
- [API design](rules/320-api-design.mdc)
- [Networking](rules/325-networking.mdc)
- [Observability](rules/330-observability.mdc), with detailed workflows in the [observability skill](skills/observability/)

### Security and Identity

- [Security](rules/310-security.mdc)
- [IAM](rules/315-iam.mdc)
- [Zero Trust](rules/316-zero-trust.mdc)
- [Okta](rules/317-okta.mdc)
- [Workload identity](rules/318-workload-identity.mdc)
- [AWS IAM](rules/412-aws-iam.mdc)

### Cloud and Infrastructure

- [GitHub Actions](rules/160-github-actions.mdc)
- [CloudFormation](rules/170-cloudformation.mdc)
- [Terraform](rules/180-terraform.mdc)
- [Ansible](rules/190-ansible.mdc)
- [Cloudflare](rules/400-cloudflare.mdc)
- [AWS](rules/410-aws.mdc)
- [Google Cloud](rules/420-gcp.mdc)
- [Azure](rules/430-azure.mdc)
- [Docker](rules/440-docker.mdc)
- [Kubernetes](rules/450-kubernetes.mdc)
- [Helm](rules/460-helm.mdc)

### Data, AI, and Documentation

- [PostgreSQL](rules/470-postgresql.mdc)
- [SQL](rules/475-sql.mdc)
- [Data engineering](rules/480-data-engineering.mdc)
- [Databricks](rules/481-databricks.mdc)
- [Snowflake](rules/482-snowflake.mdc)
- [Kafka](rules/483-kafka.mdc)
- [Teradata](rules/484-teradata.mdc)
- [AI and machine learning](rules/500-ai-ml.mdc)
- [MCP servers](rules/510-mcp-servers.mdc)
- [Markdown and generated PNG diagrams](rules/800-markdown.mdc)
- [Documentation](rules/810-documentation.mdc)
- [Open source](rules/820-open-source.mdc)

## Skill Catalog

The repository currently contains 54 skill packages. Each directory listed below contains a `SKILL.md`.

### Engineering and Languages

- [Agent workflow](skills/agent-workflow/)
- [API design](skills/api-design/)
- [Bash shell scripting](skills/bash-shell-scripting/)
- [Core engineering](skills/core-engineering/)
- [Distributed transactions](skills/distributed-transactions/)
- [Domain-Driven Design](skills/domain-driven-design/)
- [Frontend engineering](skills/frontend-engineering/)
- [Git workflow](skills/git-workflow/)
- [Go and Rust systems](skills/go-rust-systems/)
- [Networking and transport](skills/networking-transport/)
- [Observability](skills/observability/)
- [Python development](skills/python-development/)
- [Scripting automation](skills/scripting-automation/)
- [Service resilience](skills/service-resilience/)
- [System design](skills/system-design/)
- [TypeScript and JavaScript](skills/typescript-javascript/)

### Security and Identity

- [AWS IAM](skills/aws-iam/)
- [Codebase security audit](skills/codebase-security-audit/)
- [IAM security advisor](skills/iam-security-advisor/)
- [Okta](skills/okta/)
- [Security testing](skills/security-testing/)
- [Workload identity](skills/workload-identity/)
- [Zero Trust](skills/zero-trust/)

### Cloud, Infrastructure, and Delivery

- [Agents SDK](skills/agents-sdk/)
- [CI/CD with GitHub Actions](skills/cicd-github-actions/)
- [Cloud platforms](skills/cloud-platforms/)
- [Cloudflare](skills/cloudflare/)
- [Cloudflare email service](skills/cloudflare-email-service/)
- [Cloudflare WAF authoring](skills/cloudflare-waf-author/)
- [Cloudflare Workers authoring](skills/cloudflare-workers-author/)
- [Containers and orchestration](skills/containers-orchestration/)
- [Durable Objects](skills/durable-objects/)
- [Infrastructure as Code](skills/infrastructure-iac/)
- [Kubernetes and containers](skills/kubernetes-containers/)
- [Kubernetes operator development](skills/kubernetes-operator-development/)
- [Sandbox SDK](skills/sandbox-sdk/)
- [Workers best practices](skills/workers-best-practices/)
- [Wrangler](skills/wrangler/)

### Data Engineering

- [Data engineering](skills/data-engineering/)
- [Databricks](skills/databricks/)
- [PostgreSQL](skills/database-postgresql/)
- [Snowflake](skills/snowflake/)

### AI and Analysis

- [MCP development](skills/mcp-development/)
- [Memory architecture](skills/memory-architecture/)
- [Multi-perspective review](skills/multi-perspective-review/)
- [Web research knowledge-base refresh](skills/web-research-kb-refresh/)

### Documentation and Artifacts

- [Documentation standards and generated PNG diagrams](skills/documentation-standards/)
- [PDF export](skills/pdf-export/)
- [React Flow architecture diagrams](skills/reactflow-architecture-diagrams/)
- [Single-file dashboard](skills/single-file-dashboard/)
- [Web performance](skills/web-perf/)

### Skill Maintenance

- [Independent verification](skills/independent-verification/)
- [Skills composition](skills/skills-composition/)
- [Skills continuous improvement](skills/skills-continuous-improvement/)

## Skill Evaluation

The dependency-free [Agent Skills eval harness](evals/) validates all skill metadata and the 32 available behavioral suites. Model-backed comparisons use an external command adapter; pull-request CI runs deterministic validation and unit tests without model credentials.

Current behavioral suites:

- [Agent workflow](skills/agent-workflow/evals/evals.json)
- [API design](skills/api-design/evals/evals.json)
- [AWS IAM](skills/aws-iam/evals/evals.json)
- [Bash shell scripting](skills/bash-shell-scripting/evals/evals.json)
- [CI/CD with GitHub Actions](skills/cicd-github-actions/evals/evals.json)
- [Cloudflare WAF authoring](skills/cloudflare-waf-author/evals/evals.json)
- [Cloudflare Workers authoring](skills/cloudflare-workers-author/evals/evals.json)
- [Containers and orchestration](skills/containers-orchestration/evals/evals.json)
- [Core engineering](skills/core-engineering/evals/evals.json)
- [Data engineering](skills/data-engineering/evals/evals.json)
- [PostgreSQL](skills/database-postgresql/evals/evals.json)
- [Documentation standards](skills/documentation-standards/evals/evals.json)
- [Domain-Driven Design](skills/domain-driven-design/evals/evals.json)
- [Distributed transactions](skills/distributed-transactions/evals/evals.json)
- [Git workflow](skills/git-workflow/evals/evals.json)
- [Go and Rust systems](skills/go-rust-systems/evals/evals.json)
- [IAM security advisor](skills/iam-security-advisor/evals/evals.json)
- [Independent verification](skills/independent-verification/evals/evals.json)
- [Kubernetes and containers](skills/kubernetes-containers/evals/evals.json)
- [Kubernetes operator development](skills/kubernetes-operator-development/evals/evals.json)
- [Memory architecture](skills/memory-architecture/evals/evals.json)
- [Networking and transport](skills/networking-transport/evals/evals.json)
- [Observability](skills/observability/evals/evals.json)
- [Okta](skills/okta/evals/evals.json)
- [Python development](skills/python-development/evals/evals.json)
- [Scripting automation](skills/scripting-automation/evals/evals.json)
- [Security testing](skills/security-testing/evals/evals.json)
- [Service resilience](skills/service-resilience/evals/evals.json)
- [System design](skills/system-design/evals/evals.json)
- [TypeScript and JavaScript](skills/typescript-javascript/evals/evals.json)
- [Workload identity](skills/workload-identity/evals/evals.json)
- [Zero Trust](skills/zero-trust/evals/evals.json)

Run deterministic validation:

```bash
uv run python -m evals.skill_eval validate
uv run python -m unittest discover -s evals/tests -v
```

See the [eval harness documentation](evals/README.md) for adapter limits, paired comparisons, output redaction, and artifact handling.

## Repository Utilities

Preview and run Cursor cache cleanup:

```bash
./scripts/cursor-maintenance.sh --dry-run
./scripts/cursor-maintenance.sh
```

Run repository checks:

```bash
pre-commit run --all-files
uv run python -m evals.skill_eval validate
uv run python -m unittest discover -s evals/tests -v
```

Current runtime and toolchain requirements are owned by the relevant rule or skill and should be verified against the deployment target before adoption. Do not treat a version number in this README as an evergreen recommendation.

## Contributing

Contributions should keep mandatory rules concise, place procedures and examples in skills, update affected evals, and preserve safe runnable examples. See the [contribution guide](.github/CONTRIBUTING.md).

## Acknowledgments

The repository drew ideas from:

- [AI Developer Guide](https://github.com/dwmkerr/ai-developer-guide) for workflow and context-management patterns;
- [Cursor Memory Bank](https://github.com/vanzan01/cursor-memory-bank) for progressive context files;
- [Shellwright](https://github.com/dwmkerr/shellwright) for terminal automation and PTY-oriented MCP patterns.

The command-based workflow was suggested by [@DaKaZ](https://github.com/DaKaZ).

Related references:

- [Advanced Context Engineering for Coding Agents](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- [Google Style Guides](https://github.com/google/styleguide)
- [Uber Go Style Guide](https://github.com/uber-go/guide)

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
