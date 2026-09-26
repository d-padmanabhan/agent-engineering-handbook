"""Behavioral tests for Cursor hook policy and audit safety."""

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HOOK_DIRECTORY: Path = Path(__file__).resolve().parent.parent
if str(HOOK_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(HOOK_DIRECTORY))

import audit_log  # noqa: E402
import guard_before_read_file  # noqa: E402
import guard_before_shell  # noqa: E402


class ShellGuardTests(unittest.TestCase):
    """Verify shell policy decisions for bypass and boundary cases."""

    def assert_permission(self, command: str, expected_permission: str) -> None:
        """Assert the permission produced for a command.

        Args:
            command: Shell command to evaluate.
            expected_permission: Expected policy result.
        """

        decision: guard_before_shell.Decision = guard_before_shell.evaluate_command(command)
        self.assertEqual(decision.permission, expected_permission)

    def test_denies_wrapped_catastrophic_delete(self) -> None:
        self.assert_permission("command rm -fr /", "deny")

    def test_denies_nested_shell_catastrophic_delete(self) -> None:
        self.assert_permission("bash -c 'rm -rf /'", "deny")

    def test_denies_nested_login_shell_catastrophic_delete(self) -> None:
        self.assert_permission("bash -lc 'rm -rf /'", "deny")

    def test_denies_catastrophic_path_variants(self) -> None:
        for command in ('rm -rf "$HOME/"', "rm -rf /.", "rm -rf $HOME/*"):
            with self.subTest(command=command):
                self.assert_permission(command, "deny")

    def test_git_global_options_do_not_bypass_push_gate(self) -> None:
        self.assert_permission("git -C repo push origin main", "ask")

    def test_git_commit_requires_approval(self) -> None:
        self.assert_permission("git commit -m 'docs: update guide'", "ask")

    def test_git_discard_commands_require_approval(self) -> None:
        for command in (
            "git restore src/app.py",
            "git checkout -- src/app.py",
            "git reset --hard HEAD~1",
            "git clean -fd",
        ):
            with self.subTest(command=command):
                self.assert_permission(command, "ask")

    def test_git_branch_and_worktree_mutations_require_approval(self) -> None:
        for command in (
            "git branch -D feat/old",
            "git worktree add -b feat/new ../new-worktree origin/main",
            "git worktree remove ../old-worktree",
            "phantom create feat/new",
        ):
            with self.subTest(command=command):
                self.assert_permission(command, "ask")

    def test_read_only_git_commands_are_allowed(self) -> None:
        for command in (
            "git status --short",
            "git diff",
            "git fetch origin --prune",
            "git log --oneline",
            "git worktree list",
            "phantom list",
        ):
            with self.subTest(command=command):
                self.assert_permission(command, "allow")

    def test_force_push_has_specific_approval_message(self) -> None:
        decision: guard_before_shell.Decision = guard_before_shell.evaluate_command(
            "git push --force-with-lease origin feat/rewrite"
        )
        self.assertEqual(decision.permission, "ask")
        self.assertIn("force-push", decision.user_message or "")
        self.assertIn("normal push approval", decision.agent_message or "")

    def test_image_publish_and_sign_commands_require_approval(self) -> None:
        for command in (
            "docker push acme.com/app@sha256:0123456789abcdef",
            "cosign sign acme.com/app@sha256:0123456789abcdef",
            "notation sign acme.com/app@sha256:0123456789abcdef",
        ):
            with self.subTest(command=command):
                self.assert_permission(command, "ask")

    def test_local_docker_build_is_allowed(self) -> None:
        self.assert_permission("docker build -t app:test .", "allow")

    def test_infrastructure_global_options_do_not_bypass_gate(self) -> None:
        self.assert_permission("terraform -chdir=infra apply", "ask")

    def test_gh_explicit_delete_method_requires_approval(self) -> None:
        self.assert_permission("gh api --method DELETE repos/acme/app/issues/1", "ask")

    def test_gh_compact_delete_method_requires_approval(self) -> None:
        self.assert_permission("gh api -XDELETE repos/acme/app/issues/1", "ask")

    def test_gh_compact_equals_delete_method_requires_approval(self) -> None:
        self.assert_permission("gh api -X=DELETE repos/acme/app/issues/1", "ask")

    def test_gh_fields_imply_mutating_api_request(self) -> None:
        self.assert_permission("gh api repos/acme/app/issues -f title=test", "ask")

    def test_gh_compact_fields_imply_mutating_api_request(self) -> None:
        for command in (
            "gh api repos/acme/app/issues --field=title=test",
            "gh api repos/acme/app/issues --raw-field=title=test",
            "gh api repos/acme/app/issues --input=payload.json",
            "gh api repos/acme/app/issues -Ftitle=test",
            "gh api repos/acme/app/issues -ftitle=test",
        ):
            with self.subTest(command=command):
                self.assert_permission(command, "ask")

    def test_rm_long_force_option_does_not_imply_recursive(self) -> None:
        self.assert_permission("rm --preserve-root --force /", "allow")

    def test_quoted_whitespace_is_not_rewritten(self) -> None:
        self.assert_permission('printf "%s\\n" "a   b"', "allow")

    def test_command_arguments_do_not_trigger_mutation_detection(self) -> None:
        self.assert_permission("echo git push", "allow")
        self.assert_permission("echo terraform apply", "allow")

    def test_wrapper_options_do_not_hide_mutations(self) -> None:
        self.assert_permission("env -u TOKEN git push origin main", "ask")
        self.assert_permission("env -P /usr/bin git push origin main", "ask")
        self.assert_permission("time -o timing.txt git push origin main", "ask")
        self.assert_permission("sudo -D /tmp git push origin main", "ask")

    def test_malformed_shell_quoting_requires_approval(self) -> None:
        self.assert_permission("printf 'unterminated", "ask")


