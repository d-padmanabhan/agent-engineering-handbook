"""Regression tests for Go and Rust systems evals."""

import unittest
from typing import ClassVar

from evals.skill_eval import EvalCase
from evals.tests.eval_test_support import (
    assert_expected_outputs_pass,
    failed_required_check_ids,
    load_cases,
)

SKILL_NAME = "go-rust-systems"


class GoRustSystemsEvalTests(unittest.TestCase):
    """Ensure aggregate scores cannot replace deterministic Go quality gates."""

    cases: ClassVar[dict[int, EvalCase]]

    @classmethod
    def setUpClass(cls) -> None:
        """Load the Go and Rust systems eval cases once."""
        cls.cases = load_cases(SKILL_NAME)

    def failed_checks(self, case_id: int, output: str) -> set[str]:
        """Return failed required checks for one synthetic response."""
        return failed_required_check_ids(self.cases[case_id], output, SKILL_NAME)

    def test_quality_gate_expected_output_satisfies_required_checks(self) -> None:
        """Prove the canonical Go quality-gate response passes."""
        assert_expected_outputs_pass(
            self,
            {6: self.cases[6]},
            SKILL_NAME,
        )

    def test_rejects_single_score_as_go_quality_gate(self) -> None:
        """Reject replacing deterministic checks with one composite score."""
        failed = self.failed_checks(
            6,
            "Require gocode-score >= 90 and an A+ Go Report Card grade. "
            "Those two scores replace lint, tests, coverage, and security checks.",
        )

        self.assertIn("retains-deterministic-go-gates", failed)
        self.assertIn("requires-complete-lint-reporting", failed)
        self.assertIn("rejects-score-as-quality-gate", failed)
        self.assertIn("classifies-retired-and-experimental-tools", failed)
        self.assertIn("limits-crap-to-hotspot-analysis", failed)


if __name__ == "__main__":
    unittest.main()
