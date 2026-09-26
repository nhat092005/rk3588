"""Provenance fields written into every result file (Guide section 8, traceability rule)."""
from __future__ import annotations

import datetime
import hashlib
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def git_dirty() -> bool:
    """True if tracked code under ai/ or scripts/ differs from the commit."""
    try:
        out = subprocess.check_output(["git", "status", "--porcelain", "ai/", "scripts/"], cwd=REPO_ROOT, text=True)
        return bool(out.strip())
    except Exception:
        return True


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance(**extra) -> dict:
    return {
        "git_commit": git_commit(),
        "git_dirty": git_dirty(),
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        **extra,
    }
