#!/usr/bin/env bash
# Setup Agent Engineering Handbook in a workspace.
#
# Supports the recommended model:
# - Workspace uses a symlink: <workspace>/.cursor/rules -> <this-repo>/rules
# - Workspace context files live in: <workspace>/tmp/ (gitignored)
#
# Usage:
#   ./setup-workspace.sh -S -l /path/to/workspace
#
# Notes:
# - This script is intentionally self-contained and path-agnostic.
# - It does NOT modify remote git state.

set -euo pipefail
IFS=$'\n\t'

# Colors (only when stdout is a terminal)
if [[ -t 1 ]]; then
  RED=$'\033[0;31m'
  GREEN=$'\033[0;32m'
  YELLOW=$'\033[0;33m'
  CYAN=$'\033[0;36m'
  NC=$'\033[0m'
else
  RED= GREEN= YELLOW= CYAN= NC=
fi

usage() {
  cat << 'EOF'
Usage: setup-workspace.sh [OPTIONS] <workspace-path>

Sets up Cursor rules + workspace context files.

Options:
  -S, --symlink-all       Symlink <workspace>/.cursor/rules to this repo's rules/ (recommended)
  -l, --lightweight       Create only tmp/tasks.md
  -f, --full              Create tmp/tasks.md, active-context.md, progress.md, project-brief.md
  --rules-source DIR      Override rules directory (defaults to <repo>/rules)
  --ensure-gitignore      Ensure "tmp/" is present in workspace .gitignore (append if needed)
  -h, --help              Show help

Examples:
  ./setup-workspace.sh -S -l .
  ./setup-workspace.sh -S -f /path/to/repo
  ./setup-workspace.sh -S -f --ensure-gitignore /path/to/repo
EOF
}

SYMLINK_ALL=false
LIGHTWEIGHT=false
FULL=false
ENSURE_GITIGNORE=false
RULES_SOURCE_OVERRIDE=""
WORKSPACE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    -S | --symlink-all)
      SYMLINK_ALL=true
      shift
      ;;
    -l | --lightweight)
      LIGHTWEIGHT=true
      shift
      ;;
    -f | --full)
      FULL=true
      shift
      ;;
    --rules-source)
      RULES_SOURCE_OVERRIDE="${2:-}"
      shift 2
      ;;
    --ensure-gitignore)
      ENSURE_GITIGNORE=true
      shift
      ;;
    -*)
      echo "${RED}Error: Unknown option: $1${NC}" >&2
      usage >&2
      exit 1
      ;;
    *)
      WORKSPACE="$1"
      shift
      ;;
  esac
done

if [[ -z "$WORKSPACE" ]]; then
  echo "${RED}Error: workspace-path is required${NC}" >&2
  usage >&2
  exit 1
fi

if [[ ! -d "$WORKSPACE" ]]; then
  echo "${RED}Error: Workspace directory does not exist: $WORKSPACE${NC}" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_RULES_DIR="${SCRIPT_DIR}/rules"
SOURCE_RULES_DIR="${RULES_SOURCE_OVERRIDE:-$DEFAULT_RULES_DIR}"
SOURCE_TEMPLATES_DIR="${SOURCE_RULES_DIR}/templates"

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
CURSOR_RULES_DIR="${WORKSPACE}/.cursor/rules"
TMP_DIR="${WORKSPACE}/tmp"

if [[ ! -d "$SOURCE_RULES_DIR" ]]; then
  echo "${RED}Error: rules source directory not found: ${SOURCE_RULES_DIR}${NC}" >&2
  exit 1
fi

if [[ ! -d "$SOURCE_TEMPLATES_DIR" ]]; then
  echo "${RED}Error: templates directory not found: ${SOURCE_TEMPLATES_DIR}${NC}" >&2
  echo "${YELLOW}Expected templates at: <rules>/templates/*.template${NC}" >&2
  exit 1
fi

