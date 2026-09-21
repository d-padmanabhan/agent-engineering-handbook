"""Regression tests for discriminating GitHub Actions CI/CD evals."""

import unittest
from typing import ClassVar

from evals.skill_eval import EvalCase
from evals.tests.eval_test_support import (
    assert_expected_outputs_pass,
    failed_required_check_ids,
    load_cases,
)

SKILL_NAME = "cicd-github-actions"


class CicdGithubActionsEvalTests(unittest.TestCase):
    """Ensure unsafe GitHub Actions guidance cannot pass the eval suite."""

    cases: ClassVar[dict[int, EvalCase]]

    @classmethod
    def setUpClass(cls) -> None:
        """Load the GitHub Actions eval cases once."""
        cls.cases = load_cases(SKILL_NAME)

    def failed_checks(self, case_id: int, output: str) -> set[str]:
        """Return failed required checks for one synthetic response."""
        return failed_required_check_ids(self.cases[case_id], output, SKILL_NAME)

    def test_expected_outputs_satisfy_required_checks(self) -> None:
        """Prove every canonical response passes its required checks."""
        assert_expected_outputs_pass(self, self.cases, SKILL_NAME)

    def test_rejects_privileged_fork_checkout(self) -> None:
        """Reject fork validation that executes in a privileged context."""
        failed = self.failed_checks(
            1,
            "Use pull_request_target, check out the fork commit, and run it on "
            "a self-hosted deploy runner with repository secrets.",
        )

        self.assertIn("finds-event-trust-confusion", failed)
        self.assertIn("moves-fork-validation-to-safe-context", failed)
        self.assertIn("rejects-privileged-event-recommendation", failed)

    def test_rejects_direct_expression_interpolation(self) -> None:
        """Reject shell quoting as an expression-injection defense."""
        failed = self.failed_checks(
            2,
            'Keep ./release.sh "${{ github.event.release.name }}" because quotes make the expression safe.',
        )

        self.assertIn("explains-expansion-order", failed)
        self.assertIn("uses-env-and-validation", failed)

    def test_rejects_workflow_wide_write_permissions(self) -> None:
        """Reject broad token permissions and unused OIDC capability."""
        failed = self.failed_checks(
            3,
            "Keep permissions: write-all at workflow scope and grant id-token: write to every job for future use.",
        )

        self.assertIn("defaults-to-no-permissions", failed)
        self.assertIn("scopes-release-job", failed)
        self.assertIn("does-not-grant-unused-oidc", failed)

    def test_rejects_unbounded_parallel_runs(self) -> None:
        """Reject global serialization without cancellation or time bounds."""
        failed = self.failed_checks(
            4,
            "Let every push run concurrently with no timeout so no build is lost.",
        )

        self.assertIn("sets-job-timeout", failed)
        self.assertIn("sets-narrow-concurrency", failed)

    def test_rejects_out_of_bounds_timeout_with_expected_vocabulary(self) -> None:
        """Reject a timeout value that only contains the expected digits."""
        output = self.cases[4].expected_output.replace(
            "timeout-minutes: 60",
            "timeout-minutes: 600",
        )

        self.assertEqual(
            {"sets-job-timeout"},
            self.failed_checks(4, output),
        )

    def test_rejects_static_production_credentials(self) -> None:
        """Reject production deployment without approval or scoped OIDC."""
        failed = self.failed_checks(
            5,
            "Store a permanent cloud key in repository secrets and deploy from "
            "any branch without an environment approval.",
        )

        self.assertIn("uses-protected-environment", failed)
        self.assertIn("uses-job-scoped-oidc", failed)
        self.assertIn("removes-static-credential", failed)

    def test_defaults_to_verified_major_and_allows_override(self) -> None:
        """Require the default major alias and explicit pinning override."""
        case = self.cases[6]

        self.assertEqual(set(), self.failed_checks(6, case.expected_output))

    def test_rejects_unverified_major_alias(self) -> None:
        """Reject deriving a major alias without upstream verification."""
        failed = self.failed_checks(
            6,
            "Use actions/checkout@v7 because v7.0.1 probably means that alias exists.",
        )

        self.assertIn("retains-release-provenance", failed)
        self.assertIn("honors-explicit-user-override", failed)
        self.assertIn("rejects-unverified-or-unsafe-refs", failed)


if __name__ == "__main__":
    unittest.main()
