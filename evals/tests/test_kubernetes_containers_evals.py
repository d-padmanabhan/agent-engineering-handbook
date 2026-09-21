"""Regression tests for Kubernetes container eval assertions."""

import tempfile
import unittest
from pathlib import Path

from evals.skill_eval import AdapterResponse, EvalCase, evaluate_checks, load_eval_suite

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
KUBERNETES_SKILL_DIRECTORY = REPOSITORY_ROOT / "skills" / "kubernetes-containers"


class KubernetesContainersEvalTests(unittest.TestCase):
    """Ensure unsafe Kubernetes scheduling guidance cannot satisfy the suite."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the Kubernetes containers eval suite once."""
        suite = load_eval_suite(KUBERNETES_SKILL_DIRECTORY)
        if suite is None:
            raise AssertionError("kubernetes-containers eval suite is missing")
        cls.cases = {case.identifier: case for case in suite.cases}

    def failed_check_ids(self, case: EvalCase, output: str) -> set[str]:
        """Return failed required check identifiers for one response."""
        response = AdapterResponse(output=output, events=(), usage={}, raw={})
        with tempfile.TemporaryDirectory() as temp_directory:
            results = evaluate_checks(
                case.checks,
                response,
                Path(temp_directory),
                default_skill="kubernetes-containers",
            )
        return {result.identifier for result in results if result.required and not result.passed}

    def test_scheduling_expected_output_satisfies_required_checks(self) -> None:
        """Confirm the new scheduling response satisfies its checks."""
        scheduling_case = self.cases[7]

        self.assertEqual(set(), self.failed_check_ids(scheduling_case, scheduling_case.expected_output))

    def test_rejects_toleration_only_and_infeasible_hard_spread(self) -> None:
        """Require explicit node selection and capacity-aware spreading."""
        output = (
            "The toleration forces dedicated placement. Require cross-zone "
            "anti-affinity even in one-zone clusters and trust any node label."
        )

        failed = self.failed_check_ids(self.cases[7], output)

        self.assertIn("distinguishes-permission-from-selection", failed)
        self.assertIn("protects-placement-labels", failed)
        self.assertIn("rejects-infeasible-hard-affinity", failed)
        self.assertIn("selects-spread-policy-by-capacity", failed)
        self.assertIn("explains-topology-domain-and-soft-skew", failed)


if __name__ == "__main__":
    unittest.main()
