# CLI Design Patterns

## Argument Parsing

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
readonly VERSION="1.0.0"

show_help() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] <command> [args...]

Commands:
    init        Initialize a new project
    build       Build the project
    deploy      Deploy to environment

Options:
    -h, --help          Show this help message
    -v, --version       Show version
    -V, --verbose       Enable verbose output
    -q, --quiet         Suppress output
    -c, --config FILE   Use config file (default: ./config.yaml)
    -e, --env ENV       Target environment (dev|staging|prod)
    --dry-run           Show what would happen without executing

Examples:
    $SCRIPT_NAME init my-project
    $SCRIPT_NAME build --verbose
    $SCRIPT_NAME deploy --env prod --dry-run
EOF
}

parse_args() {
    # Defaults
    VERBOSE=false
    QUIET=false
    DRY_RUN=false
    CONFIG_FILE="./config.yaml"
    ENV="dev"
    COMMAND=""
    ARGS=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                echo "$SCRIPT_NAME version $VERSION"
                exit 0
                ;;
            -V|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -c|--config)
                [[ -z "${2:-}" ]] && die "Missing value for $1"
                CONFIG_FILE="$2"
                shift 2
                ;;
            -e|--env)
                [[ -z "${2:-}" ]] && die "Missing value for $1"
                ENV="$2"
                shift 2
                ;;
            -*)
                die "Unknown option: $1"
                ;;
            *)
                if [[ -z "$COMMAND" ]]; then
                    COMMAND="$1"
                else
                    ARGS+=("$1")
                fi
                shift
                ;;
        esac
    done

    [[ -z "$COMMAND" ]] && { show_help; exit 1; }
}
```

## Variable Declaration: `local`, `declare`/`typeset`, `readonly`, `export`

**Goal:** Use the right primitive for scope, attributes, and intent without sacrificing portability.

**Guidelines:**

- **Scope**
  - Use `local` **inside functions** for locals.
  - At top-level, simple assignments create globals.

- **Attributes (Bash/ksh/zsh only)**
  - Use `declare` **or** `typeset` to add attributes:
    - `-i` integer, `-a` array, `-A` assoc array, `-l` lower, `-u` upper, `-r` readonly, `-x` export, `-g` global (bash/zsh).
  - In **bash**, `typeset` ≈ `declare`. Prefer `declare` for clarity in bash; use `typeset` if targeting ksh/zsh too.

- **Intent**
  - Use **`readonly`** for constants.
  - Use **`export`** only if a child process needs the value.

- **Portability**
  - `typeset`/`declare` are **not POSIX**. For `/bin/sh` portability, avoid them (and arrays) and stick to plain assignments + `export`/`readonly`.

**Examples:**

```bash
# Top-level constants & environment
readonly SCRIPT_NAME="$(basename "$0" .sh)"
readonly DEFAULT_TIMEOUT=60
export PATH="/usr/local/bin:$PATH"   # Export only when needed by children

# Function locals with attributes (bash)
do_work() {
  local -i retries=0 max=5
  local -A meta=()                  # bash 4+
  local -a files=()
  local -l env="${ENVIRONMENT:-dev}"  # always-lowercased on assignment
}

# Same using declare/typeset
do_work2() {
  declare -i retries=0 max=5
  declare -A meta=()
  typeset -a files=()
}

# Make a global from inside a function (rare):
set_flag() { declare -g BUILD_FLAG=1; }
```

## Output Formatting

```bash
# Colors (check if terminal supports them)
if [[ -t 2 ]]; then
  readonly RED=$'\033[0;31m'
  readonly GREEN=$'\033[0;32m'
  readonly YELLOW=$'\033[0;33m'
  readonly BLUE=$'\033[0;34m'
  readonly NC=$'\033[0m'
else
  readonly RED=''
  readonly GREEN=''
  readonly YELLOW=''
  readonly BLUE=''
  readonly NC=''
fi

# Logging functions
log() { printf "%s[INFO]%s %s\n" "${BLUE}" "${NC}" "$*" >&2; }
success() { printf "%s[OK]%s %s\n" "${GREEN}" "${NC}" "$*" >&2; }
warn() { printf "%s[WARN]%s %s\n" "${YELLOW}" "${NC}" "$*" >&2; }
error() { printf "%s[ERROR]%s %s\n" "${RED}" "${NC}" "$*" >&2; }

# Progress indicator
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}
```

## User Interaction

```bash
# Confirm action
confirm() {
    local message="${1:-Are you sure?}"
    local default="${2:-n}"
    
    if [[ "$default" == "y" ]]; then
        read -rp "$message [Y/n] " response
        [[ "$response" =~ ^[Nn] ]] && return 1
    else
        read -rp "$message [y/N] " response
        [[ ! "$response" =~ ^[Yy] ]] && return 1
    fi
    return 0
}

# Select from options
select_option() {
    local prompt="$1"
    shift
    local options=("$@")
    
    echo "$prompt"
    PS3="Enter selection: "
    select opt in "${options[@]}"; do
        [[ -n "$opt" ]] && { echo "$opt"; return 0; }
        echo "Invalid selection"
    done
}

# Usage
if confirm "Deploy to production?" "n"; then
    deploy_prod
fi

choice=$(select_option "Select environment:" "dev" "staging" "prod")
```

## Exit Codes

```bash
# Standard exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_ERROR=1
readonly EXIT_USAGE=2
readonly EXIT_MISSING_DEP=3
readonly EXIT_CONFIG_ERROR=4

die() {
    error "$*"
    exit $EXIT_ERROR
}

die_usage() {
    error "$*"
    show_help >&2
    exit $EXIT_USAGE
}

# Check dependencies
check_deps() {
    local deps=("docker" "kubectl" "jq")
    local missing=()
    
    for dep in "${deps[@]}"; do
        command -v "$dep" >/dev/null 2>&1 || missing+=("$dep")
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing[*]}"
        exit $EXIT_MISSING_DEP
    fi
}
```

## Configuration

```bash
# Load config file
load_config() {
    local config_file="${1:-config.yaml}"
    
    [[ ! -f "$config_file" ]] && die "Config not found: $config_file"
    
    # Simple key=value config
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        export "CFG_$key=$value"
    done < "$config_file"
}

# Environment variable fallback
get_config() {
    local key="$1"
    local default="${2:-}"
    local env_var="CFG_$key"
    echo "${!env_var:-$default}"
}
```

## Subcommands

```bash
cmd_init() {
    local name="${1:-}"
    [[ -z "$name" ]] && die_usage "init requires a project name"
    
    log "Initializing project: $name"
    mkdir -p "$name"
    # Initialize project...
    success "Project $name initialized"
}

cmd_build() {
    log "Building project..."
    # Build logic...
    success "Build complete"
}

cmd_deploy() {
    log "Deploying to $ENV..."
    if $DRY_RUN; then
        warn "Dry run - no changes made"
        return
    fi
    # Deploy logic...
    success "Deployed to $ENV"
}

main() {
    parse_args "$@"
    
    case "$COMMAND" in
        init) cmd_init "${ARGS[@]}" ;;
        build) cmd_build "${ARGS[@]}" ;;
        deploy) cmd_deploy "${ARGS[@]}" ;;
        *) die_usage "Unknown command: $COMMAND" ;;
    esac
}

main "$@"
```
