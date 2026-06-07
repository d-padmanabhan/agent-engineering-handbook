# Bash Engineering Best Practices

**Goal:** Production-grade Bash standards for portability, safety, performance, and maintainability.

**Principles:** DRY • KISS • Fail Fast • Zero Warnings

## Bash Philosophy (Core Principles)

**Core Principles:**

- **"Fail fast, fail clearly"** - Use strict mode, validate early, provide clear error messages
- **"Quotes are your friend"** - Always quote variables unless you explicitly want word splitting
- **"Explicit over implicit"** - Use `local`, `readonly`, clear function names, document assumptions
- **"Portability matters"** - Prefer POSIX-compliant code when possible, document Bash-specific features
- **"Security by default"** - Sanitize inputs, use `mktemp`, avoid `eval`, validate file paths
- **"Composition over complexity"** - Small functions, clear separation of concerns, reusable patterns
- **"Prefer `case` for branching"** - When matching on a single value/pattern, prefer `case` over long `if/elif/else` chains
- **"Observability is essential"** - Structured logging, proper exit codes, error context
- **"Test what you write"** - Use shellcheck, test on multiple platforms, write BATS tests

**Applying Bash Principles:**

```bash
# ❌ BAD: Implicit, unsafe, unclear
#!/bin/bash
cd $DIR
rm -rf *
for file in $(ls *.txt); do
  process $file
done

# ✅ GOOD: Explicit, safe, clear
#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TARGET_DIR="${1:-}"

if [[ -z "$TARGET_DIR" ]]; then
  echo "Usage: $0 <directory>" >&2
  exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Error: Directory '$TARGET_DIR' does not exist" >&2
  exit 1
fi

cd "$TARGET_DIR" || { echo "Error: Failed to cd to '$TARGET_DIR'" >&2; exit 1; }

for file in *.txt; do
  [[ -f "$file" ]] || continue
  process "$file"
done
```

---

## Quick Reference

```bash
set -euo pipefail           # Strict mode (fail-fast)
set -uo pipefail            # Controlled mode (explicit error handling)
set -Euo pipefail           # Strict + ERR trap propagation to functions
command -v cmd >/dev/null   # Check if command exists (portable)
trap 'cleanup' EXIT         # Always cleanup
flock -n 200 || exit 1      # Prevent concurrent runs
readonly VAR="value"        # Immutable constant
local var="value"           # Function-local variable
```

---

## Core Standards

- **Shebang:** `#!/usr/bin/env bash` (for portability) or `#!/bin/bash` (when bash-specific features required)
- **Safety Mode:** Choose based on context:
  - `set -euo pipefail` - Strict (fail-fast for simple scripts)
  - `set -uo pipefail` - Controlled (explicit error handling for complex scripts)
  - `set -Euo pipefail` - Strict + ERR trap propagation to functions
- **Linting:** Must pass **`shellcheck`** with **0 errors/warnings**
- **Formatting:** Must pass **`shfmt -i 2 -ci -sr -bn`** (2-space indent, indent switch/case, simplify redirects, binary ops at line end)
- **Extension:** Use `.sh` for scripts, no extension for executables in `bin/` is acceptable if documented
- **Variable Naming:**
  - **Uppercase** for constants and configuration: `readonly MAX_RETRIES=10`, `readonly CONFIG_FILE="/etc/app.conf"`
  - **Lowercase** for local variables: `local count=0`, `local file_name="data.txt"`
  - **Uppercase convention** helps distinguish constants from variables, avoids collisions with environment variables

---

## Error Handling & Safety

### Error Handling Modes

**Strict Mode (Fail-Fast):**

```bash
set -euo pipefail  # Exit immediately on any error
```

Use for: Simple linear scripts, dependency installation, straightforward validation.

**Controlled Mode (Explicit):**

```bash
set -uo pipefail  # No -e: you handle errors explicitly
```

Use for: Diagnostics, cleanup operations, commands where failure is expected (grep, curl with retries).

**Strict + ERR Trap Propagation:**

```bash
set -Euo pipefail  # -E ensures ERR traps propagate to functions

trap 'echo "ERROR in ${FUNCNAME[0]:-main} at line $LINENO"' ERR

func1() {
  false  # Will trigger ERR trap even inside function
}
```

Use for: Production scripts with comprehensive error handling via ERR traps.

