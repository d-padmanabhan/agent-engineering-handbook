#!/usr/bin/env bash
# Batch setup Agent Engineering Handbook for all git repos under a parent directory.
#
# Usage:
#   ./setup-all-repos.sh [OPTIONS] [parent-workspace]
#
# Examples:
#   ./setup-all-repos.sh ~/code
#   ./setup-all-repos.sh -S -l --ensure-gitignore ~/code

set -euo pipefail
IFS=$'\n\t'

if [[ -t 1 ]]; then
  RED=$'\033[0;31m'
  GREEN=$'\033[0;32m'
  YELLOW=$'\033[0;33m'
  BLUE=$'\033[0;34m'
  CYAN=$'\033[0;36m'
  NC=$'\033[0m'
else
  RED= GREEN= YELLOW= BLUE= CYAN= NC=
fi

usage() {
  cat << 'EOF'
Usage: setup-all-repos.sh [OPTIONS] [parent-workspace]

Finds git repos under parent-workspace (max depth 2) and runs setup-workspace.sh for each.

Options (passed through to setup-workspace.sh):
  -S, --symlink-all
  -l, --lightweight
  -f, --full
  --ensure-gitignore
  -h, --help

Examples:
  ./setup-all-repos.sh -S -l ~/code
  ./setup-all-repos.sh -S -f --ensure-gitignore ~/code
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup-workspace.sh"

if [[ ! -f "$SETUP_SCRIPT" ]]; then
  echo "${RED}Error: setup script not found: $SETUP_SCRIPT${NC}" >&2
  exit 1
fi

PARENT_WORKSPACE="$(pwd)"
SETUP_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    -S | --symlink-all | -l | --lightweight | -f | --full | --ensure-gitignore)
      SETUP_ARGS+=("$1")
      shift
      ;;
    -*)
      echo "${RED}Error: Unknown option: $1${NC}" >&2
      usage >&2
      exit 1
      ;;
    *)
      PARENT_WORKSPACE="$1"
      shift
      ;;
  esac
done

if [[ ! -d "$PARENT_WORKSPACE" ]]; then
  echo "${RED}Error: Parent workspace directory not found: $PARENT_WORKSPACE${NC}" >&2
  exit 1
fi

PARENT_WORKSPACE="$(cd "$PARENT_WORKSPACE" && pwd)"

echo "${BLUE}Setting up Cursor rules for repos under:${NC}"
echo "${CYAN}${PARENT_WORKSPACE}${NC}"
echo ""

repos=()
while IFS= read -r -d '' git_dir; do
  repos+=("$(dirname "$git_dir")")
done < <(find "$PARENT_WORKSPACE" -maxdepth 2 -type d -name ".git" -print0)

if [[ ${#repos[@]} -eq 0 ]]; then
  echo "${YELLOW}No git repositories found.${NC}"
  exit 0
fi

echo "${GREEN}Found ${#repos[@]} repository(ies).${NC}"
echo "${YELLOW}Press Enter to continue, or Ctrl+C to cancel...${NC}"
read -r

success_count=0
skip_count=0
error_count=0

for repo_dir in "${repos[@]}"; do
  repo_rel_path="${repo_dir#$PARENT_WORKSPACE/}"
  echo -n "${BLUE}[${repo_rel_path}]${NC} "

  # Skip if already present (symlink or dir)
  if [[ -L "${repo_dir}/.cursor/rules" ]] || [[ -d "${repo_dir}/.cursor/rules" ]]; then
    echo "${YELLOW}Already set up, skipping.${NC}"
    ((skip_count++))
    continue
  fi

  if "$SETUP_SCRIPT" "${SETUP_ARGS[@]}" "$repo_dir" > /dev/null 2>&1; then
    echo "${GREEN}✓ Setup complete${NC}"
    ((success_count++))
  else
    echo "${RED}✗ Setup failed${NC}"
    ((error_count++))
  fi
done

echo ""
echo "${GREEN}Setup Summary:${NC}"
echo "  ${GREEN}✓ Success:${NC} $success_count"
echo "  ${YELLOW}⊘ Skipped:${NC} $skip_count"
echo "  ${RED}✗ Errors:${NC} $error_count"

if [[ $error_count -gt 0 ]]; then
  exit 1
fi
