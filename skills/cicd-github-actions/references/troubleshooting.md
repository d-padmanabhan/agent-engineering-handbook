# GitHub Actions Troubleshooting

## Common Issues

### Permissions Denied

```yaml
# Issue: Resource not accessible by integration
# Solution: Add required permissions
permissions:
  contents: read
  pull-requests: write
```

### Cache Not Restoring

```yaml
# Check cache key matches exactly
- uses: actions/cache@v6
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    # Add restore-keys for partial matches
    restore-keys: |
      ${{ runner.os }}-node-
```

### Secrets Not Available

```yaml
# Secrets not available in:
# - fork PRs (security)
# - workflow_dispatch from forks

# Use environment-scoped secrets for deployments
jobs:
  deploy:
    environment: production
    steps:
      - name: Deploy
        env:
          PROD_KEY: ${{ secrets.PROD_KEY }}
        run: ./deploy.sh
```

### Workflow Does Not Trigger

Check these in order:

1. The workflow file exists on the default branch for `workflow_dispatch` and scheduled events.
2. The event, branch, tag, and path filters all match. `paths` and `paths-ignore` cannot be used together for the same event.
3. The changed files are not excluded by the workflow's path filters.
4. The repository or organization has not disabled Actions or restricted the referenced actions.
5. A previous run was not skipped by commit-message filtering or cancelled by concurrency.

Use the Actions UI or `gh workflow view <workflow> --yaml` to inspect the workflow GitHub is actually evaluating.

## Debugging

### Enable Debug Logging

```yaml
# Repository secret
ACTIONS_STEP_DEBUG: true
ACTIONS_RUNNER_DEBUG: true

# Or in workflow
- run: echo "Debug info"
  env:
    ACTIONS_STEP_DEBUG: true
```

### Print Context

Print only the fields needed for diagnosis. Do not dump the complete `github` context because it includes sensitive values such as `github.token`.

```yaml
- name: Print diagnostic context
  env:
    EVENT_NAME: ${{ github.event_name }}
    REF_NAME: ${{ github.ref_name }}
    COMMIT_SHA: ${{ github.sha }}
    ACTOR: ${{ github.actor }}
  run: |
    printf 'Event: %s\n' "$EVENT_NAME"
    printf 'Ref: %s\n' "$REF_NAME"
    printf 'SHA: %s\n' "$COMMIT_SHA"
    printf 'Actor: %s\n' "$ACTOR"
```

Interactive debug shells expand the runner's exposure and may reveal credentials or private network access. Use them only through an explicitly approved, time-bounded workflow on trusted branches and never for untrusted pull requests.

## Performance

### Slow Checkout

```yaml
# Use shallow clone
- uses: actions/checkout@v7
  with:
    fetch-depth: 1
```

### Large Artifacts

```yaml
# Compress before upload
- run: tar -czf build.tar.gz dist/
- uses: actions/upload-artifact@v7
  with:
    name: build
    path: build.tar.gz
    compression-level: 0  # Already compressed
```

### Parallel Jobs

```yaml
jobs:
  test:
    timeout-minutes: 30
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - name: Run test shard
        env:
          TEST_SHARD: ${{ matrix.shard }}
        run: npm test -- --shard="$TEST_SHARD"/4
```

## Error Handling

### Continue on Error

```yaml
- name: Non-critical step
  continue-on-error: true
  run: ./optional-check.sh

- name: Check result
  if: steps.previous.outcome == 'failure'
  run: echo "Previous step failed but continuing"
```

### Retry Logic

```yaml
- name: Retry on failure
  uses: nick-fields/retry@v4
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: npm test
```

### Timeout

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Long step
        timeout-minutes: 10
        run: ./long-running.sh
```

## Common Gotchas

1. **`pull_request_target`**: Has write access, dangerous for forks
2. **Expression syntax**: `${{ }}` vs `${ }` in shell
3. **Multiline strings**: Use `|` for run commands
4. **Environment variables**: Quote values with special chars
5. **Path context**: `working-directory` doesn't affect `uses`

```yaml
# Correct multiline
- run: |
    echo "Line 1"
    echo "Line 2"

# Correct quoting
- env:
    MY_VAR: ${{ github.event.pull_request.title }}
  run: printf 'Value: %s\n' "$MY_VAR"
```