class FileReadGuardTests(unittest.TestCase):
    """Verify secret-file, malformed-input, and size boundaries."""

    def test_blocks_environment_file_family(self) -> None:
        decision: dict[str, object] = guard_before_read_file.evaluate_read({"file_path": "/repo/.env.staging"})
        self.assertEqual(decision["permission"], "deny")

    def test_blocks_case_insensitive_private_key_names(self) -> None:
        for file_name in ("secret.PEM", "ID_RSA"):
            with self.subTest(file_name=file_name):
                decision: dict[str, object] = guard_before_read_file.evaluate_read({"file_path": f"/repo/{file_name}"})
                self.assertEqual(decision["permission"], "deny")

    def test_allows_committed_environment_example(self) -> None:
        decision: dict[str, object] = guard_before_read_file.evaluate_read(
            {"file_path": "/repo/.env.example", "content": "NAME=value"}
        )
        self.assertEqual(decision["permission"], "allow")

    def test_blocks_missing_path(self) -> None:
        decision: dict[str, object] = guard_before_read_file.evaluate_read({})
        self.assertEqual(decision["permission"], "deny")

    def test_blocks_non_string_content(self) -> None:
        decision: dict[str, object] = guard_before_read_file.evaluate_read(
            {"file_path": "/repo/readme.md", "content": {"unexpected": True}}
        )
        self.assertEqual(decision["permission"], "deny")

    def test_blocks_oversized_content(self) -> None:
        decision: dict[str, object] = guard_before_read_file.evaluate_read(
            {
                "file_path": "/repo/large.txt",
                "content": "x" * (guard_before_read_file.MAX_CONTENT_CHARACTERS + 1),
            }
        )
        self.assertEqual(decision["permission"], "deny")


class AuditLogTests(unittest.TestCase):
    """Verify audit redaction, bounds, permissions, and resilience."""

    def test_redacts_keys_and_embedded_secret_values(self) -> None:
        payload: dict[str, object] = {
            "api_key": "key-value",
            "command": "curl -H Authorization:Bearer-secret https://acme.com",
            "content": "password=plaintext",
            "environment": ('AWS_SECRET_ACCESS_KEY=aws-secret GH_TOKEN=gh-secret api_key="quoted-secret"'),
        }

        redacted: dict[str, object] = audit_log.redact_value(payload)
        serialized: str = json.dumps(redacted)

        self.assertNotIn("key-value", serialized)
        self.assertNotIn("Bearer-secret", serialized)
        self.assertNotIn("plaintext", serialized)
        self.assertNotIn("aws-secret", serialized)
        self.assertNotIn("gh-secret", serialized)
        self.assertNotIn("quoted-secret", serialized)
        self.assertIn(audit_log.REDACTED_VALUE, serialized)

    def test_redacts_malformed_quoted_secret_excerpt(self) -> None:
        malformed_payload: str = '{"password": "secret"'
        redacted_payload: str = audit_log.redact_string(malformed_payload)

        self.assertNotIn("secret", redacted_payload)
        self.assertIn(audit_log.REDACTED_VALUE, redacted_payload)

    def test_bounds_depth_and_collection_size(self) -> None:
        nested: object = "leaf"
        for _ in range(audit_log.MAX_DEPTH + 2):
            nested = {"next": nested}
        payload: dict[str, object] = {
            "nested": nested,
            "items": list(range(audit_log.MAX_COLLECTION_ITEMS + 5)),
        }

        redacted: dict[str, object] = audit_log.redact_value(payload)
        serialized: str = json.dumps(redacted)

        self.assertIn("<max-depth-reached>", serialized)
        self.assertIn("<truncated-items>", serialized)

    def test_non_mapping_tool_input_does_not_raise(self) -> None:
        record: dict[str, object] = audit_log.build_record({"tool_input": "unexpected", "tool_name": "Read"})
        self.assertIsNone(record["file_path"])

    def test_serialized_record_is_bounded(self) -> None:
        record: dict[str, object] = audit_log.build_record({"content": "x" * (audit_log.MAX_RECORD_BYTES * 2)})
        serialized_record: bytes = audit_log.serialize_record(record)
        self.assertLessEqual(len(serialized_record), audit_log.MAX_RECORD_BYTES)

    def test_append_record_uses_private_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            log_path: Path = Path(temp_directory) / "state" / "audit.jsonl"

            audit_log.append_record(log_path, b'{"event":"test"}\n')

            directory_mode: int = stat.S_IMODE(log_path.parent.stat().st_mode)
            file_mode: int = stat.S_IMODE(log_path.stat().st_mode)
            self.assertEqual(directory_mode, 0o700)
            self.assertEqual(file_mode, 0o600)

    def test_main_remains_non_blocking_when_write_fails(self) -> None:
        with (
            patch.object(audit_log, "load_payload", return_value={}),
            patch.object(audit_log, "append_record", side_effect=OSError("full")),
            patch("sys.stdout.write") as stdout_write,
            patch("sys.stderr.write") as stderr_write,
        ):
            exit_code: int = audit_log.main()

        self.assertEqual(exit_code, 0)
        stdout_write.assert_called_once_with('{"continue":true}\n')
        stderr_write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
