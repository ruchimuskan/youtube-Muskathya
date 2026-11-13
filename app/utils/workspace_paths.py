from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Repo root (parent of `app/`)."""
    return Path(__file__).resolve().parents[2]


def abs_path(path: str | Path) -> Path:
    """Absolute path for queued uploads — survives GHA checkout cwd changes."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (project_root() / p).resolve()
    else:
        p = p.resolve()
    return p


def abs_path_str(path: str | Path) -> str:
    return str(abs_path(path))
