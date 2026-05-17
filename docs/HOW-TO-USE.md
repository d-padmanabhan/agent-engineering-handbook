# How to Use Agent Engineering Handbook

This guide explains how to integrate Agent Engineering Handbook into your projects.

---

## Table of Contents

1. [Understanding Rule Loading](#understanding-rule-loading)
2. [Installation Methods](#installation-methods)
3. [Configuration Strategies](#configuration-strategies)
4. [Rule Selection Guide](#rule-selection-guide)
5. [Testing Your Setup](#testing-your-setup)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Understanding Rule Loading

Cursor supports two approaches for loading rules. Understanding the difference helps you choose the right setup.

### Approach A: Frontmatter-based (Automatic)

Rules placed in `.cursor/rules/` with `alwaysApply: true` in their frontmatter load automatically. **No `.cursorrules` file needed.**

```yaml
# Example frontmatter in a .mdc file
---
title: Core Coding Standards
alwaysApply: true
priority: 100
---
```

**When to use:**

- Personal setup with rules symlinked to `~/.cursor/rules/`
- You want core rules to always apply without configuration
- You prefer convention over configuration

**Rules with `alwaysApply: true` in this repo:**

| Rule | Purpose |
|------|---------|
| `010-workflow.mdc` | Plan/Implement/Review workflow |
| `015-context-engineering.mdc` | Prompt packing, retrieval, compaction |
| `020-agent-audit.mdc` | Agent audit requirements |
| `100-core.mdc` | Core coding standards |
| `130-git.mdc` | Git conventions |
| `120-utilities.mdc` | CLI tools |
| `110-configuration.mdc` | Configuration management |
| `310-security.mdc` | Security best practices |
| `316-zero-trust.mdc` | Distinguished Engineer - Zero Trust |
| `800-markdown.mdc` | Markdown formatting |

Rules without `alwaysApply: true` load based on file patterns (e.g., `200-python.mdc` loads when editing `.py` files) or when explicitly requested.

### Approach B: Explicit `.cursorrules` File

A `.cursorrules` file in your project root gives you explicit control over which rules load.

```yaml
# Option 1: Load all rules from a directory
rulesDirectory: .cursor/rules

# Option 2: Explicit list of rules
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc
```

**When to use:**

- Team projects where you want consistent, version-controlled configuration
- You want to load only a specific subset of rules
- Different projects need different rule combinations

> [!IMPORTANT]
> When using `.cursorrules`, rules with `alwaysApply: true` still load automatically in addition to your explicit list. You cannot disable `alwaysApply` rules via `.cursorrules`.

### Choosing an Approach

| Scenario | Recommended Approach |
|----------|---------------------|
| Personal setup, all projects | Symlink to `~/.cursor/rules/` (Approach A) |
| Team project, shared config | `.cursorrules` in git (Approach B) |
| Project-specific subset | `.cursorrules` with explicit list (Approach B) |
| Mixed (global + project) | Both: symlink globals + `.cursorrules` for project-specific additions |

---

## Installation Methods

### Setup script (convenience)

If you keep this repo as a shared checkout (or as a submodule), you can run:

```bash
/path/to/agent-engineering-handbook/setup-workspace.sh -S -l .
```

### Method 1: Symlink (Recommended for Multiple Projects)

**Advantages:**

- Update rules once, all projects benefit
- No duplication
- Easy maintenance

**Setup:**

```bash
# Clone the repository
git clone https://github.com/d-padmanabhan/agent-engineering-handbook.git
cd /path/to/your/workspace

# From your project
cd /path/to/your/project
mkdir -p .cursor
ln -s /absolute/path/to/agent-engineering-handbook/rules .cursor/rules

# Verify
ls -la .cursor/rules
```

Rules with `alwaysApply: true` load automatically. No `.cursorrules` file needed.

**Optional:** Add `.cursorrules` if you want explicit control (see [Approach B](#approach-b-explicit-cursorrules-file)).

---

### Method 2: Copy Rules (Recommended for Single Project)

**Advantages:**

- Self-contained project
- Version control rules with project
- Custom modifications per project

**Setup:**

```bash
# From your project
cd /path/to/your/project
mkdir -p .cursor/rules

# Copy all rules
cp /path/to/agent-engineering-handbook/rules/*.mdc .cursor/rules/

# Or copy specific rules
cp /path/to/agent-engineering-handbook/rules/200-python.mdc .cursor/rules/
cp /path/to/agent-engineering-handbook/rules/410-aws.mdc .cursor/rules/

# (Optional) Copy workflow templates (tasks, active-context, etc.)
mkdir -p .cursor/rules/templates
cp /path/to/agent-engineering-handbook/rules/templates/*.template .cursor/rules/templates/
```

Rules with `alwaysApply: true` load automatically.

**Optional:** Add `.cursorrules` for explicit rule selection:

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc
```

---

### Method 3: Git Submodule (Recommended for Team Projects)

**Advantages:**

- Track specific version
- Easy updates via git
- Team consistency

**Setup:**

```bash
# From your project
cd /path/to/your/project

# Add as submodule
git submodule add https://github.com/d-padmanabhan/agent-engineering-handbook.git .cursor-rules

# Symlink to .cursor/rules
mkdir -p .cursor
ln -s ../.cursor-rules/rules .cursor/rules

# Team members clone with submodules
git clone --recurse-submodules <your-project-url>

# Or update existing clone
git submodule init
git submodule update
```

**Update rules:**

```bash
cd .cursor-rules
git pull origin main
cd ..
git add .cursor-rules
git commit -m "chore: update cursor rules"
```

---

## Configuration Strategies

### Strategy 1: Load All Rules (Comprehensive)

**Use when:**

- Large, complex projects
- Multiple technologies in one repo
- Want maximum guidance

**Configuration:**

```yaml
# .cursorrules
rulesDirectory: .cursor/rules
```

**Pros:**

- No maintenance needed
- All patterns available
- Consistent standards

**Cons:**

- May load unnecessary rules
- Slightly slower (negligible)

---

### Strategy 2: Selective Loading (Focused)

**Use when:**

- Clear technology stack
- Want faster rule loading
- Smaller projects

**Configuration:**

```yaml
# .cursorrules
rules:
  # Core (always include)
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/310-security.mdc
  
  # Your stack
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc
  - .cursor/rules/180-terraform.mdc
  
  # Optional
  - .cursor/rules/300-testing.mdc
  - .cursor/rules/810-documentation.mdc
```

**Pros:**

- Faster loading
- Clear dependencies
- Easy to understand

**Cons:**

- Manual maintenance
- May miss relevant rules

---

### Strategy 3: Progressive Enhancement (Start Small)

**Use when:**

- New to Cursor rules
- Evaluating value
- Small projects

**Phase 1: Core Only**

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
```

**Phase 2: Add Language**

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/200-python.mdc  # Your primary language
```

**Phase 3: Add Platform**

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc     # Your cloud platform
```

**Phase 4: Add Patterns**

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc
  - .cursor/rules/310-security.mdc
  - .cursor/rules/300-testing.mdc
```

---

## Rule Selection Guide

### By Project Type

#### Web Application (Full-Stack)

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/240-typescript.mdc     # Frontend
  - .cursor/rules/200-python.mdc         # Backend
  - .cursor/rules/470-postgresql.mdc     # Database
  - .cursor/rules/320-api-design.mdc     # API patterns
  - .cursor/rules/310-security.mdc       # Security
  - .cursor/rules/300-testing.mdc        # Testing
```

#### Microservices (Go + Kubernetes)

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/210-go.mdc
  - .cursor/rules/450-kubernetes.mdc
  - .cursor/rules/440-docker.mdc
  - .cursor/rules/330-observability.mdc
  - .cursor/rules/310-security.mdc
  - .cursor/rules/300-testing.mdc
```

#### Infrastructure/Platform Engineering

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/140-bash.mdc
  - .cursor/rules/180-terraform.mdc
  - .cursor/rules/450-kubernetes.mdc
  - .cursor/rules/160-github-actions.mdc
  - .cursor/rules/310-security.mdc
```

#### Data Engineering

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/470-postgresql.mdc
  - .cursor/rules/410-aws.mdc           # or 420-gcp.mdc
  - .cursor/rules/300-testing.mdc
```

#### AI/ML Application

```yaml
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/500-ai-ml.mdc
  - .cursor/rules/510-mcp-servers.mdc
  - .cursor/rules/410-aws.mdc           # Bedrock
  - .cursor/rules/310-security.mdc
```

---

## Testing Your Setup

### 1. Verify Rules Are Loaded

Open Cursor and check:

1. Go to Settings -> Rules & Memories
2. Verify your rules appear in the list
3. Check that `alwaysApply` rules are marked

### 2. Test Code Generation

Ask Cursor to generate code that exercises your rules:

**Test Python rules:**

```
Generate a Python function to fetch data from an API with proper error handling, type hints, and async support.
```

**Test AWS rules:**

```
Create a Terraform module for an S3 bucket with versioning, encryption, and lifecycle policies.
```

**Test Security rules:**

```
Create a REST API endpoint with authentication, input validation, and rate limiting.
```

### 3. Verify Rule Application

Check that generated code follows patterns:

- Proper error handling
- Type annotations
- Security best practices
- Documentation
- Tests

---

## Troubleshooting

### Rules Not Loading

**Symptom:** Cursor ignores your rules

**Solutions:**

1. **Check file paths**

   ```bash
   ls -la .cursor/rules/
   cat .cursorrules
   ```

2. **Verify symlink** (if using symlinks)

   ```bash
   readlink .cursor/rules
   # Should show absolute path to rules directory
   ```

3. **Restart Cursor**
   - Quit completely (not just close window)
   - Reopen project

4. **Check Cursor settings**
   - Settings -> Rules & Memories
   - Ensure rules are enabled

### Rules Conflict

**Symptom:** Unexpected code generation patterns

**Solutions:**

1. **Check rule order**
   - Later rules override earlier ones
   - Put more specific rules last

2. **Check `alwaysApply` rules**
   - These load automatically
   - May conflict with selective loading

3. **Use local overrides**
   - Create `999-local-overrides.mdc`
   - Override conflicting patterns

### Performance Issues

**Symptom:** Cursor is slow

**Solutions:**

1. **Reduce rules**
   - Use selective loading
   - Only load rules for your stack

2. **Optimize rule files**
   - Remove unused sections
   - Split large files

---

## Advanced Usage

### Custom Rule Development

Create project-specific rules:

```bash
# Create custom rule
vim .cursor/rules/999-local-overrides.mdc
```

```markdown
---
title: Project-Specific Overrides
description: Custom patterns for this project
priority: 999
alwaysApply: true
---

# Project Overrides

## Custom Pattern 1
[Your specific requirements]
```

### Environment-Specific Rules

Use different rules per environment:

```bash
# Development
cp .cursorrules.dev .cursorrules

# Production
cp .cursorrules.prod .cursorrules
```

### Multi-Repo Workspaces

When you have many repositories (e.g., 100 repos in a parent directory) with global rules in `~/.cursor/rules`, here's how selective loading works:

#### What Loads Automatically

Rules with `alwaysApply: true` load for **every** repository:

| Rule | Purpose |
|------|---------|
| `010-workflow.mdc` | Plan/Implement/Review workflow |
| `015-context-engineering.mdc` | Prompt packing, retrieval, compaction |
| `020-agent-audit.mdc` | Agent audit requirements |
| `100-core.mdc` | Core coding standards |
| `130-git.mdc` | Git conventions |
| `120-utilities.mdc` | CLI tools |
| `110-configuration.mdc` | Configuration management |
| `310-security.mdc` | Security best practices |
| `316-zero-trust.mdc` | Distinguished Engineer - Zero Trust |
| `800-markdown.mdc` | Markdown formatting |

These cannot be disabled per-repo.

#### File Pattern-Based Loading

Other rules use file patterns in their frontmatter and load automatically when you open matching files:

```yaml
# Example frontmatter from 200-python.mdc
---
title: Python Best Practices
alwaysApply: false
files:
  include:
    - "**/*.py"
    - "**/pyproject.toml"
---
```

| You open... | Rules that auto-load |
|-------------|---------------------|
| `*.py`, `pyproject.toml` | `200-python.mdc` |
| `*.tf`, `*.tfvars` | `180-terraform.mdc` |
| `*.go`, `go.mod` | `210-go.mdc` |
| `*.ts`, `*.tsx` | `240-typescript.mdc` |
| `*.js`, `*.jsx` | `230-javascript.mdc` |
| `Dockerfile`, `docker-compose.yml` | `440-docker.mdc` |
| `*.yaml` in `.github/workflows/` | `160-github-actions.mdc` |

**This means most repos need zero configuration.** Open a Python file, Python rules load. Open a Go file, Go rules load.

#### Per-Repo Explicit Control

For repos that need specific rule combinations, add a `.cursorrules` file:

```yaml
# python-aws-repo/.cursorrules
rules:
  - ~/.cursor/rules/200-python.mdc
  - ~/.cursor/rules/410-aws.mdc
  - ~/.cursor/rules/180-terraform.mdc
```

```yaml
# go-k8s-repo/.cursorrules
rules:
  - ~/.cursor/rules/210-go.mdc
  - ~/.cursor/rules/450-kubernetes.mdc
  - ~/.cursor/rules/440-docker.mdc
```

#### Per-Repo Overrides

For repos that need custom patterns on top of global rules:

```bash
# Create repo-specific overrides
mkdir -p .cursor/rules
cat > .cursor/rules/999-local-overrides.mdc << 'EOF'
---
title: Repo-Specific Overrides
priority: 999
alwaysApply: true
---

# Project Overrides

## Custom Patterns
- This repo uses MongoDB instead of PostgreSQL
- API responses use camelCase, not snake_case
EOF
```

#### Recommended Directory Structure

```
~/.cursor/rules/              <- Global (symlink to agent-engineering-handbook)
  ├── 100-core.mdc            <- alwaysApply: true (all repos)
  ├── 200-python.mdc          <- loads when *.py opened
  ├── 210-go.mdc              <- loads when *.go opened
  └── ...

~/code/
  ├── repo-a/                 <- Python project
  │   └── (no config needed, file patterns handle it)
  │
  ├── repo-b/                 <- Go + K8s project
  │   └── .cursorrules        <- explicit rule list
  │
  └── repo-c/                 <- Has custom requirements
      └── .cursor/rules/
          └── 999-local-overrides.mdc
```

#### Decision Guide

| Scenario | Solution |
|----------|----------|
| Standard project, single language | No config needed (file patterns work) |
| Multi-language project | No config needed (each file type loads its rules) |
| Need specific cloud/platform rules | Add `.cursorrules` with explicit list |
| Need to override global patterns | Add `999-local-overrides.mdc` |
| Team project, need consistency | Commit `.cursorrules` to git |

### Team Standardization

For team projects:

1. **Commit `.cursorrules` to git**

   ```bash
   git add .cursorrules
   git commit -m "chore: add cursor rules configuration"
   ```

2. **Document in README**

   ```markdown
   ## Development Setup
   
   This project uses Agent Engineering Handbook:
   1. Clone with submodules: `git clone --recurse-submodules <url>`
   2. Rules are automatically loaded from `.cursor/rules`
   3. See `.cursorrules` for configuration
   ```

3. **Add to onboarding**
   - Include in team documentation
   - Mention in pull request templates
   - Reference in code review checklist

---

## Quick Reference

### Essential Commands

```bash
# Setup (symlink method)
ln -s /path/to/agent-engineering-handbook/rules .cursor/rules

# Update rules (git submodule)
git submodule update --remote .cursor-rules

# Verify setup
ls -la .cursor/rules
cat .cursorrules

# Test
# (Ask Cursor to generate code)
```

### Key Files

- `.cursorrules` - Configuration file
- `.cursor/rules/` - Rules directory
- `999-local-overrides.mdc` - Project-specific rules

### Documentation

- [README.md](../README.md) - Overview
- [CONTRIBUTING.md](../.github/CONTRIBUTING.md) - Contributing guidelines
- [rules/INDEX.md](../rules/INDEX.md) - Rule catalog

---

**Need Help?** Open an issue on [GitHub](https://github.com/d-padmanabhan/agent-engineering-handbook/issues)
