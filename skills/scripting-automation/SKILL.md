---
name: scripting-automation
description: Advanced Bash automation patterns for production-grade scripts and automation workflows. Covers retry logic, lock files, signal handling, advanced error handling, performance optimization, testing with BATS, and cross-platform compatibility. Use when building automation scripts, deployment tools, CI/CD helpers, or when asking about advanced Bash patterns, script reliability, or automation best practices.
---

# Scripting & Automation

## Guiding Principles

- **"Fail fast, fail clearly"** - Use strict mode, validate early, provide clear error messages
- **"Quotes are your friend"** - Always quote variables unless you explicitly want word splitting
- **"Explicit over implicit"** - Use `local`, `readonly`, clear function names, document assumptions
- **"Security by default"** - Sanitize inputs, use `mktemp`, avoid `eval`, validate file paths
- **"Composition over complexity"** - Small functions, clear separation of concerns, reusable patterns
- **"Observability is essential"** - Structured logging, proper exit codes, error context
- **"Test what you write"** - Use shellcheck, test on multiple platforms, write BATS tests
- **"Format consistently"** - Must pass `shfmt -i 2 -ci -sr -bn` (2-space indentation; prefer ~100-character lines)

## Quick Reference

```bash
# Safety modes
set -euo pipefail           # Strict mode (fail-fast)
set -uo pipefail            # Controlled mode (explicit error handling)
set -Euo pipefail           # Strict + ERR trap propagation to functions

# Common patterns
command -v cmd >/dev/null   # Check if command exists (portable)
trap 'cleanup' EXIT         # Always cleanup
flock -n 200 || exit 1      # Prevent concurrent runs
readonly VAR="value"        # Immutable constant
local var="value"           # Function-local variable
shfmt -w -i 2 -ci -sr -bn . # Format with Google-style 2-space indentation
```

## Standard Header + Prelude

Use this for new automation scripts. It documents purpose and usage, keeps debug tracing available but commented, creates a timestamped logfile named after the script, and uses a safe logging helper instead of raw `echo`.

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

readonly DTTM="$(date -u +"%Y%m%d_%H%M%S")"
readonly SCRIPT_NAME="$(basename "${0}" .sh)"
readonly LOGFILE="${SCRIPT_NAME}_${DTTM}.log"

logmsg() {
  local timestamp
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf "%s: %s\n" "${timestamp}" "$*" | tee -a "${LOGFILE}" >&2
}
```

## Generation Contract

For any non-trivial automation script (argument parsing, dependency checks, config resolution, build/deploy/verify steps), generate this structure:

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

Reject generated automation scripts that skip this structure unless the script is intentionally tiny and linear.

## Error Handling Modes

### Strict Mode (Fail-Fast)

```bash
set -euo pipefail  # Exit immediately on any error
```

Use for: Simple linear scripts, dependency installation, straightforward validation.

### Controlled Mode (Explicit)

```bash
set -uo pipefail  # No -e: you handle errors explicitly
```

Use for: Diagnostics, cleanup operations, commands where failure is expected (grep, curl with retries).

### Strict + ERR Trap Propagation

```bash
set -Euo pipefail  # -E ensures ERR traps propagate to functions

trap 'echo "ERROR in ${FUNCNAME[0]:-main} at line $LINENO"' ERR

func1() {
  false  # Will trigger ERR trap even inside function
}
```

Use for: Production scripts with comprehensive error handling via ERR traps.

## Advanced Patterns

### Main Function for Multi-Step Automation

Use `main()` once an automation script has multiple named phases. This keeps constants and function definitions separate from execution, makes the script easy to scan, and gives tests a natural set of functions to call.

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

Keep truly tiny scripts linear. If you are adding phase comments like "parse", "validate", "deploy", or "verify", promote those phases into functions and call them from `main()`.

### Know When Bash Is the Wrong Tool

Use Bash for glue: calling CLIs, moving files, simple validation, CI wrappers, and deployment orchestration. Prefer Python/Go/Node when the script needs complex data structures, non-trivial JSON transformation, API clients with pagination/retry state, concurrency, long-lived daemons, or more than a few hundred lines of business logic.

### Retry with Exponential Backoff

```bash
retry_with_backoff() {
  local max_attempts="${1:-5}"
  local delay="${2:-1}"
  shift 2
  local attempt=1

  while ! "$@"; do
    if ((attempt >= max_attempts)); then
      echo "Failed after $max_attempts attempts" >&2
      return 1
    fi

    echo "Attempt $attempt/$max_attempts failed, retrying in ${delay}s..." >&2
    sleep "$delay"
    delay=$((delay * 2 > 60 ? 60 : delay * 2))  # Cap at 60s
    ((attempt++))
  done
}

