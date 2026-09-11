"""Regression tests for high-risk Kubernetes operator eval assertions."""

import tempfile
import unittest
from pathlib import Path

from evals.skill_eval import AdapterResponse, EvalCase, evaluate_checks, load_eval_suite

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OPERATOR_SKILL_DIRECTORY = REPOSITORY_ROOT / "skills" / "kubernetes-operator-development"


class KubernetesOperatorDevelopmentEvalTests(unittest.TestCase):
    """Ensure unsafe operator guidance cannot satisfy the eval suite."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the Kubernetes operator eval suite once."""
        suite = load_eval_suite(OPERATOR_SKILL_DIRECTORY)
        if suite is None:
            raise AssertionError("kubernetes-operator-development eval suite is missing")
        cls.cases = {case.identifier: case for case in suite.cases}

    def failed_check_ids(self, case: EvalCase, output: str) -> set[str]:
        """Return failed required check identifiers for one response."""
        response = AdapterResponse(output=output, events=(), usage={}, raw={})
        with tempfile.TemporaryDirectory() as temp_directory:
            results = evaluate_checks(
                case.checks,
                response,
                Path(temp_directory),
                default_skill="kubernetes-operator-development",
            )
        return {result.identifier for result in results if result.required and not result.passed}

    def test_expected_outputs_satisfy_required_checks(self) -> None:
        """Confirm each canonical expected response satisfies its own checks."""
        for case in self.cases.values():
            with self.subTest(case=case.identifier):
                self.assertEqual(set(), self.failed_check_ids(case, case.expected_output))

    def test_rejects_observe_then_create_with_attempt_key(self) -> None:
        """Require stable operation identity and lost-response recovery."""
        output = "GET by display name, then POST with a new UUID on every retry."

        failed = self.failed_check_ids(self.cases[1], output)

        self.assertIn("rejects-observe-only-idempotency", failed)
        self.assertIn("binds-stable-operation-identity", failed)
        self.assertIn("recovers-lost-response", failed)
        self.assertIn("rejects-new-attempt-key", failed)

    def test_rejects_destructive_name_based_cleanup(self) -> None:
        """Require conservative deletion, ownership proof, and recovery."""
        output = "Default to Delete, delete by bucket name, and leave the finalizer until it works."

        failed = self.failed_check_ids(self.cases[3], output)

        self.assertIn("uses-conservative-deletion", failed)
        self.assertIn("verifies-delete-ownership", failed)
        self.assertIn("orders-and-idempotently-cleans", failed)
        self.assertIn("defines-stuck-finalizer-recovery", failed)

    def test_rejects_sleep_and_global_cache_bypass(self) -> None:
        """Require convergence-aware cache handling and narrow live reads."""
        output = "Sleep after every write and disable the controller-runtime cache."

        failed = self.failed_check_ids(self.cases[4], output)

        self.assertIn("explains-cache-semantics", failed)
        self.assertIn("designs-for-convergence", failed)
        self.assertIn("narrows-live-reads", failed)
        self.assertIn("rejects-sleep-and-global-bypass", failed)

    def test_rejects_compile_only_crd_upgrade(self) -> None:
        """Require conversion, stored-version migration, and rollback evidence."""
        output = "Generated code compiles, so remove v1alpha1 while installing v1."

        failed = self.failed_check_ids(self.cases[6], output)

        self.assertIn("preserves-served-version", failed)
        self.assertIn("requires-roundtrip-conversion", failed)
        self.assertIn("orders-webhook-rollout", failed)
        self.assertIn("tests-upgrade-and-rollback", failed)

    def test_rejects_fake_and_envtest_as_full_cluster_proof(self) -> None:
        """Require test layers that match Kubernetes behavior claims."""
        output = "The fake client and envtest prove garbage collection and kubelet behavior."

        failed = self.failed_check_ids(self.cases[7], output)

        self.assertIn("rejects-fake-api-proof", failed)
        self.assertIn("scopes-envtest-use", failed)
        self.assertIn("identifies-envtest-gap", failed)
        self.assertIn("requires-realistic-substitute", failed)

    def test_rejects_stale_ready_and_generation_only_predicate(self) -> None:
        """Require current conditions and dependency-triggered recovery."""
        output = "Ready stays true, and GenerationChangedPredicate will notice the Secret update."

        failed = self.failed_check_ids(self.cases[8], output)

        self.assertIn("rejects-stale-readiness", failed)
        self.assertIn("uses-standard-condition", failed)
        self.assertIn("rejects-generation-only-recovery", failed)
        self.assertIn("watches-referenced-secret", failed)


if __name__ == "__main__":
    unittest.main()
