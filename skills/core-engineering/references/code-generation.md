# Code Generation Patterns

## Generation Approach

1. **Handle ambiguity proactively** - If scope is ambiguous, proceed with minimal **Assumptions** and list ≤3 targeted questions that could change the approach materially.
2. **Design clean architecture** - Easy to test, maintain, and extend.
3. **Provide complete, runnable code** - No TODOs, placeholders, or incomplete sections.
4. **Include practical examples** - Usage examples or basic test cases.
5. **Document appropriately** - Inline comments for complex logic only; clear function/class docs.

## What to Include

- **Error handling:** Validate inputs, handle edge cases, fail fast with clear messages
- **Logging:** Key operations and errors (don't over-log); follow the Logging Policy
- **Type hints/annotations:** Where language supports them
- **Configuration:** Externalize configuration values (no hardcoded secrets)
- **Documentation:** Brief module/function docstrings explaining purpose and parameters

## What NOT to Include (Unless Requested)

- Over-engineered abstractions for simple problems
- Premature optimization
- Extensive test suites (provide 1-2 examples instead)
- Complex frameworks when stdlib suffices
- Features not in requirements
- Generic boilerplate text or “best practices” not tied to the task (“AI slop”)

## Assumption Format

When making assumptions, document them clearly:

```
**Assumption:** [Clear statement of what you're assuming]
**Impact if wrong:** [What would need to change]
**Validating question:** [Specific question to confirm/reject assumption]
```

## Code Structure Template

```python
"""
Brief module description and purpose.
"""
# Imports (stdlib, third-party, local)

# Constants and configuration

# Main implementation (classes/functions)

# Helper functions

# Entry point or usage example (if applicable)
```

## Response Format for Code Generation

```markdown
[Complete, runnable code with inline documentation]

## Assumptions Made
[List any assumptions with validation questions]

## Usage Example
[How to use the code]

## Key Implementation Notes
[Any important decisions or considerations]
```

## Response Format for Questions/Clarifications

```markdown
I'll proceed with these assumptions:
**Assumption:** [Statement]
**Impact if wrong:** [What changes]

To refine the solution, clarify:
1. [High-impact question]
2. [High-impact question]
3. [High-impact question]

[Provide initial solution based on assumptions]
```

## Clarifying Questions Framework

When asking questions (limit to ≤3), prioritize those that would most change the solution:

**Scope & Constraints:**

- Essential vs nice-to-have
- Performance/scale/resource constraints
- Usage pattern & volume

**Technical Context:**

- Existing stack
- Integrations/dependencies
- Deployment target (local/cloud/container)

**Quality & Risk:**

- Risk tolerance
- Compliance/security needs
- Appropriate testing level

## Best Practices by Language

### Python (target 3.12+)

- Use type hints and PEP 8
- Prefer `functools.cache`/`lru_cache`, `dataclasses`, modern `typing`
- Use context managers for resources (`with` statements)
- Prefer stdlib over adding dependencies

### Go

- Handle all errors explicitly
- Use `defer` for cleanup
- Follow Effective Go; keep interfaces small
- Run `govulncheck` in CI

### JavaScript/TypeScript

- Use async/await; avoid callback pyramids
- Prefer destructuring; `const` by default, `let` when needed
- Enable strict mode (`"strict": true` in TS)
- ESLint with zero warnings policy

### Bash

- Use `set -euo pipefail` for strict error handling
- Use `shfmt` for formatting and `shellcheck` for linting
- Use functions for reusable code blocks
- Quote variables: `"${var}"` not `$var`

### Docker

- Use multi-stage builds to reduce image size
- Run as non-root user
- Pin base image versions (`python:3.14.0-slim`, not `python:latest`)
- Scan images for vulnerabilities

### AWS (boto3/Lambda)

- Create boto3 clients in global scope (outside Lambda handler)
- Use `botocore.config.Config` for retry/timeout settings
- Handle specific `ClientError` codes, not generic exceptions
- Use paginators for large result sets
- Never log AWS credentials or session tokens

### Terraform/CloudFormation

- **Terraform:** `snake_case` for resource, variable, output names
- **CloudFormation:** Hungarian notation (parameters `p*`, resources `r*`)
- Use remote state with locking
- Tag all resources with `owner`, `environment`, `cost_center`
- Never commit `.terraform/` or `*.tfstate` files
