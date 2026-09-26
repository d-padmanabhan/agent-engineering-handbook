#!/usr/bin/env -S uv run
"""Gate Cursor shell execution before a command runs.

The hook is designed for ``beforeShellExecution``. It denies clearly
catastrophic filesystem deletion, asks for approval before remote or
high-blast-radius mutations, and allows lower-risk commands.
"""

import posixpath
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hook_io import load_json_payload, write_json_decision

COMMAND_SEPARATORS: frozenset[str] = frozenset({";", "&&", "||", "|", "&"})
GIT_GLOBAL_OPTIONS_WITH_VALUES: frozenset[str] = frozenset(
    {
        "-C",
        "-c",
        "--git-dir",
        "--namespace",
        "--super-prefix",
        "--work-tree",
    }
)
GH_GLOBAL_OPTIONS_WITH_VALUES: frozenset[str] = frozenset({"-R", "--hostname", "--repo"})
MUTATING_COMMAND_SEQUENCES: tuple[tuple[str, ...], ...] = (
    ("terraform", "apply"),
    ("terraform", "destroy"),
    ("terragrunt", "apply"),
    ("terragrunt", "destroy"),
    ("kubectl", "apply"),
    ("kubectl", "delete"),
    ("helm", "upgrade"),
    ("helm", "uninstall"),
    ("docker", "push"),
    ("cosign", "sign"),
    ("notation", "sign"),
    ("aws", "cloudformation", "deploy"),
    ("aws", "cloudformation", "delete-stack"),
    ("aws", "s3", "rm"),
)
MUTATING_GH_METHODS: frozenset[str] = frozenset({"DELETE", "PATCH", "POST", "PUT"})
SHELL_EXECUTABLES: frozenset[str] = frozenset({"bash", "dash", "sh", "zsh"})
SUDO_OPTIONS_WITH_VALUES: frozenset[str] = frozenset(
    {
        "-C",
        "-D",
        "-R",
        "-T",
        "-U",
        "-g",
        "-h",
        "-p",
        "-r",
        "-t",
        "-u",
        "--close-from",
        "--command-timeout",
        "--chdir",
        "--chroot",
        "--group",
        "--host",
        "--prompt",
        "--role",
        "--type",
        "--user",
    }
)
TIME_OPTIONS_WITH_VALUES: frozenset[str] = frozenset({"-f", "-o", "--format", "--output"})


@dataclass(frozen=True)
class Decision:
    """Represent a Cursor hook permission decision.

    Attributes:
        permission: Cursor permission value: ``allow``, ``ask``, or ``deny``.
        user_message: Optional concise explanation shown to the user.
        agent_message: Optional instruction returned to the coding agent.
        continue_execution: Whether Cursor should continue processing the hook.
    """

    permission: str
    user_message: str | None = None
    agent_message: str | None = None
    continue_execution: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert the decision to Cursor's JSON response shape.

        Returns:
            A JSON-serializable response dictionary.
        """
        decision: dict[str, Any] = {
            "continue": self.continue_execution,
            "permission": self.permission,
        }
        if self.user_message:
            decision["user_message"] = self.user_message
        if self.agent_message:
            decision["agent_message"] = self.agent_message
        return decision


def tokenize_command(command: str) -> list[str] | None:
    """Tokenize shell text while preserving command separators.

    Args:
        command: Original shell command received from Cursor.

    Returns:
        Parsed tokens, or ``None`` when shell quoting is malformed.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return None


def command_segments(tokens: list[str]) -> list[list[str]]:
    """Split tokens into command segments around shell operators.

    Args:
        tokens: Tokens produced by :func:`tokenize_command`.

    Returns:
        Non-empty command segments.
    """
    segments: list[list[str]] = []
    current_segment: list[str] = []
    for token in tokens:
        if token in COMMAND_SEPARATORS:
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            continue
        current_segment.append(token)
    if current_segment:
        segments.append(current_segment)
    return segments


