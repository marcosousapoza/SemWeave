"""File discovery for SemWeave projects."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from semweave.config.schema import TraversalConfig

# Directories to always skip
_ALWAYS_EXCLUDE = {".git", "__pycache__", "node_modules", ".svn", ".hg"}


def scan_project(root: Path, config: TraversalConfig) -> list[Path]:
    """Discover files in a project directory matching traversal config.

    Walks the directory tree, applies include/exclude glob patterns,
    and filters by extension if configured.
    """
    root = root.resolve()
    files: list[Path] = []

    for path in _walk(root):
        rel = path.relative_to(root)
        rel_str = str(rel)

        if _matches_any(rel_str, config.exclude):
            continue

        if config.include and not _matches_any(rel_str, config.include):
            continue

        if config.extensions is not None:
            if path.suffix not in config.extensions:
                continue

        files.append(path)

    files.sort()
    return files


def _walk(root: Path) -> list[Path]:
    """Walk directory tree, skipping always-excluded directories."""
    files: list[Path] = []
    for item in sorted(root.iterdir()):
        if item.name.startswith(".") and item.is_dir():
            continue
        if item.name in _ALWAYS_EXCLUDE:
            continue
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(_walk(item))
    return files


def _matches_any(rel_path: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any glob pattern.

    Supports ** for recursive matching. Works around Python <3.12
    PurePosixPath.match() not matching root-level files for ** patterns.
    """
    if not patterns:
        return False
    p = PurePosixPath(rel_path)
    for pattern in patterns:
        if pattern in ("**/*", "**"):
            return True
        if p.match(pattern):
            return True
        # Workaround: '**/*.tex' doesn't match 'main.tex' in Python <3.12.
        # Try matching without the '**/' prefix for root-level files.
        if pattern.startswith("**/") and PurePosixPath(rel_path).match(pattern[3:]):
            return True
    return False