# Usage
retry_with_backoff 5 2 curl -f https://api.acme.com/health
```

### Lock File Pattern

```bash
acquire_lock() {
  local lock_file="${1:-/tmp/script.lock}"
  local lock_fd=200

  exec ${lock_fd}>"$lock_file" || {
    echo "Failed to open lock file" >&2
    return 1
  }

  if ! flock -n "$lock_fd"; then
    echo "Another instance is running" >&2
    return 1
  fi

  echo "Lock acquired"
  trap "flock -u $lock_fd; rm -f $lock_file" EXIT
}
```

### Signal Handling

```bash
cleanup() {
  echo "Cleaning up..." >&2
  rm -f "$TEMP_FILE"
  # Release resources, close connections, etc.
}

trap cleanup EXIT INT TERM

# Handle specific signals
trap 'echo "Received SIGUSR1"' USR1
trap 'echo "Received SIGUSR2"' USR2
```

## Performance Optimization

### Avoid Subshells (Process Substitution)

```bash
# ❌ Wrong - subshell, variables don't persist
count=0
cat file.txt | while read -r line; do
  count=$((count + 1))
done
echo "$count"  # Empty! (subshell issue)

# ✅ Correct - process substitution, no subshell
count=0
while read -r line; do
  count=$((count + 1))
done < file.txt
echo "$count"  # Works! Variable persists
```

### Prefer Builtins Over External Commands

```bash
# ❌ BAD: External command (slow)
result=$(echo "$var" | sed 's/old/new/g')

# ✅ GOOD: Builtin parameter expansion (fast)
result="${var//old/new}"

# ❌ BAD: External command
length=$(echo "$var" | wc -c)

# ✅ GOOD: Builtin expansion
length=${#var}
```

### Use `awk`, `sed`, and `jq` Deliberately

```bash
# Simple string changes: prefer Bash parameter expansion
normalized_path="${input_path//\/\//\/}"

# Use awk/sed only when the operation is truly line-, column-, or regex-oriented
awk -F',' 'NR > 1 && $3 == "active" { print $1 }' users.csv
sed -E 's/[[:space:]]+$//' input.txt > output.txt

# JSON must use jq
jq -e '.items[] | select(.enabled == true) | .id' config.json
```

### Use Arrays for Collections

```bash
# ❌ BAD: String concatenation (slow, error-prone)
files=""
for file in *.txt; do
  files="$files $file"
done

# ✅ GOOD: Arrays (fast, safe)
files=()
for file in *.txt; do
  [[ -f "$file" ]] || continue
  files+=("$file")
done

# Process array
for file in "${files[@]}"; do
  process "$file"
done
```

## Logging & Observability

### Structured Logging

```bash
log() {
  local level="$1"
  shift
  # UTC ISO-8601 timestamp
  printf "%s [%s] %s\n" "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$level" "$*" >&2
}

log_info() { log "INFO" "$@"; }
log_error() { log "ERROR" "$@"; }
log_debug() { [[ "${DEBUG:-0}" == "1" ]] && log "DEBUG" "$@" || true; }
```

### Terminal-safe ANSI colors

Only emit colors for interactive terminal output. Do not write ANSI escape codes to log files.

```bash
if [[ -t 2 ]]; then
  readonly RED=$'\033[0;31m'
  readonly GREEN=$'\033[0;32m'
  readonly NC=$'\033[0m'
else
  readonly RED=''
  readonly GREEN=''
  readonly NC=''
fi

log_error "${RED}Invalid input${NC}"
```

### Structured Error Reporting (JSON)

```bash
log_error_json() {
  local message="$*"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%d %T")

  printf '{"timestamp":"%s","level":"ERROR","message":"%s","source":"%s","line":%d,"function":"%s"}\n' \
    "$timestamp" "$message" "${BASH_SOURCE[1]}" "${BASH_LINENO[0]}" "${FUNCNAME[1]:-main}" \
    >> "${LOG_FILE}.errors"
}
```

## Testing with BATS

### BATS Test Structure

```bash
#!/usr/bin/env bats

load test_helper

@test "function returns success on valid input" {
  run my_function "valid_input"
  [ "$status" -eq 0 ]
  [ "$output" = "expected_output" ]
}

@test "function fails on invalid input" {
  run my_function ""
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Error" ]]
}

@test "function is idempotent" {
  run my_function "input"
  first_output="$output"

  run my_function "input"
  [ "$output" = "$first_output" ]
}
```

### Test Helpers

```bash
# test_helper.bash
setup() {
  TEST_DIR=$(mktemp -d)
  cd "$TEST_DIR" || exit 1
}

teardown() {
  rm -rf "$TEST_DIR"
}

# Mock external commands
mock_command() {
  local cmd="$1"
  local output="$2"
  echo "$output" > "$TEST_DIR/$cmd"
  chmod +x "$TEST_DIR/$cmd"
  PATH="$TEST_DIR:$PATH"
}
```

## Security Best Practices

### Sanitize Inputs

```bash
# Use read -r (no backslash escaping)
read -r user_input

# Validate input
case "$user_input" in
  [0-9]*) echo "Valid number" ;;
  *) echo "Invalid input"; exit 1 ;;
