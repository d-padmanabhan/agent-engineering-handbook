"""Regression tests for skills-canonical rule ownership."""

import re
import unittest
from pathlib import Path

REPOSITORY_ROOT: Path = Path(__file__).resolve().parents[2]
HANDBOOK_ROOT_ASSIGNMENT: str = 'HANDBOOK_ROOT="${HOME}/.cursor/agent-engineering-handbook"'
HANDBOOK_ROOT_REFERENCE: str = "${HANDBOOK_ROOT}/"
RULE_LINE_BUDGETS: dict[str, int] = {
    "010-workflow.mdc": 100,
    "100-core.mdc": 180,
    "130-git.mdc": 100,
    "140-bash.mdc": 100,
    "200-python.mdc": 100,
    "225-javascript-typescript.mdc": 110,
    "310-security.mdc": 100,
    "320-api-design.mdc": 120,
    "440-docker.mdc": 100,
    "450-kubernetes.mdc": 140,
    "460-helm.mdc": 90,
    "800-markdown.mdc": 90,
    "810-documentation.mdc": 90,
}
SCOPED_RULES: tuple[str, ...] = (
    "140-bash.mdc",
    "200-python.mdc",
    "225-javascript-typescript.mdc",
    "320-api-design.mdc",
    "440-docker.mdc",
    "450-kubernetes.mdc",
    "460-helm.mdc",
    "800-markdown.mdc",
    "810-documentation.mdc",
)
ROUTING_FILES: tuple[Path, ...] = (
    *(REPOSITORY_ROOT / "rules" / name for name in RULE_LINE_BUDGETS),
    REPOSITORY_ROOT / "skills" / "git-workflow" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "containers-orchestration" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "kubernetes-containers" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "kubernetes-operator-development" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "bash-shell-scripting" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "python-development" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "typescript-javascript" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "agent-workflow" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "core-engineering" / "SKILL.md",
    REPOSITORY_ROOT / "skills" / "documentation-standards" / "SKILL.md",
)