def skip_options(segment: list[str], start_index: int, options_with_values: frozenset[str]) -> int:
    """Skip CLI options and return the next positional-token index.

    Args:
        segment: One parsed command segment.
        start_index: First token after the executable.
        options_with_values: Options that consume the following token.

    Returns:
        Index of the next positional token, or ``len(segment)``.
    """
    index: int = start_index
    while index < len(segment):
        token: str = segment[index]
        if token == "--":
            return index + 1
        option_name: str = token.split("=", 1)[0]
        if option_name in options_with_values:
            index += 1 if "=" in token else 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return index
    return index


def effective_command(segment: list[str]) -> list[str]:
    """Remove recognized wrappers from a parsed command segment.

    Args:
        segment: One parsed command segment.

    Returns:
        Tokens beginning with the executable that will actually run.
    """
    index: int = 0
    while index < len(segment):
        executable: str = Path(segment[index]).name
        if executable == "command":
            index = skip_options(segment, index + 1, frozenset())
            continue
        if executable == "sudo":
            index = skip_options(segment, index + 1, SUDO_OPTIONS_WITH_VALUES)
            continue
        if executable == "env":
            index = skip_options(
                segment,
                index + 1,
                frozenset(
                    {
                        "-C",
                        "-P",
                        "-S",
                        "-u",
                        "--chdir",
                        "--split-string",
                        "--unset",
                    }
                ),
            )
            while index < len(segment) and "=" in segment[index] and not segment[index].startswith("="):
                index += 1
            continue
        if executable == "time":
            index = skip_options(segment, index + 1, TIME_OPTIONS_WITH_VALUES)
            continue
        if executable == "nohup":
            index = skip_options(segment, index + 1, frozenset())
            continue
        return segment[index:]
    return []


def embedded_shell_commands(segment: list[str]) -> list[str]:
    """Return commands passed to a nested shell's ``-c`` option.

    Args:
        segment: One parsed command segment.

    Returns:
        Embedded command strings requiring recursive evaluation.
    """
    if not segment or Path(segment[0]).name not in SHELL_EXECUTABLES:
        return []
    for index, token in enumerate(segment[1:-1], start=1):
        is_command_option: bool = token == "--command" or (
            token.startswith("-") and not token.startswith("--") and "c" in token.lstrip("-")
        )
        if is_command_option:
            return [segment[index + 1]]
    return []


def catastrophic_path(path: str) -> bool:
    """Return whether a path resolves to a critical deletion target.

    Args:
        path: Shell-expanded path token from an ``rm`` command.

    Returns:
        ``True`` for filesystem root, the user's home, or their direct globs.
    """
    home_directory: str = str(Path.home())
    expanded_path: str = (
        path.replace("${HOME}", home_directory).replace("$HOME", home_directory).replace("~", home_directory, 1)
    )
    normalized_path: str = posixpath.normpath(expanded_path)
    return normalized_path in {
        "/",
        "//",
        "/*",
        "//*",
        home_directory,
        f"{home_directory}/*",
    }


def catastrophic_rm(segment: list[str]) -> bool:
    """Detect recursive forced deletion of critical filesystem paths.

    Args:
        segment: Tokens beginning with the effective executable.

    Returns:
        ``True`` when the segment contains a catastrophic ``rm`` invocation.
    """
    if not segment or Path(segment[0]).name != "rm":
        return False

    has_recursive: bool = False
    has_force: bool = False
    paths: list[str] = []
    parse_options: bool = True
    for argument in segment[1:]:
        if argument == "--":
            parse_options = False
            continue
        if parse_options and argument.startswith("--"):
            has_recursive = has_recursive or argument == "--recursive"
            has_force = has_force or argument == "--force"
            continue
        if parse_options and argument.startswith("-") and argument != "-":
            short_options: str = argument.lstrip("-")
            has_recursive = has_recursive or "r" in short_options or "R" in short_options
            has_force = has_force or "f" in short_options
            continue
        paths.append(argument)

    return has_recursive and has_force and any(catastrophic_path(path) for path in paths)


