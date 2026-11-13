"""Fail when a public top-level name is defined in more than one repo.

Enforces STANDARDS.md rule "one home".
"""

import ast
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREES = {"common": "common/python", "ai": "ai/ai", "deploy": "deploy/python"}
IGNORED = {"main", "parse_args"}


def public_names(path: Path) -> Iterator[str]:
    """Yield public top-level names defined in a Python module."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            names = [node.target.id]
        else:
            continue
        yield from (
            n for n in names if not n.startswith("_") and n not in IGNORED
        )


def main() -> int:
    """Check repository trees for duplicate public top-level names."""
    homes = defaultdict(set)
    for repo, tree in TREES.items():
        for path in sorted((ROOT / tree).rglob("*.py")):
            for name in public_names(path):
                homes[name].add(f"{repo}:{path.relative_to(ROOT)}")
    clashes = {
        name: places
        for name, places in homes.items()
        if len({p.split(":")[0] for p in places}) > 1
    }
    for name, places in sorted(clashes.items()):
        print(f"{name} defined in {', '.join(sorted(places))}")
    return 1 if clashes else 0


if __name__ == "__main__":
    sys.exit(main())
