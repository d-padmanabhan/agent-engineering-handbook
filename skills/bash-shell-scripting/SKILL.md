---
name: bash-shell-scripting
description: Bash scripting best practices for production-grade scripts, CLI tools, and Makefiles. Covers strict mode, error handling, portability, performance patterns, and argument parsing. Use when working with .sh files, Makefiles, shell scripts, or when asking about Bash, shell scripting, CLI design, or command-line tools.
---

# Bash & Shell Scripting

## Core Principles

- **DRY**: Don't Repeat Yourself
- **KISS**: Keep It Simple
- **Fail Fast**: Exit on errors immediately
- **Zero Warnings**: Must pass shellcheck

## Quick Reference

```bash
set -euo pipefail           # Strict mode (fail-fast)
set -uo pipefail            # Controlled mode (explicit error handling)
set -Euo pipefail           # Strict + ERR trap propagation
command -v cmd >/dev/null   # Check if command exists (portable)
trap 'cleanup' EXIT         # Always cleanup
flock -n 200 || exit 1      # Prevent concurrent runs
readonly VAR="value"        # Immutable constant
local var="value"           # Function-local variable
```

## Core Standards

| Aspect | Standard |
|--------|----------|
| **Shebang** | `#!/usr/bin/env bash` or `#!/bin/bash` |
| **Safety Mode** | `set -euo pipefail` (strict) or `set -uo pipefail` (controlled) |
| **Linting** | Must pass `shellcheck` with 0 errors/warnings |
| **Formatting** | Must pass `shfmt -i 2 -ci -sr -bn`; prefer ~100-character lines |
| **Extension** | `.sh` for scripts |
| **Variables** | Uppercase constants/globals, lowercase locals, descriptive names, braces + quotes (`"${VAR}"`) |

## Generation Contract

For any non-trivial script (more than 10-15 lines, more than one command phase, argument parsing, dependency checks, config resolution, build/deploy/verify steps), generate this structure:

1. Header block.
2. Commented debug toggle (`# set -x`), disabled by default.
3. Strict or controlled mode.
4. Readonly constants and timestamped `LOGFILE`.
5. `logmsg`, `die`, and optional `debug` helper.
6. `require_command` for dependencies.
7. Helper functions with lowercase locals.
8. `parse_args`.
9. `main()`.
10. `main "$@"` as the final line.

Reject generated Bash that skips this structure unless the script is intentionally tiny and linear.

## Error Handling Modes

### Strict Mode (Fail-Fast)

```bash
set -euo pipefail  # Exit immediately on any error
```

Use for: Simple linear scripts, dependency installation, straightforward validation.

### Controlled Mode (Explicit)

```bash
set -uo pipefail  # No -e: handle errors explicitly
```

Use for: Diagnostics, cleanup operations, commands where failure is expected.

### Strict + ERR Trap

```bash
set -Euo pipefail

trap 'echo "ERROR in ${FUNCNAME[0]:-main} at line $LINENO"' ERR
```

Use for: Production scripts with comprehensive error handling.

## Script Template

```bash
#!/usr/bin/env bash
#
# Script Name         : <script_name>.sh
#
# Purpose             : <One or two sentences explaining what the script does.
#                       Wrap continuation lines under the value column.>
#
# Dependencies        : <List required commands, or "None">
#
# Script Usage        : ./<script_name>.sh [options] <arguments>
#
#                       <Examples and argument notes.>
#
##----------------------------------------------------------------------------------------##
# Turn debug on or off
# set -x
##----------------------------------------------------------------------------------------##

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DTTM="$(date -u +"%Y%m%d_%H%M%S")"
readonly SCRIPT_NAME="$(basename "${0}" .sh)"
readonly LOGFILE="${SCRIPT_NAME}_${DTTM}.log"

cleanup() {
  rm -f "${TEMP_FILE:-}" 2>/dev/null || true
}
trap cleanup EXIT

logmsg() {
  local timestamp
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf "%s: %s\n" "${timestamp}" "$*" | tee -a "${LOGFILE}" >&2
}

die() {
  logmsg "ERROR: $*"
  exit 1
}

main() {
  local arg="${1:-}"
  [[ -z "${arg}" ]] && die "Usage: ${SCRIPT_NAME} <argument>"

  logmsg "Processing: ${arg}"
  # Main logic here
}

main "$@"
```

Minimal dependency helper:

```bash
require_command() {
  local command_name="$1"
  command -v "${command_name}" >/dev/null 2>&1 || die "Missing command: ${command_name}"
}
```

## Best Practices

### Always Quote Variables