esac
```

### Secure Temporary Files

```bash
umask 077
TEMP=$(mktemp) || { echo "Failed to create temp file"; exit 1; }
trap 'rm -f "$TEMP"' EXIT

# Write sensitive data
echo "secret" > "$TEMP"
```

### Avoid eval with User Input

```bash
# ❌ NEVER DO THIS
eval "$user_input"

# ✅ Use case statements or arrays instead
case "$user_input" in
  start) start_service ;;
  stop) stop_service ;;
  *) echo "Invalid command"; exit 1 ;;
esac
```

## Prompting & User Interaction

### Yes/No/Cancel Prompt

```bash
prompt_ync() {
  local yn
  while true; do
    read -n 1 -p "$1 [y/n/c] " yn
    echo
    case "$yn" in
      [Yy]*) return 0 ;;
      [Nn]*) return 1 ;;
      [Cc]*) exit 2 ;;
      *) echo "Invalid input (y/n/c)" ;;
    esac
  done
}
```

### Secure Password Prompt

```bash
# Prompt for password without echoing
read -r -s -p "Enter password: " password
echo  # Newline after hidden input

# Validate password strength
if [[ ${#password} -lt 8 ]]; then
  echo "Password must be at least 8 characters" >&2
  exit 1
fi
```

## Cross-Platform Compatibility

### GNU vs BSD Tools

```bash
# GNU (Linux)
SCRIPT=$(readlink -f "$0")

# BSD/macOS fallback
SCRIPT=$(readlink -f "$0" 2>/dev/null || realpath "$0")
```

### Version Compatibility

- **macOS ships with Bash 3.2** - Install Bash 4+ via Homebrew for modern features
- For maximum portability (POSIX sh), avoid `[[`, `${var,,}`, associative arrays
- Test scripts with `dash` or `sh` for POSIX compliance

## Common Pitfalls to Avoid

### Unquoted Variables

```bash
# ❌ Wrong
if [ $var = "hello" ]; then  # Fails if var is empty or has spaces

# ✅ Correct
if [ "$var" = "hello" ]; then
# Or use [[ (Bash-specific but safer)
if [[ $var = "hello" ]]; then
```

### Parsing ls Output

```bash
# ❌ Wrong
for file in $(ls *.txt); do

# ✅ Correct
for file in *.txt; do
  [ -f "$file" ] || continue
```

### cd Without Error Checking

```bash
# ❌ Wrong
cd "$some_dir"
rm -rf *  # Disaster if cd failed!

# ✅ Correct
cd "$some_dir" || { echo "Failed to cd"; exit 1; }
rm -rf *
```

### Using $* Instead of "$@"

```bash
# ❌ WRONG - $* loses argument boundaries
my_script() {
  for arg in $*; do
    echo "$arg"
  done
}

# ✅ CORRECT - "$@" preserves boundaries
my_script() {
  for arg in "$@"; do
    echo "$arg"
  done
}
```

## Automation Script Checklist

- [ ] Strict error handling (`set -euo pipefail` or `set -uo pipefail`)
- [ ] Lock file for concurrency control
- [ ] Dependency checking at startup
- [ ] Input validation
- [ ] Structured logging (UTC timestamps, levels)
- [ ] Retry logic for network calls
- [ ] Cleanup on exit (trap EXIT)
- [ ] Usage documentation
- [ ] Exit codes documented
- [ ] Passes shellcheck with 0 warnings
- [ ] Formatted with shfmt
- [ ] Tested with BATS

## Detailed References

- **Bash Best Practices**: See [references/bash.md](references/bash.md) for comprehensive Bash patterns, performance optimization, advanced error handling, testing, security, cross-platform compatibility, and comprehensive examples
