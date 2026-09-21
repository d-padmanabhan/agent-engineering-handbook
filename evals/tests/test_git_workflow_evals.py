"""Regression tests for Git workflow eval assertions."""

import tempfile
import unittest
from pathlib import Path

from evals.skill_eval import AdapterResponse, EvalCase, evaluate_checks, load_eval_suite

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GIT_WORKFLOW_SKILL_DIRECTORY = REPOSITORY_ROOT / "skills" / "git-workflow"


class GitWorkflowEvalTests(unittest.TestCase):
    """Ensure commit preparation preserves concurrent session work."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the Git workflow eval suite once."""
        suite = load_eval_suite(GIT_WORKFLOW_SKILL_DIRECTORY)
        if suite is None:
            raise AssertionError("git-workflow eval suite is missing")
        cls.cases = {case.identifier: case for case in suite.cases}

    def failed_check_ids(self, case: EvalCase, output: str) -> set[str]:
        """Return failed required check identifiers for one response."""
        response = AdapterResponse(output=output, events=(), usage={}, raw={})
        with tempfile.TemporaryDirectory() as temp_directory:
            results = evaluate_checks(
                case.checks,
                response,
                Path(temp_directory),
                default_skill="git-workflow",
            )
        return {result.identifier for result in results if result.required and not result.passed}

    def test_concurrent_session_expected_output_satisfies_checks(self) -> None:
        """Confirm the concurrent-session response satisfies its checks."""
        case = self.cases[4]

        self.assertEqual(set(), self.failed_check_ids(case, case.expected_output))

    def test_rejects_absorbing_every_worktree_change(self) -> None:
        """Require provenance-aware staging after hooks and upgrades."""
        output = "Run git add -A and commit api.go, billing.go, migration.sql, tool.toml, and tool.lock."

        failed = self.failed_check_ids(self.cases[4], output)

        self.assertIn("preserves-concurrent-session-work", failed)
        self.assertIn("rejects-broad-staging", failed)
        self.assertIn("includes-induced-task-changes", failed)
        self.assertIn("reviews-and-reverifies-induced-diff", failed)
        self.assertIn("previews-exact-staged-scope", failed)

    def test_repository_root_expected_output_satisfies_checks(self) -> None:
        """Confirm the canonical repository-root response satisfies its checks."""
        case = self.cases[5]

        self.assertEqual(set(), self.failed_check_ids(case, case.expected_output))

    def test_rejects_current_directory_as_repository_root(self) -> None:
        """Require root discovery that works from nested directories."""
        output = "Use pwd as the repository root and write .agent/reports relative to it."

        failed = self.failed_check_ids(self.cases[5], output)

        self.assertIn("uses-canonical-root-assignment", failed)
        self.assertIn("quotes-root-references", failed)
        self.assertIn("rejects-cwd-assumptions", failed)


if __name__ == "__main__":
    unittest.main()