def command_after_global_options(
    segment: list[str],
    executable_index: int,
    options_with_values: frozenset[str],
) -> tuple[str | None, int]:
    """Find a CLI subcommand after global options.

    Args:
        segment: One parsed command segment.
        executable_index: Index of the CLI executable.
        options_with_values: Global options that consume the following token.

    Returns:
        The subcommand and its index, or ``(None, -1)`` when absent.
    """
    index: int = executable_index + 1
    while index < len(segment):
        token: str = segment[index]
        option_name: str = token.split("=", 1)[0]
        if option_name in options_with_values:
            index += 1 if "=" in token else 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token, index
    return None, -1


def mutating_git_command(segment: list[str]) -> bool:
    """Detect Git remote writes and local history rewrites.

    Args:
        segment: One parsed command segment.

    Returns:
        ``True`` when approval is required.
    """
    if not segment or Path(segment[0]).name != "git":
        return False
    subcommand, subcommand_index = command_after_global_options(segment, 0, GIT_GLOBAL_OPTIONS_WITH_VALUES)
    arguments: list[str] = segment[subcommand_index + 1 :]
    forced_clean: bool = subcommand == "clean" and any(
        argument == "--force"
        or (argument.startswith("-") and not argument.startswith("--") and "f" in argument.lstrip("-"))
        for argument in arguments
    )
    return (
        subcommand in {"commit", "push", "rebase", "restore"}
        or (subcommand == "checkout" and "--" in arguments)
        or (subcommand == "reset" and "--hard" in arguments)
        or (subcommand == "branch" and any(argument in {"-d", "-D", "--delete"} for argument in arguments))
        or (subcommand == "worktree" and any(action in arguments for action in {"add", "remove"}))
        or forced_clean
    )


def worktree_manager_creation(segment: list[str]) -> bool:
    """Detect worktree creation through a supported wrapper.

    Args:
        segment: One parsed command segment.

    Returns:
        ``True`` when explicit worktree-creation approval is required.
    """
    return bool(segment) and Path(segment[0]).name == "phantom" and "create" in segment[1:]


def force_git_push(segment: list[str]) -> bool:
    """Detect an explicitly forced Git push.

    Args:
        segment: One parsed command segment.

    Returns:
        ``True`` when the push contains a force-update option.
    """
    if not segment or Path(segment[0]).name != "git":
        return False
    subcommand, subcommand_index = command_after_global_options(segment, 0, GIT_GLOBAL_OPTIONS_WITH_VALUES)
    if subcommand != "push":
        return False
    return any(
        argument in {"--force", "--force-with-lease", "--force-if-includes"}
        or (argument.startswith("-") and not argument.startswith("--") and "f" in argument.lstrip("-"))
        for argument in segment[subcommand_index + 1 :]
    )


def mutating_gh_command(segment: list[str]) -> bool:
    """Detect GitHub CLI operations that mutate remote state.

    Args:
        segment: One parsed command segment.

    Returns:
        ``True`` when approval is required.
    """
    if not segment or Path(segment[0]).name != "gh":
        return False
    subcommand, subcommand_index = command_after_global_options(segment, 0, GH_GLOBAL_OPTIONS_WITH_VALUES)
    arguments: list[str] = segment[subcommand_index + 1 :]
    if subcommand == "pr" and any(argument in {"create", "merge"} for argument in arguments):
        return True
    if subcommand == "repo" and "sync" in arguments:
        return True
    if subcommand != "api":
        return False

    method: str = "GET"
    fields_present: bool = False
    for index, argument in enumerate(arguments):
        if argument in {"--method", "-X"} and index + 1 < len(arguments):
            method = arguments[index + 1].upper()
        elif argument.startswith("--method="):
            method = argument.split("=", 1)[1].upper()
        elif argument.startswith("-X") and len(argument) > 2:
            method = argument[2:].lstrip("=").upper()
        elif argument in {"--field", "--raw-field", "-F", "-f", "--input"}:
            fields_present = True
        elif argument.startswith(("--field=", "--raw-field=", "--input=", "-F=", "-f=")):
            fields_present = True
        elif argument.startswith(("-F", "-f")) and len(argument) > 2:
            fields_present = True
    return method in MUTATING_GH_METHODS or (method == "GET" and fields_present)


