# Scripts

Utility scripts for Cursor IDE maintenance and management.

## Available Scripts

### `cursor-maintenance.sh`

Cleans Cursor cache, logs, and temporary files to reclaim disk space.

**Usage:**

```bash
./scripts/cursor-maintenance.sh [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-n, --dry-run` | Show what would be deleted without actually deleting |
| `-v, --verbose` | Enable verbose output |
| `-a, --aggressive` | Include additional cleanup (terminal history, backups) |
| `-h, --help` | Show help message |

**Examples:**

```bash
# Preview what would be cleaned
./scripts/cursor-maintenance.sh -n

# Standard cleanup
./scripts/cursor-maintenance.sh

# Aggressive cleanup with verbose output
./scripts/cursor-maintenance.sh -a -v
```

**What Gets Cleaned:**

| Mode | Directories |
|------|-------------|
| **Standard** | `cache/`, `CachedData/`, `CachedExtensionVSIXs/`, `Code Cache/`, `GPUCache/`, `logs/` |
| **Aggressive** | Standard + `Backups/`, `projects/*/terminals/` |

**What's Protected:**

- User settings (`User/settings.json`)
- Extensions
- Keybindings
- MCP configuration
- Rules

> [!TIP]
> Run weekly or when Cursor feels sluggish. Close Cursor before running for best results.

### `cursor-hooks-install.sh`

Installs the optional Cursor hooks pack from this repo into either:

- `~/.cursor/` (user hooks), or
- a specific project’s `.cursor/` directory (project hooks)

This script is idempotent and merges into an existing `hooks.json` by default (with a timestamped backup).

**Usage:**

```bash
# Install globally (user hooks)
./scripts/cursor-hooks-install.sh --user

# Install into a specific repo (project hooks)
./scripts/cursor-hooks-install.sh --project /path/to/repo

# Preview actions
./scripts/cursor-hooks-install.sh --user --dry-run
```

## Installation

The scripts are ready to use from this repository:

```bash
# Run directly
/path/to/agent-engineering-handbook/scripts/cursor-maintenance.sh

# Or add to PATH
export PATH="$PATH:/path/to/agent-engineering-handbook/scripts"
cursor-maintenance.sh
```

## Adding New Scripts

When adding new scripts:

1. Follow [140-bash.mdc](../rules/140-bash.mdc) standards
2. Include `--help` documentation
3. Support `--dry-run` for destructive operations
4. Pass `shellcheck` validation
5. Update this README