echo "${CYAN}Workspace:${NC} $WORKSPACE"
echo "${CYAN}Rules source:${NC} $SOURCE_RULES_DIR"

if [[ "$SYMLINK_ALL" == true ]]; then
  # Ensure parent exists
  mkdir -p "$(dirname "$CURSOR_RULES_DIR")"

  if [[ -e "$CURSOR_RULES_DIR" ]] && [[ ! -L "$CURSOR_RULES_DIR" ]]; then
    echo "${YELLOW}⚠${NC} .cursor/rules exists and is not a symlink"
    echo "${YELLOW}⚠${NC} Backing up to .cursor/rules.backup"
    mv "$CURSOR_RULES_DIR" "${CURSOR_RULES_DIR}.backup"
  fi

  if [[ -L "$CURSOR_RULES_DIR" ]]; then
    echo "${YELLOW}⚠${NC} .cursor/rules already symlinked, skipping"
  else
    ln -s "$SOURCE_RULES_DIR" "$CURSOR_RULES_DIR"
    echo "${GREEN}✓${NC} Symlinked .cursor/rules -> $SOURCE_RULES_DIR"
  fi
else
  echo "${YELLOW}⚠${NC} No rule installation method selected."
  echo "${YELLOW}⚠${NC} Re-run with --symlink-all to install rules.${NC}"
fi

# Decide default: if neither is specified, use lightweight.
if [[ "$LIGHTWEIGHT" == false && "$FULL" == false ]]; then
  LIGHTWEIGHT=true
fi

# Ensure tmp directory exists
mkdir -p "$TMP_DIR"

create_from_template() {
  local template_basename="$1" # e.g. tasks.md
  local dest_path="$2"         # e.g. /workspace/tmp/tasks.md
  local src_path="${SOURCE_TEMPLATES_DIR}/${template_basename}.template"

  if [[ -f "$dest_path" ]]; then
    echo "${YELLOW}⚠${NC} Exists, skipping: ${dest_path}"
    return 0
  fi
  if [[ ! -f "$src_path" ]]; then
    echo "${YELLOW}⚠${NC} Missing template, skipping: ${src_path}"
    return 0
  fi
  cp "$src_path" "$dest_path"
  echo "${GREEN}✓${NC} Created ${dest_path}"
}

if [[ "$LIGHTWEIGHT" == true ]]; then
  create_from_template "tasks.md" "${TMP_DIR}/tasks.md"
else
  create_from_template "tasks.md" "${TMP_DIR}/tasks.md"
  create_from_template "active-context.md" "${TMP_DIR}/active-context.md"
  create_from_template "progress.md" "${TMP_DIR}/progress.md"
  create_from_template "project-brief.md" "${TMP_DIR}/project-brief.md"
fi

if [[ "$ENSURE_GITIGNORE" == true ]]; then
  if [[ -d "${WORKSPACE}/.git" ]]; then
    GITIGNORE_PATH="${WORKSPACE}/.gitignore"
    if [[ ! -f "$GITIGNORE_PATH" ]]; then
      printf "%s\n" "tmp/" > "$GITIGNORE_PATH"
      echo "${GREEN}✓${NC} Created .gitignore with tmp/"
    elif ! grep -qE '(^|/)\s*tmp/\s*$' "$GITIGNORE_PATH"; then
      {
        echo ""
        echo "# Private/local documentation"
        echo "tmp/"
      } >> "$GITIGNORE_PATH"
      echo "${GREEN}✓${NC} Appended tmp/ to .gitignore"
    else
      echo "${YELLOW}⚠${NC} .gitignore already contains tmp/"
    fi
  else
    echo "${YELLOW}⚠${NC} Not a git repo (no .git); skipping .gitignore update"
  fi
fi

echo ""
echo "${GREEN}Setup complete.${NC}"
echo ""
echo "Next steps:"
echo "  - Open the workspace in Cursor"
echo "  - Context files are in: ${TMP_DIR}"
echo "  - Rules are in: ${WORKSPACE}/.cursor/rules"
