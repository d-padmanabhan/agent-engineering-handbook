"""Regression tests for discriminating core-engineering eval assertions."""

import tempfile
import unittest
from pathlib import Path

from evals.skill_eval import AdapterResponse, EvalCase, evaluate_checks, load_eval_suite

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CORE_SKILL_DIRECTORY = REPOSITORY_ROOT / "skills" / "core-engineering"


class CoreEngineeringEvalTests(unittest.TestCase):
    """Ensure known noncompliant responses cannot pass core evals."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the core-engineering eval suite once."""
        suite = load_eval_suite(CORE_SKILL_DIRECTORY)
        if suite is None:
            raise AssertionError("core-engineering eval suite is missing")
        cls.cases = {case.identifier: case for case in suite.cases}

    def failed_check_ids(self, case: EvalCase, output: str) -> set[str]:
        """Return failed required check identifiers for one response."""
        response = AdapterResponse(output=output, events=(), usage={}, raw={})
        with tempfile.TemporaryDirectory() as temp_directory:
            results = evaluate_checks(
                case.checks,
                response,
                Path(temp_directory),
                default_skill="core-engineering",
            )
        return {result.identifier for result in results if result.required and not result.passed}

    def test_python_cli_rejects_generic_shebang(self) -> None:
        """Reject otherwise plausible code that does not use uv."""
        output = """```python
#!/usr/bin/env python3
import argparse
import json
import sys

def main(argv: list[str] | None = None) -> int:
    \"\"\"Run the command.\"\"\"
    return 0

if __name__ == \"__main__\":
    raise SystemExit(main())
```"""

        failed = self.failed_check_ids(self.cases[2], output)

        self.assertIn("uses-uv-shebang", failed)
        self.assertIn("rejects-generic-python-shebang", failed)

    def test_python_cli_accepts_sys_exit_propagation(self) -> None:
        """Accept either standard mechanism for propagating main's exit code."""
        output = """
def main(argv: list[str] | None = None) -> int:
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

        failed = self.failed_check_ids(self.cases[2], output)

        self.assertNotIn("uses-typed-main", failed)
        self.assertNotIn("propagates-main-exit-code", failed)

    def test_github_actions_rejects_old_python_and_pip(self) -> None:
        """Reject workflow guidance that violates runtime and package policy."""
        output = """
uses: actions/checkout@v7.0.1
uses: actions/setup-python@v7.0.0
python-version: '3.12'
cache: pip
run: pip install -r requirements.txt
uses: astral-sh/setup-uv@v3
run: uv sync
https://github.com/actions/checkout
https://github.com/actions/setup-python
"""

        failed = self.failed_check_ids(self.cases[3], output)

        self.assertIn("uses-python-3-14", failed)
        self.assertIn("rejects-lower-python-versions", failed)
        self.assertIn("rejects-pip-and-requirements", failed)
        self.assertIn("configures-uv-in-ci", failed)
        self.assertIn("names-current-releases", failed)
        self.assertIn("uses-setup-uv-official-source", failed)

    def test_github_actions_accepts_metadata_provenance_wording(self) -> None:
        """Accept explicit metadata provenance without one prescribed verb."""
        output = "Model memory may be stale; versions come from the attached official release metadata."

        failed = self.failed_check_ids(self.cases[3], output)

        self.assertNotIn("requires-verification", failed)

    def test_kiss_review_rejects_speculative_class_hierarchy(self) -> None:
        """Reject a response that implements the proposed over-engineering."""
        output = """
Use KISS for the 30-line script, but implement the extensible design:

class PluginFactory:
    pass

Revisit this when multiple formats exist.
"""

        failed = self.failed_check_ids(self.cases[4], output)

        self.assertIn("does-not-draft-class-hierarchy", failed)

    def test_complexity_review_rejects_missing_tradeoffs(self) -> None:
        """Reject a rewrite that gives unsupported bounds and omits space cost."""
        output = """
Use a set because every lookup is guaranteed O(1), making the whole operation O(n).
This has no additional memory cost.
"""

        failed = self.failed_check_ids(self.cases[6], output)

        self.assertIn("defines-input-variables", failed)
        self.assertIn("analyzes-current-complexity", failed)
        self.assertIn("analyzes-corrected-complexity", failed)
        self.assertIn("requires-measurement", failed)

    def test_complexity_eval_rejects_incorrect_big_o_rules(self) -> None:
        """Reject common unconditional and loop-counting misconceptions."""
        output = """
Hash-map lookups are guaranteed O(1).
Every append is O(1).
Any two loops make the function O(n^2).
"""

        failed = self.failed_check_ids(self.cases[7], output)

        self.assertIn("qualifies-hash-lookup", failed)
        self.assertIn("explains-amortized-append", failed)
        self.assertIn("combines-sequential-loops", failed)

    def test_complexity_eval_rejects_notation_only_optimization(self) -> None:
        """Reject complexity-driven machinery without workload evidence."""
        output = "Build the index so lookup improves from O(n) to O(1)."

        failed = self.failed_check_ids(self.cases[8], output)

        self.assertIn("rejects-notation-only-optimization", failed)
        self.assertIn("keeps-simple-design", failed)
        self.assertIn("requires-bottleneck-evidence", failed)

    def test_simplification_rejects_broad_dense_rewrite(self) -> None:
        """Reject an unscoped, untested simplification that favors fewer lines."""
        output = "Collapse the chain into one nested ternary. Then clean up the rest of the billing module."

        failed = self.failed_check_ids(self.cases[9], output)

        self.assertIn("limits-simplification-scope", failed)
        self.assertIn("preserves-behavior-with-tests", failed)
        self.assertIn("rejects-broad-or-dense-rewrite", failed)

    def test_simplification_accepts_negated_guidance(self) -> None:
        """Accept a correct answer that restates the unsafe request it declines."""
        case = self.cases[9]
        output = "You asked to clean up the rest of the billing module, but " + case.expected_output

        self.assertEqual(set(), self.failed_check_ids(case, output))
        self.assertEqual(set(), self.failed_check_ids(case, case.expected_output))

    def test_sample_app_rejects_overbuilt_insecure_demo(self) -> None:
        """Reject a sample that adds abstractions and silently drops authentication."""
        output = "Add the plugin system, repository layer, and caching. Disable authentication on the admin route."

        failed = self.failed_check_ids(self.cases[10], output)

        self.assertIn("keeps-sample-focused", failed)
        self.assertIn("keeps-secure-defaults", failed)
        self.assertIn("rejects-silent-auth-removal", failed)


if __name__ == "__main__":
    unittest.main()
