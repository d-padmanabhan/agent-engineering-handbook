# Dependency and Toolchain Currency

Use the latest supported stable release that is compatible with the repository, deployment target, and vendor support matrix. "Latest" alone is not a version policy.

## Decision Order

Choose versions in this order:

1. **Supported:** The vendor, runtime platform, operating system, cloud service, and required libraries support the release.
2. **Stable:** Exclude alpha, beta, release-candidate, nightly, `main`, `master`, and `latest` references unless the task explicitly requires prerelease testing.
3. **Secure:** Prefer a supported version without known applicable critical or high-severity vulnerabilities. Expedite security updates.
4. **Compatible:** Confirm API, ABI, extension, plugin, schema, and deployment-target compatibility.
5. **Current:** Among acceptable releases, select the newest verified stable release.
6. **Reproducible:** Pin execution inputs and commit generated lockfiles or checksums.

Verify exact releases and references through official release metadata, registries, installed-tool output, or vendor documentation. Never construct a tag or version alias and assume it exists.

## New and Existing Projects

For a new application:

- start from the newest supported stable runtime and toolchain available on the deployment target;
- resolve current dependency releases with the native package manager;
- commit runtime/toolchain pins and lockfiles;
- run build, test, lint, type, license, and vulnerability checks.

For an existing application:

- respect the repository's declared support range and pinning posture;
- do not combine an unrequested major migration with unrelated work;
- apply supported security patches promptly;
- handle major upgrades as explicit migrations with release-note review, compatibility tests, staged rollout, and rollback;
- remove stale compatibility code only after the supported floor changes.

Libraries declare the compatibility range they promise to consumers. Applications pin the concrete dependency graph they deploy.

## Pinning Contract

| Surface | Compatibility declaration | Reproducible execution |
|---|---|---|
| Python application | `requires-python` range | Exact `.python-version` plus `uv.lock` |
| Python library | Supported Python and dependency ranges | Lockfile for development and CI |
| Go module | `go` compatibility plus toolchain policy | Verified `go.mod` and `go.sum`; exact toolchain where required |
| Node application | `engines` support policy | Exact `packageManager` plus lockfile and pinned CI runtime |
| TypeScript package | Semver peer/runtime support ranges | Lockfile and tested compiler version |
| pre-commit hook | None | Exact existing `rev` tag or SHA in `.pre-commit-config.yaml` |
| GitHub Action | Repository pinning policy | Verified exact tag or immutable commit SHA |
| Container base | Supported image line | Immutable digest where deployment policy requires it |

Do not hand-edit lockfiles. Use the native resolver and review the resulting graph.

## Upgrade Workflow

1. Inventory runtime, toolchain, direct dependencies, actions, hooks, container bases, plugins, and generated lockfiles.
2. Read repository support policy and identify frozen or intentionally deferred pins.
3. Query authoritative release metadata and verify the exact proposed ref exists.
4. Review release notes, migrations, deprecations, security advisories, license changes, and transitive graph changes.
5. Update through the native tool: `uv`, `go`, npm/pnpm/yarn, `pre-commit autoupdate`, Dependabot, or Renovate.
6. Run unit, integration, compatibility, lint, type, build, package, and vulnerability checks applicable to the change.
7. Roll out incrementally when runtime behavior or deployment artifacts change.
8. Record the selected version, evidence, rollback, and any deferred follow-up.

## Ecosystem Requirements

### GitHub Actions

- Inspect every `uses:` entry in a changed workflow.
- Verify the exact Git ref. A latest release named `v10.0.1` does not prove a `v10` moving tag exists.
- Default to the verified latest stable moving major alias.
- If the user explicitly requests an exact stable tag or immutable commit SHA, verify and use that pinning mode instead.
- Let Dependabot or Renovate propose future updates.

### pre-commit

- Hook `rev` values must resolve to exact tags or SHAs.
- Run `pre-commit autoupdate`, inspect every changed hook, then run `pre-commit run --all-files`.
- Do not accept a hook update that silently changes language runtime, file scope, or mutation behavior.

### Python and uv

- New applications use the handbook's supported Python line and the latest tested stable patch available on the deployment target.
- Keep a compatibility range in `requires-python`; pin the tested interpreter separately.
- Use `uv lock --upgrade` or targeted `uv lock --upgrade-package`, review `uv.lock`, and run Python compatibility and vulnerability checks.
- Libraries may retain a lower supported floor when the compatibility commitment is explicit and tested.

### Go

- Use the latest supported stable Go toolchain compatible with the deployment and module policy.
- Keep `go.mod` and `go.sum` authoritative; run `go get` or `go get -u` deliberately, followed by `go mod tidy`, `go mod verify`, tests, static analysis, and `govulncheck`.
- Review major module paths and behavior changes rather than forcing versions in `go.mod`.

### Node.js, Package Managers, and TypeScript

- Production applications normally use the newest supported active LTS Node.js line accepted by the deployment target, not an untested Current or prerelease line.
- Pin the package manager version in `packageManager`, use Corepack, and commit exactly one native lockfile.
- Upgrade dependencies with the declared package manager; review peer dependency and engine changes.
- Pin and test the TypeScript compiler used by CI. A newer compiler can change type checking or emitted output even when application dependencies are unchanged.
- Run tests, type checks, builds, linters, and `npm audit` or the repository's established vulnerability scanner.

## Automation and Exceptions

Enable scheduled Dependabot, Renovate, or equivalent automation for supported ecosystems. Keep update groups small enough to diagnose failures. Automate discovery and testing, not unconditional production adoption.

An exception must include:

```text
Component and current version:
Latest acceptable version considered:
Reason for deferral:
Compatibility or security impact:
Compensating controls:
Owner:
Expiry date:
Upgrade trigger or plan:
```

No owner or expiry means no exception.