class RuleOwnershipTests(unittest.TestCase):
    """Keep rules concise, supported, and free of copied tutorials."""

    def test_gate_rules_stay_within_line_budgets(self) -> None:
        for rule_name, line_budget in RULE_LINE_BUDGETS.items():
            rule_path = REPOSITORY_ROOT / "rules" / rule_name
            with self.subTest(rule=rule_name):
                line_count: int = len(rule_path.read_text(encoding="utf-8").splitlines())
                self.assertLessEqual(line_count, line_budget)

    def test_scoped_rules_use_supported_frontmatter(self) -> None:
        for rule_name in SCOPED_RULES:
            rule = (REPOSITORY_ROOT / "rules" / rule_name).read_text(encoding="utf-8")
            frontmatter: str = rule.split("---", 2)[1]

            with self.subTest(rule=rule_name):
                self.assertIn("globs:", frontmatter)
                self.assertNotIn("\nfiles:", frontmatter)
                self.assertNotIn("alwaysApply: true", frontmatter)

    def test_git_rule_contains_gates_not_tutorials(self) -> None:
        git_rule: str = (REPOSITORY_ROOT / "rules" / "130-git.mdc").read_text(encoding="utf-8")

        self.assertIn("## Commit Authorization and Signing", git_rule)
        self.assertIn("## Branches, History, and Remote Writes", git_rule)
        for removed_heading in (
            "## What is a Ref?",
            "## The Reflog",
            "## Repository Scaffolding",
            "## Git Worktrees & Parallel Development",
        ):
            with self.subTest(heading=removed_heading):
                self.assertNotIn(removed_heading, git_rule)

    def test_docker_rule_contains_gates_not_tutorials(self) -> None:
        docker_rule: str = (REPOSITORY_ROOT / "rules" / "440-docker.mdc").read_text(encoding="utf-8")

        self.assertIn("## Build Cache Contract", docker_rule)
        self.assertIn("## Compose and Publishing", docker_rule)
        for removed_heading in (
            "## Dockerfile Best Practices",
            "## Common Patterns",
            "## Troubleshooting",
            "## Best Practices Checklist",
        ):
            with self.subTest(heading=removed_heading):
                self.assertNotIn(removed_heading, docker_rule)

    def test_kubernetes_rule_routes_operator_workflows(self) -> None:
        kubernetes_rule = (REPOSITORY_ROOT / "rules" / "450-kubernetes.mdc").read_text(encoding="utf-8")
        kubernetes_skill = (REPOSITORY_ROOT / "skills" / "kubernetes-containers" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        operator_reference = "${HANDBOOK_ROOT}/skills/kubernetes-operator-development/SKILL.md"

        self.assertIn(operator_reference, kubernetes_rule)
        self.assertIn(operator_reference, kubernetes_skill)
        self.assertIn("observe-before-create alone is not race-safe", kubernetes_rule)
        self.assertIn("Status identifiers alone are not ownership proof", kubernetes_rule)

    def test_documentation_rule_routes_workflows_without_stale_tutorials(self) -> None:
        documentation_rule = (REPOSITORY_ROOT / "rules" / "810-documentation.mdc").read_text(encoding="utf-8")

        self.assertIn("${HANDBOOK_ROOT}/skills/documentation-standards/SKILL.md", documentation_rule)
        self.assertIn("${HANDBOOK_ROOT}/rules/120-utilities.mdc", documentation_rule)
        self.assertIn("${HANDBOOK_ROOT}/rules/800-markdown.mdc", documentation_rule)
        for stale_content in (
            "## Reading & Researching Documentation",
            "Default: Use Lynx",
            "LightPanda",
            "Puppeteer",
            "```mermaid",
            "(Mermaid)",
        ):
            with self.subTest(content=stale_content):
                self.assertNotIn(stale_content, documentation_rule)

    def test_github_actions_uses_exact_latest_release_tags(self) -> None:
        github_actions_rule = (REPOSITORY_ROOT / "rules" / "160-github-actions.mdc").read_text(encoding="utf-8")
        github_actions_skill = (REPOSITORY_ROOT / "skills" / "cicd-github-actions" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        for content in (github_actions_rule, github_actions_skill):
            with self.subTest(source=content[:40]):
                self.assertIn("releases/latest\" --jq '.tag_name'", content)
                self.assertIn("latest stable release tag", content)
                self.assertNotIn("latest_sha=", content)
                self.assertNotIn("SHA-pinned repository", content)
                self.assertNotIn("Preserve SHA posture", content)

    def test_workflow_publishes_stable_handbook_root(self) -> None:
        workflow_rule: str = (REPOSITORY_ROOT / "rules" / "010-workflow.mdc").read_text(encoding="utf-8")

        self.assertIn(HANDBOOK_ROOT_ASSIGNMENT, workflow_rule)
        self.assertIn(HANDBOOK_ROOT_REFERENCE, workflow_rule)

    def test_handbook_has_no_user_specific_paths(self) -> None:
        personal_root: str = "/Users/" + "Devesh_Padmanabhan"
        excluded_directories: set[str] = {".agent", ".git", ".venv", "__pycache__", "tmp"}

        for file_path in REPOSITORY_ROOT.rglob("*"):
            if not file_path.is_file() or excluded_directories.intersection(file_path.parts):
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            with self.subTest(file=file_path.relative_to(REPOSITORY_ROOT)):
                self.assertNotIn(personal_root, content)

    def test_routing_avoids_relative_markdown_links(self) -> None:
        relative_link_pattern = re.compile(r"\]\((?!https?://|file://|#|mailto:)[^)]+\)")

        for file_path in ROUTING_FILES:
            with self.subTest(file=file_path.relative_to(REPOSITORY_ROOT)):
                content: str = file_path.read_text(encoding="utf-8")
                self.assertIsNone(relative_link_pattern.search(content))

    def test_skills_do_not_claim_unsupported_paths_frontmatter(self) -> None:
        for skill_file in (path for path in ROUTING_FILES if path.name == "SKILL.md"):
            frontmatter: str = skill_file.read_text(encoding="utf-8").split("---", 2)[1]
            with self.subTest(skill=skill_file.parent.name):
                self.assertNotIn("\npaths:", frontmatter)

    def test_retired_language_rules_are_removed(self) -> None:
        for retired_name in ("230-javascript.mdc", "240-typescript.mdc"):
            with self.subTest(rule=retired_name):
                self.assertFalse((REPOSITORY_ROOT / "rules" / retired_name).exists())


if __name__ == "__main__":
    unittest.main()
