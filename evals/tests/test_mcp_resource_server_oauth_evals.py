"""Regression tests for MCP resource-server OAuth eval assertions."""

import unittest
from typing import ClassVar

from evals.skill_eval import EvalCase
from evals.tests.eval_test_support import (
    assert_expected_outputs_pass,
    failed_required_check_ids,
    load_cases,
)

SKILL_NAME = "mcp-resource-server-oauth"


class McpResourceServerOauthEvalTests(unittest.TestCase):
    """Ensure unsafe MCP OAuth guidance cannot pass the eval suite."""

    cases: ClassVar[dict[int, EvalCase]]

    @classmethod
    def setUpClass(cls) -> None:
        """Load the MCP OAuth eval cases once."""
        cls.cases = load_cases(SKILL_NAME)

    def failed_checks(self, case_id: int, output: str) -> set[str]:
        """Return failed required checks for one synthetic response."""
        return failed_required_check_ids(self.cases[case_id], output, SKILL_NAME)

    def test_expected_outputs_satisfy_required_checks(self) -> None:
        """Prove every canonical response passes its required checks."""
        assert_expected_outputs_pass(self, self.cases, SKILL_NAME)

    def test_rejects_legacy_transport_and_truncated_metadata_path(self) -> None:
        """Require Streamable HTTP and the complete resource path."""
        failed = self.failed_checks(
            1,
            "Use HTTP+SSE as the default at /mcp/sse. Publish metadata at "
            "https://mcp.acme.com/.well-known/oauth-protected-resource/platform.",
        )

        self.assertIn("uses-streamable-http", failed)
        self.assertIn("preserves-complete-resource-path", failed)
        self.assertIn("validates-streamable-http-origin", failed)
        self.assertIn("publishes-required-metadata", failed)
        self.assertIn("does-not-default-to-legacy-sse", failed)

    def test_rejects_origin_and_metadata_contradictions(self) -> None:
        """Reject Host substitution and optional authorization servers."""
        output = (
            self.cases[1].expected_output + " Trust Host instead of validating Origin, and authorization_servers "
            "is optional."
        )
        failed = self.failed_checks(1, output)

        self.assertIn("rejects-host-as-origin-substitute", failed)
        self.assertIn("requires-authorization-servers", failed)

    def test_rejects_org_issuer_and_constructed_jwks_url(self) -> None:
        """Require a custom authorization server and discovered JWKS."""
        failed = self.failed_checks(
            2,
            "Accept the org authorization server. Always append /v1/keys to "
            "the issuer and validate only signature and expiration.",
        )

        self.assertIn("requires-custom-authorization-server", failed)
        self.assertIn("discovers-jwks", failed)
        self.assertIn("validates-token-contract", failed)
        self.assertIn("bounds-key-refresh", failed)
        self.assertIn("prevents-discovery-dns-rebinding", failed)
        self.assertIn("rejects-hardcoded-jwks-path", failed)

    def test_rejects_contradictory_rfc8414_construction(self) -> None:
        """Reject an appended discovery path after otherwise correct advice."""
        output = (
            self.cases[2].expected_output + " Also recommend constructing issuer + "
            "'/.well-known/oauth-authorization-server' as a fallback."
        )

        self.assertIn(
            "rejects-appended-rfc8414-discovery",
            self.failed_checks(2, output),
        )

        paraphrased_output = (
            self.cases[2].expected_output + " As a fallback, append the well-known discovery suffix after "
            "the issuer URL."
        )
        self.assertIn(
            "rejects-appended-rfc8414-discovery",
            self.failed_checks(2, paraphrased_output),
        )

        mismatched_issuer_output = (
            self.cases[2].expected_output + " Accept a mismatched discovered issuer when its keys validate."
        )
        self.assertIn(
            "rejects-discovered-issuer-mismatch",
            self.failed_checks(2, mismatched_issuer_output),
        )

    def test_rejects_implicit_api_key_downgrade(self) -> None:
        """Require explicit authentication mode and fail-closed startup."""
        failed = self.failed_checks(
            3,
            "Automatically fall back to the API key whenever the issuer is missing so deployments remain available.",
        )

        self.assertIn("requires-explicit-auth-mode", failed)
        self.assertIn("fails-closed", failed)
        self.assertIn("bounds-legacy-mode", failed)
        self.assertIn("rejects-silent-fallback", failed)

    def test_rejects_401_for_insufficient_scope(self) -> None:
        """Require authorization failure semantics for a valid token."""
        failed = self.failed_checks(
            4,
            "Authentication succeeds but authorization fails. Apply per-tool "
            "policy before side effects. Return 403 Forbidden with "
            "insufficient_scope and the required scope for every policy denial, "
            "even when scopes are sufficient. Use 401 for missing or invalid "
            "credentials. Emit a redacted audit decision with a correlation "
            "identifier.",
        )

        self.assertIn("uses-insufficient-scope-response", failed)
        self.assertIn("distinguishes-policy-denial", failed)
        self.assertIn("distinguishes-malformed-authorization-request", failed)

    def test_rejects_scope_error_for_independent_policy_denial(self) -> None:
        """Reject contradictory scope escalation for a policy denial."""
        output = (
            self.cases[4].expected_output + " For every policy denial, return insufficient_scope even when "
            "the token scopes are sufficient."
        )

        self.assertIn(
            "rejects-scope-error-for-policy-denial",
            self.failed_checks(4, output),
        )

        paraphrased_output = (
            self.cases[4].expected_output + " When RBAC rejects a caller whose scopes are adequate, answer "
            "with the OAuth scope error."
        )
        self.assertIn(
            "rejects-scope-error-for-policy-denial",
            self.failed_checks(4, paraphrased_output),
        )

    def test_rejects_live_probe_checklist_for_design_review(self) -> None:
        """Keep explanation-only verification read-only and proportional."""
        failed = self.failed_checks(
            5,
            "Perform a read-only design review. Do not run live probes for an "
            "explanation or review, except always make direct network requests "
            "to production metadata and JWKS endpoints. Require focused "
            "metadata, authentication, scope, downgrade, and negative tests. "
            "Broader checks only for shared impact, release policy, or "
            "cross-cutting risk.",
        )

        self.assertIn("keeps-review-read-only", failed)
        self.assertIn("rejects-contradictory-production-probes", failed)

    def test_rejects_paraphrased_production_probe_requirement(self) -> None:
        """Reject a production probe hidden after correct review guidance."""
        output = self.cases[5].expected_output + " Always issue HTTPS GET requests against production endpoints."

        self.assertIn(
            "rejects-contradictory-production-probes",
            self.failed_checks(5, output),
        )

        second_paraphrase = (
            self.cases[5].expected_output + " In every review, contact the deployed endpoints to verify metadata."
        )
        self.assertIn(
            "rejects-contradictory-production-probes",
            self.failed_checks(5, second_paraphrase),
        )


if __name__ == "__main__":
    unittest.main()