```bash
# ✅ GOOD
echo "${var}"
[[ -n "${var:-}" ]] && echo "set"
printf "%s\n" "${array[@]}"

# ❌ BAD
echo $var
[ -n $var ] && echo "set"
```

### Process Text and JSON Deliberately

```bash
# Simple string changes: prefer Bash parameter expansion
normalized_path="${input_path//\/\//\/}"

# Line/column text processing: awk/sed are appropriate when necessary
awk -F',' 'NR > 1 && $3 == "active" { print $1 }' users.csv
sed -E 's/[[:space:]]+$//' input.txt > output.txt

# JSON: use jq; never parse JSON with grep/sed/string splitting
jq -e '.users[] | select(.active == true) | .id' users.json
```

### Terminal-safe ANSI Colors

Define color codes only when writing to an interactive terminal. Do not emit ANSI escapes into log files, CI summaries, or non-terminal output.

```bash
if [[ -t 2 ]]; then
  readonly RED=$'\033[0;31m'
  readonly GREEN=$'\033[0;32m'
  readonly YELLOW=$'\033[1;33m'
  readonly NC=$'\033[0m'
else
  readonly RED=''
  readonly GREEN=''
  readonly YELLOW=''
  readonly NC=''
fi

logmsg "${GREEN}Starting job${NC}"
logmsg "${RED}Invalid input${NC}"
```

### Use Functions

```bash
process_file() {
    local file="$1"
    [[ -f "$file" ]] || return 1
    # Process file
}
```

### Know When Bash Is the Wrong Tool

Use Bash for glue: calling CLIs, moving files, simple validation, CI wrappers, and deployment orchestration. Prefer Python/Go/Node when the script needs complex data structures, non-trivial JSON transformation, API clients with pagination/retry state, concurrency, long-lived daemons, or more than a few hundred lines of business logic.

### Use `main()` When the Script Has Phases

Tiny one-shot scripts can stay linear, but once a script has multiple named phases, wrap execution in `main()`. This separates globals/functions from execution, makes the script read like a table of contents, and makes future testing/refactoring easier.

```bash
main() {
  parse_args "$@"
  require_command curl
  require_command git
  require_command npm
  resolve_env_file
  install_dependencies_if_needed
  build_assets
  load_deploy_environment
  deploy_worker_assets "$@"
  verify_worker_hostnames
}

main "$@"
```

### Check Command Existence

```bash
command -v docker >/dev/null 2>&1 || die "docker is required"
```

### Temporary Files

```bash
readonly TEMP_FILE="$(mktemp)"
trap 'rm -f "$TEMP_FILE"' EXIT

echo "data" > "$TEMP_FILE"
```

### Lock Files

```bash
exec 200>"/tmp/${SCRIPT_NAME}.lock"
flock -n 200 || { echo "Already running"; exit 1; }
```

## Performance Patterns

### Avoid Subshells in Loops

```bash
# ❌ BAD - subshell, variables don't persist
count=0
cat file.txt | while read -r line; do
    count=$((count + 1))
done
echo "$count"  # Empty! (subshell issue)

# ✅ GOOD - process substitution
count=0
while read -r line; do
    count=$((count + 1))
done < file.txt
echo "$count"  # Correct
```

### Use Arrays

```bash
# Arrays for multiple values
files=("file1.txt" "file2.txt" "file3.txt")
for file in "${files[@]}"; do
    process "$file"
done

# Append to array
files+=("file4.txt")
```

## Argument Parsing

```bash
show_help() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] <file>

Options:
    -h, --help      Show this help
    -v, --verbose   Enable verbose mode
    -o, --output    Output file (default: stdout)
EOF
}

parse_args() {
    VERBOSE=false
    OUTPUT=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help) show_help; exit 0 ;;
            -v|--verbose) VERBOSE=true; shift ;;
            -o|--output) OUTPUT="$2"; shift 2 ;;
            -*) die "Unknown option: $1" ;;
            *) break ;;
        esac
    done

    [[ $# -eq 0 ]] && die "Missing required argument"
    INPUT_FILE="$1"
}
```

## Detailed References

- **Shell Utilities**: See [references/shell-utilities.md](references/shell-utilities.md) for curl, jq, lynx
- **Makefile Patterns**: See [references/makefile-patterns.md](references/makefile-patterns.md)
- **CLI Design**: See [references/cli-design.md](references/cli-design.md)
- **Justfile Patterns**: See [references/justfile.md](references/justfile.md)
- **Repo Sync (rsync)**: See [references/rsync-repo-sync.md](references/rsync-repo-sync.md)
