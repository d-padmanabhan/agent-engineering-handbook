"""Atomic KB swap helper.

Pattern: archive-then-write-then-verify-then-rollback-on-failure.

The canonical filename never changes; downstream consumers (generators, dashboards,
slash commands) keep importing the same module. The archived file is a rollback
anchor and a diff source.

Usage::

    from atomic_swap import atomic_swap_kb
    archive = atomic_swap_kb(
        canonical=Path("kb/product_knowledge_base.py"),
        new_content=rendered_python,
        verify=lambda: importlib.import_module("kb.product_knowledge_base"),
    )
    print(f"Archived prior KB to {archive}")

If `verify` raises, the canonical file is automatically restored from the archive
and a RuntimeError is raised with the original exception chained.

For non-Python KBs (JSON, YAML, SQL), substitute an appropriate verifier:

    verify=lambda: json.loads(canonical.read_text())
    verify=lambda: yaml.safe_load(canonical.read_text())
    verify=lambda: sqlite3.connect(canonical).execute("SELECT 1").fetchone()
"""

from __future__ import annotations

import importlib
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def atomic_swap_kb(
    canonical: Path,
    new_content: str | bytes,
    *,
    verify: Callable[[], Any] | None = None,
    importable_module: str | None = None,
    archive_format: str = "%Y%m%d-%H%M%S",
) -> Path:
    """Archive the canonical file, write new content, verify, rollback on failure.

    Args:
        canonical: Path to the file that downstream consumers import / read.
        new_content: The new content to write. Bytes for binary KBs.
        verify: Callable that raises on invalid content. Either this or
            `importable_module` must be supplied.
        importable_module: Python module name to import as a verification step.
            Used only if `verify` is None.
        archive_format: strftime format for the archive timestamp suffix.
            Default produces `<stem>_YYYYMMDD-HHMMSS<suffix>`.

    Returns:
        Absolute path to the archived prior file (or the canonical path if no
        prior file existed).

    Raises:
        ValueError: if neither `verify` nor `importable_module` is supplied.
        RuntimeError: if verification fails; the canonical file is restored
            from the archive before this is raised.
    """
    if verify is None and importable_module is None:
        raise ValueError("Pass either `verify=...` or `importable_module=...`")

    canonical = canonical.resolve()
    canonical.parent.mkdir(parents=True, exist_ok=True)

    # Archive timestamp = (now - 1s) so it precedes the write moment.
    archive_ts = time.strftime(archive_format, time.gmtime(time.time() - 1))
    archive = canonical.with_name(f"{canonical.stem}_{archive_ts}{canonical.suffix}")

    if canonical.exists():
        shutil.copy2(canonical, archive)

    if isinstance(new_content, bytes):
        canonical.write_bytes(new_content)
    else:
        canonical.write_text(new_content, encoding="utf-8")

    try:
        if verify is not None:
            verify()
        else:
            importlib.invalidate_caches()
            importlib.import_module(importable_module)  # type: ignore[arg-type]
    except Exception as exc:
        if archive.exists():
            shutil.copy2(archive, canonical)
        raise RuntimeError(
            f"Refresh aborted; canonical restored from {archive}. "
            f"Inspect the archive for diagnosis."
        ) from exc

    return archive


def list_archives(canonical: Path, *, limit: int | None = None) -> list[Path]:
    """List archived versions of `canonical`, newest first.

    Useful for "show me the last N refreshes" or selecting a rollback target.
    """
    canonical = canonical.resolve()
    pattern = f"{canonical.stem}_*{canonical.suffix}"
    archives = sorted(
        (p for p in canonical.parent.glob(pattern)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return archives[:limit] if limit is not None else archives


def rollback_to(canonical: Path, archive: Path) -> None:
    """Restore `archive` to `canonical` (manual rollback after the fact).

    Raises FileNotFoundError if either path is missing.
    """
    canonical = canonical.resolve()
    archive = archive.resolve()
    if not archive.exists():
        raise FileNotFoundError(f"Archive not found: {archive}")
    shutil.copy2(archive, canonical)
