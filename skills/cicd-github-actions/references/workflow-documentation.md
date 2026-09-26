# Documenting GitHub Actions Workflows

Use this how-to when creating or reviewing workflow comments, names, inputs,
outputs, summaries, and operating notes.

## Workflow Header

Put the workflow `name:` first, followed immediately by the bordered
operational comment block. Keep the block current with the workflow.

```yaml
name: Deploy Application

# ================================================================
# Purpose: Deploys a previously tested release to a protected environment
#
# Triggers:
#   - Manual workflow dispatch for staging or production
#
# Required Secrets:
#   - None: cloud authentication uses OIDC
#
# Dependencies:
#   - Published release artifact
#   - Acme deployment API
#   - Production GitHub Environment approval
#   - Rollback runbook: docs/deployment-rollback.md
# ================================================================

run-name: Deploy ${{ inputs.version }} to ${{ inputs.environment }}
```

Document:

- purpose and scope;
- triggers and material path or branch conditions;
- required secret references, or an explicit `None`, never credential values;
- external services, artifacts, reusable workflows, or ordering dependencies;
- approval, manual intervention, rollback, recovery, and runbook requirements
  under `Dependencies`.

Do not repeat every YAML key in prose. A short CI workflow may need only two or
three comment lines. A production deployment usually needs the complete
operational block.

## Names

- Use a descriptive Title Case workflow `name:`.
- Use kebab-case workflow filenames.
- Give each job a human-readable `name:` when its identifier is insufficient.
- Name non-obvious steps by their outcome, such as `Validate release input` or
  `Verify deployed health`.
- Use `run-name:` when the event, ref, version, or environment materially helps
  operators distinguish runs.

Names must not include secrets or unnecessary sensitive identifiers.

## Reusable Interfaces

Document reusable workflow and action interfaces where they are declared:

```yaml
on:
  workflow_call:
    inputs:
      environment:
        description: Target GitHub Environment.
        required: true
        type: string
      version:
        description: Immutable release version to deploy.
        required: true
        type: string
    secrets:
      deployment-token:
        description: Short-lived broker token when OIDC is unavailable.
        required: false
    outputs:
      deployment-url:
        description: HTTPS URL verified by the deploy job.
        value: ${{ jobs.deploy.outputs.url }}
```

State defaults, accepted formats, side effects, and security expectations. Do
not use descriptions to compensate for missing schema validation.

## Comments Near Jobs and Steps

Add a nearby comment only when it explains a non-obvious constraint:

```yaml
jobs:
  deploy:
    name: Deploy to production

    # Queue production deploys. Cancelling an in-flight mutation can leave a
    # partial release that requires manual recovery.
    concurrency:
      group: deploy-production
      cancel-in-progress: false
```

Useful comments explain why a permission, timeout, concurrency group, cache
boundary, or unusual condition exists. Avoid comments such as `# Run tests`
above a step named `Run tests`.

## Summaries and Annotations

Use `GITHUB_STEP_SUMMARY` for concise operator or reviewer outcomes. Move
untrusted expressions through step-level environment variables before shell
use:

```yaml
- name: Write deployment summary
  if: always()
  env:
    TARGET_ENVIRONMENT: ${{ inputs.environment }}
    RELEASE_VERSION: ${{ inputs.version }}
    DEPLOYMENT_STATUS: ${{ job.status }}
  run: |
    {
      printf '## Deployment result\n\n'
      printf -- '- Environment: `%s`\n' "$TARGET_ENVIRONMENT"
      printf -- '- Version: `%s`\n' "$RELEASE_VERSION"
      printf -- '- Status: `%s`\n' "$DEPLOYMENT_STATUS"
    } >> "$GITHUB_STEP_SUMMARY"
```

Do not place secrets, raw environment dumps, customer data, or unrestricted
logs in summaries, annotations, artifacts, or pull-request comments.

## Review Checklist

- The bordered comment block immediately follows `name:`.
- The block uses `Purpose`, `Triggers`, `Required Secrets`, and `Dependencies`.
- Comments match actual triggers, permissions, dependencies, and approval
  behavior.
- Reusable inputs, outputs, and secrets have useful descriptions.
- Job and step names communicate outcomes.
- Recovery guidance exists for consequential partial failures.
- Links resolve and point to owned, current runbooks.
- No comment, summary, annotation, or artifact leaks sensitive data.
- Documentation updates are included in the same change as workflow behavior.