### Best Practices

- **Variables:** Always quote variables `"${VAR}"` to prevent word splitting
- **Unset Vars:** `set -u` ensures you don't use undefined variables
- **Pipefail:** `set -o pipefail` catches errors in the middle of pipes
- **Temporary Files:** Use `mktemp` and `trap 'rm ...' EXIT` to clean up
- **Lockfiles:** Use `flock` to prevent concurrent runs:

```bash
exec 200>"/tmp/${SCRIPT_NAME}.lock"
flock -n 200 || { echo "Already running"; exit 1; }
```

---

## Performance & Patterns

**Golden Rule:** Profile with `time` command, optimize hot paths, prefer builtins over external commands.

### Process Substitution (Avoid Subshells)

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
done < <(cat file.txt)
echo "$count"  # Works! Variable persists
```

### Performance Optimization Examples

**String Operations:**

```bash
# ❌ BAD: External command (slow)
result=$(echo "$var" | sed 's/old/new/g')

# ✅ GOOD: Builtin parameter expansion (fast)
result="${var//old/new}"

# ❌ BAD: Multiple external commands
length=$(echo "$var" | wc -c)

# ✅ GOOD: Builtin expansion
length=${#var}
```

**Array Operations:**

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

**Builtin vs External Commands:**

```bash
# ❌ BAD: External command
if [ "$(echo "$var" | grep -q pattern)" ]; then

# ✅ GOOD: Builtin test
if [[ "$var" =~ pattern ]]; then

# ❌ BAD: External command for arithmetic
result=$(expr "$a" + "$b")

# ✅ GOOD: Builtin arithmetic
result=$((a + b))

# ❌ BAD: External command for basename
name=$(basename "$file")

# ✅ GOOD: Builtin parameter expansion
name="${file##*/}"
```

### Other Performance Tips

- **Builtins:** Prefer `[[ ... ]]` over `[ ... ]` (test) for Bash
- **Subshells:** Avoid unnecessary `$(...)` or pipes if builtins work
- **Dependencies:** Check for required tools (`command -v tool`) at startup
- **Arrays:** Use arrays for lists of items instead of strings (Bash 4+)
- **Native Operations:** Prefer `${var//old/new}` over `echo "$var" | sed 's/old/new/g'`
- **Caching:** Cache expensive command results, avoid repeated calls
- **Early Returns:** Exit early to avoid unnecessary processing

---

## Logging & Observability

**Standard Logging:**

```bash
log() {
  local level="$1"
  shift
  # UTC ISO-8601-like timestamp
  echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') [$level] $*" >&2
}
```

**Structured Error Logging:**

```bash
logmsg() {
  local level="${1:-INFO}"; shift
  local timestamp
  timestamp=$(date -u +"%Y-%m-%d %T,%3N" 2>/dev/null || date -u +"%Y-%m-%d %T")
  printf "%s: %s: %s\n" "$timestamp" "$level" "$*" | tee -a "$LOGFILE"
  command -v logger >/dev/null && logger -t "$SCRIPT_NAME" "$level: $*"

  # Structured JSON error reporting
  if [[ "$level" == "ERROR" ]]; then
    printf '{"timestamp":"%s","level":"%s","message":"%s","source":"%s","line":%d,"function":"%s"}\n' \
      "$timestamp" "$level" "$*" "${BASH_SOURCE[1]}" "${BASH_LINENO[0]}" "${FUNCNAME[1]:-main}" \
      >> "${LOGFILE}.errors"
  fi
}
```

---

## Structure & Modularity

- **Main Function:** Encapsulate logic in `main()` and call it at the end
- **Functions:** Use `function_name() { ... }` style
- **Locals:** Use `local` keyword for variables inside functions
- **Usage:** Provide a `usage()` function for help text

### Variable Declaration

**Guidelines:**

- Use `local` **inside functions** for locals
- Use **`readonly`** for constants
- Use **`export`** only if a child process needs the value
- Use `declare` or `typeset` for attributes (Bash-specific)

**Examples:**

```bash
# Top-level constants & environment
readonly SCRIPT_NAME="$(basename "$0" .sh)"
readonly DEFAULT_TIMEOUT=60
export PATH="/usr/local/bin:$PATH"

# Function locals with attributes (bash)
do_work() {
  local -i retries=0 max=5
  local -A meta=()                  # bash 4+
  local -a files=()
  local -l env="${ENVIRONMENT:-dev}"  # always-lowercased
}
```

### Usage Function Pattern

```bash
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [OPTIONS] <arguments>

Description:
  Brief description of what the script does.

Options:
  -h, --help      Show this help message
  -v, --version   Show version information
  -d, --debug     Enable debug output
  -q, --quiet     Suppress non-error output

Arguments:
  <arguments>     Description of required arguments

Examples:
  $(basename "${BASH_SOURCE[0]}") --debug input.txt
  $(basename "${BASH_SOURCE[0]}") -q output.txt

Exit Codes:
  0  Success
  1  General error
  2  Invalid arguments
  3  Missing dependency
EOF
  exit "${1:-1}"
}
```

### Here-Documents (Here-Docs)

**Use here-docs for multiline strings, templates, and embedded content:**

> [!IMPORTANT]
> The heredoc terminator (e.g., `EOF`) must start at **column 0** and match exactly. If you want indentation, use `<<-EOF` and **tabs only** (spaces will break termination).

```bash
# Basic here-doc
cat <<EOF > config.yaml
port: 8080
env: production
database:
  host: localhost
  port: 5432
EOF

# Here-doc with variable expansion
cat <<EOF > message.txt
Hello ${USER},
Your script completed at $(date).
EOF

# Indented here-doc (removes leading tabs)
cat <<-EOF
    This line has leading tabs removed
    So does this one
EOF

# Here-doc without variable expansion (literal)
cat <<'EOF'
This $VAR will not be expanded
Nor will $(command) be executed
EOF
```

**When to use here-docs:**

- Configuration file generation
- Template files (Dockerfiles, Kubernetes manifests)
- Multiline error messages
- Embedded SQL queries
- Cleaner than multiple `echo` statements

---

## Common Pitfalls (Avoid These)

### 1. Unquoted Variables

```bash
# ❌ Wrong
if [ $var = "hello" ]; then  # Fails if var is empty or has spaces

# ✅ Correct
if [ "$var" = "hello" ]; then
# Or use [[ (Bash-specific but safer)
if [[ $var = "hello" ]]; then
```

### 2. Parsing `ls` Output

```bash
# ❌ Wrong
for file in $(ls *.txt); do

# ✅ Correct
for file in *.txt; do
  [ -f "$file" ] || continue
```

### 3. `cd` Without Error Checking

```bash
# ❌ Wrong
cd "$some_dir"
rm -rf *  # Disaster if cd failed!

# ✅ Correct
cd "$some_dir" || { echo "Failed to cd"; exit 1; }
rm -rf *
```

### 4. Using `$*` Instead of `"$@"`

**Always use `"$@"` for script arguments to preserve argument boundaries:**

```bash
# ❌ WRONG - $* loses argument boundaries
my_script() {
  for arg in $*; do
    echo "$arg"
  done
}

my_script "file one.txt" "file two.txt"
# Output: file (lost quotes!)
#         one.txt

# ✅ CORRECT - "$@" preserves boundaries
my_script() {
  for arg in "$@"; do
    echo "$arg"
  done
}

my_script "file one.txt" "file two.txt"
# Output: file one.txt (preserved!)
#         file two.txt
```

**Why `"$@"` matters:**

- Preserves quoted arguments with spaces
- Handles filenames correctly
- Maintains argument count (`$#`)
- Prevents data loss and security issues

**Rule of thumb:** Always use `"$@"` unless you explicitly need word splitting (rare).

---

## Security

- **Sanitize Inputs:** Use `read -r` (no backslash escaping)
- **Sensitive Data:** Use `read -s` for passwords
- **Avoid `eval`:** Never use `eval` with unsanitized input
- **Temp Files:** Use `mktemp` with `umask 077`:

```bash
umask 077
TEMP=$(mktemp) || { echo "Failed to create temp file"; exit 1; }
trap 'rm -f "$TEMP"' EXIT
```

- **Validate Input:** Use `case` or regex:

```bash
case "$input" in
  [0-9]*) echo "Valid" ;;
  *) echo "Invalid"; exit 1 ;;
esac
```

---

## Testing & Validation

```bash
# Static analysis
shellcheck script.sh

# Formatting
shfmt -w -i 2 -ci -sr -bn .

# Unit tests with BATS
@test "check_dependency detects missing tool" {
  run check_dependency "nonexistent_tool"
  [ "$status" -eq 3 ]
}
```

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

---

## Advanced Patterns

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

---

## Prompting & User Interaction

### Basic Prompting

```bash
# Simple prompt
read -p "Enter your name: " name

# Single-key prompt
read -n 1 -p "Continue? [y/n] " yn
echo
[[ "$yn" =~ ^[Yy]$ ]] && proceed

# Prompt with timeout
read -t 5 -p "Press Enter to continue (timeout in 5s): " || echo "Timeout"
```

### Yes/No/Cancel Function

```bash
prompt_ync() {
  local yn
  while true; do
    read -n 1 -p "${GREEN}$1 [y/n/c]${NC} " yn
    echo
    case "$yn" in
      [Yy]*) logmsg "INFO" "User chose Yes"; return 0 ;;
      [Nn]*) logmsg "INFO" "User chose No"; return 1 ;;
      [Cc]*) logmsg "INFO" "User canceled"; exit 2 ;;
      *) logmsg "${RED}Invalid (y/n/c)${NC}" ;;
    esac
  done
}
```

### Secure Password Prompting

```bash
# Prompt for password without echoing
read -r -s -p "${GREEN}Enter password:${NC} " password
echo  # Newline after hidden input

# Validate password strength
if [[ ${#password} -lt 8 ]]; then
  logmsg "${RED}Password must be at least 8 characters${NC}"
  exit 1
fi
```

---

## Cross-Platform Notes

- **macOS ships with Bash 3.2** - Install Bash 4+ via Homebrew for modern features
- **GNU vs BSD tools** - Provide fallbacks:

```bash
# GNU (Linux)
SCRIPT=$(readlink -f "$0")

# BSD/macOS fallback
SCRIPT=$(readlink -f "$0" 2>/dev/null || realpath "$0")
```

- **POSIX compliance** - For maximum portability, avoid `[[`, `${var,,}`, associative arrays
- **Test on target platforms** - Use `dash` or `sh` for POSIX testing

---

## Troubleshooting & Debugging

### Debug Techniques

```bash
# Enable debug output
set -x  # Print each command before execution
set -v  # Print each line as read

# Disable debug
set +x
set +v

# Debug function
debug() {
  if [[ "${DEBUG:-0}" == "1" ]]; then
    echo "[DEBUG] $*" >&2
  fi
}

# Usage
DEBUG=1 ./script.sh
```

### Error Tracing

```bash
# Enhanced error trap
trap 'echo "Error at line $LINENO in ${FUNCNAME[0]:-main}: $BASH_COMMAND"' ERR

# Function call stack
trap 'echo "Call stack: ${FUNCNAME[*]}"' ERR
```

### Common Issues & Solutions

**Issue: Variable not set**

```bash
# Problem: Unset variable causes script to exit
set -u
echo "$UNDEFINED_VAR"  # Exits with error

# Solution: Use default value
echo "${UNDEFINED_VAR:-default_value}"

# Solution: Check before use
if [[ -n "${UNDEFINED_VAR:-}" ]]; then
  echo "$UNDEFINED_VAR"
fi
```

**Issue: Command not found**

```bash
# Solution: Check first
if ! command -v some_command >/dev/null 2>&1; then
  echo "Error: some_command not found" >&2
  exit 1
fi
some_command
```

---

## Version Compatibility Matrix

| Feature | Bash 3.2 | Bash 4.x | Bash 5.x | POSIX sh |
|---------|----------|----------|----------|----------|
| `[[...]]` | ✅ | ✅ | ✅ | ❌ |
| `${var,,}` (lowercase) | ❌ | ✅ | ✅ | ❌ |
| Associative arrays `-A` | ❌ | ✅ | ✅ | ❌ |
| `mapfile`/`readarray` | ❌ | ✅ | ✅ | ❌ |
| Process substitution `<()` | ✅ | ✅ | ✅ | ❌ |
| `[...]` test | ✅ | ✅ | ✅ | ✅ |
| `readonly` | ✅ | ✅ | ✅ | ✅ |
| `local` | ✅ | ✅ | ✅ | ❌ |

**Notes:**

- **macOS ships with Bash 3.2 by default** - Install via Homebrew for modern features
- For maximum portability (POSIX sh), avoid Bash-specific features
- Test scripts with `dash` or `sh` to verify POSIX compliance

---

## Comprehensive Example Script

```bash
#!/usr/bin/env bash
set -eEuo pipefail

# ================================================================
# Script: process-users.sh
# Purpose: Process user data files with validation
# ================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "$0" .sh)"
readonly VERSION="1.0.0"

# Configuration
readonly MAX_RETRIES=3
readonly RETRY_DELAY=2
readonly LOCK_FILE="/tmp/${SCRIPT_NAME}.lock"
readonly LOGFILE="${HOME}/log/${SCRIPT_NAME}_$(date -u +%Y%m%d_%H%M%S).log"

# Logging
log() {
  local level="$1"
  shift
  local timestamp
  timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
  printf "%s [%s] %s\n" "${timestamp}" "${level}" "$*" | tee -a "${LOGFILE}" >&2
}

log_info() { log "INFO" "$@"; }
log_error() { log "ERROR" "$@"; }

# Cleanup
cleanup() {
  log_info "Cleaning up..."
  rm -f "$LOCK_FILE"
  [[ -n "${TEMP_FILE:-}" ]] && rm -f "$TEMP_FILE"
}

trap cleanup EXIT INT TERM

# Lock file
acquire_lock() {
  exec 200>"$LOCK_FILE" || {
    log_error "Failed to create lock file"
    exit 1
  }

  if ! flock -n 200; then
    log_error "Another instance is running"
    exit 1
  fi
}

# Dependency check
check_dependencies() {
  local deps=("jq" "curl")
  local missing=()

  for dep in "${deps[@]}"; do
    if ! command -v "$dep" >/dev/null 2>&1; then
      missing+=("$dep")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    log_error "Missing dependencies: ${missing[*]}"
    exit 1
  fi
}

# Validate input file
validate_input() {
  local file="$1"

  if [[ ! -f "$file" ]]; then
    log_error "Input file not found: $file"
    return 1
  fi

  if [[ ! -r "$file" ]]; then
    log_error "Input file not readable: $file"
    return 1
  fi

  if [[ ! -s "$file" ]]; then
    log_error "Input file is empty: $file"
    return 1
  fi

  # Validate JSON format
  if ! jq empty "$file" 2>/dev/null; then
    log_error "Invalid JSON format: $file"
    return 1
  fi

  return 0
}

# Retry wrapper
retry() {
  local max_attempts="$1"
  local delay="$2"
  shift 2
  local attempt=1

  while ! "$@"; do
    if ((attempt >= max_attempts)); then
      log_error "Failed after $max_attempts attempts: $*"
      return 1
    fi

    log_info "Attempt $attempt/$max_attempts failed, retrying in ${delay}s..."
    sleep "$delay"
    delay=$((delay * 2 > 60 ? 60 : delay * 2))
    ((attempt++))
  done
}

# Usage
usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] <input_file>

Options:
  -h, --help      Show this help message
  -v, --version   Show version
  -d, --debug     Enable debug output

Arguments:
  input_file      JSON file containing user data

Examples:
  $SCRIPT_NAME users.json
  $SCRIPT_NAME --debug users.json
EOF
  exit 0
}

# Main function
main() {
  local input_file="${1:-}"

  if [[ -z "$input_file" ]]; then
    log_error "Input file required"
    usage
  fi

  log_info "Starting $SCRIPT_NAME v$VERSION"

  acquire_lock
  check_dependencies

  if ! validate_input "$input_file"; then
    exit 1
  fi

  log_info "Processing complete"
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
```

**Key Patterns Demonstrated:**

- ✅ Strict error handling (`set -eEuo pipefail`)
- ✅ Lock file for concurrency control
- ✅ Dependency checking
- ✅ Input validation
- ✅ Structured logging
- ✅ Retry logic with exponential backoff
- ✅ Cleanup on exit
- ✅ Usage documentation

---

## Anti-Patterns (Forbidden)

- ❌ `eval` on user input
- ❌ Using unquoted variables in file paths
- ❌ Parsing `ls` output (use `find` or globs)
- ❌ Swallowing errors (unless explicit `|| true`)
- ❌ `cd` without error checking before destructive operations
- ❌ Variables in pipes (use process substitution)
- ❌ Using aliases in scripts (use functions instead)