def contains_mutating_sequence(segment: list[str]) -> bool:
    """Detect known infrastructure and cloud mutation command sequences.

    Args:
        segment: One parsed command segment.

    Returns:
        ``True`` when a known mutation sequence appears.
    """
    if not segment:
        return False
    normalized_tokens: list[str] = [Path(token).name for token in segment]
    if normalized_tokens[0] not in {
        "aws",
        "cosign",
        "docker",
        "helm",
        "kubectl",
        "notation",
        "terraform",
        "terragrunt",
    }:
        return False
    for sequence in MUTATING_COMMAND_SEQUENCES:
        next_index: int = 0
        for token in normalized_tokens:
            if token == sequence[next_index]:
                next_index += 1
                if next_index == len(sequence):
                    return True
    if "aws" in normalized_tokens and "s3api" in normalized_tokens:
        s3api_index: int = normalized_tokens.index("s3api")
        if any(token.startswith("delete-") for token in normalized_tokens[s3api_index + 1 :]):
            return True
    return False


def evaluate_command(command: str, recursion_depth: int = 0) -> Decision:
    """Evaluate one shell command against the hook policy.

    Args:
        command: Original shell command received from Cursor.
        recursion_depth: Current nested-shell evaluation depth.

    Returns:
        A deny, ask, or allow decision.
    """
    if recursion_depth > 3:
        return Decision(
            permission="ask",
            user_message="Approval required for deeply nested shell execution",
            agent_message="Flatten the command and explain each operation before retrying.",
        )

    tokens: list[str] | None = tokenize_command(command)
    if tokens is None:
        return Decision(
            permission="ask",
            user_message="Approval required because the shell command could not be parsed",
            agent_message="Correct the shell quoting and present the command again.",
        )

    segments: list[list[str]] = [effective_command(segment) for segment in command_segments(tokens)]
    if any(catastrophic_rm(segment) for segment in segments):
        return Decision(
            permission="deny",
            user_message="Blocked catastrophic delete command",
            agent_message=(
                "Refuse to delete critical filesystem paths. Propose a safer alternative with explicit, narrow paths."
            ),
        )

    for segment in segments:
        is_force_push: bool = force_git_push(segment)
        is_mutation: bool = (
            is_force_push
            or mutating_git_command(segment)
            or worktree_manager_creation(segment)
            or mutating_gh_command(segment)
            or contains_mutating_sequence(segment)
        )
        if is_mutation:
            user_message: str = (
                f"Explicit force-push authorization required for: {command.strip()}"
                if is_force_push
                else f"Approval required for: {command.strip()}"
            )
            agent_message: str = (
                (
                    "A normal push approval does not authorize a force update. Show the exact ref, "
                    "remote divergence, affected commits, and rollback plan, then wait for explicit approval."
                )
                if is_force_push
                else (
                    "This command changes remote state, rewrites history, or has a "
                    "large blast radius. Explain the impact and wait for approval."
                )
            )
            return Decision(
                permission="ask",
                user_message=user_message,
                agent_message=agent_message,
            )
        for embedded_command in embedded_shell_commands(segment):
            embedded_decision: Decision = evaluate_command(embedded_command, recursion_depth + 1)
            if embedded_decision.permission != "allow":
                return embedded_decision

    return Decision(permission="allow")


def main() -> int:
    """Read a hook event, evaluate its command, and emit a decision.

    Returns:
        Process exit code. Hook decisions use JSON and therefore return zero.
    """
    payload: dict[str, Any] | None = load_json_payload()
    if payload is None:
        write_json_decision(
            Decision(
                permission="ask",
                user_message="Approval required because hook input was malformed",
                agent_message="Retry with a valid shell command payload.",
            ).to_dict()
        )
        return 0

    command_value: Any = payload.get("command")
    if not isinstance(command_value, str) or not command_value.strip():
        write_json_decision(
            Decision(
                permission="ask",
                user_message="Approval required because no shell command was provided",
                agent_message="Provide the exact command before requesting execution.",
            ).to_dict()
        )
        return 0

    write_json_decision(evaluate_command(command_value).to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
