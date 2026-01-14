from __future__ import annotations

import ast
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]

CORE_DIRS = [
    "apps/core",
    "apps/users",
    "apps/profile",
    "apps/social",
    "apps/messaging",
    "apps/payments",
    "apps/notifications",
    "apps/moderation",
    "apps/config",
    "apps/contrib_rewards",
    "apps/coin",
    "apps/core_platform",
]

DISALLOWED_PREFIXES = (
    "apps.mentor.services",
    "apps.mentor.tasks",
    "apps.astro.services",
    "apps.astro.tasks",
    "apps.matching.services",
    "apps.matching.tasks",
    "apps.search.client",
    "apps.search.indexers",
    "apps.search.tasks",
    "apps.reco.services",
    "apps.reco.scores",
    "apps.ai.services",
    "apps.matrix.services",
)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for rel in CORE_DIRS:
        root = BASE_DIR / rel
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "migrations" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            files.append(path)
    return files


def _iter_imports(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


@pytest.mark.parametrize("path", _iter_python_files())
def test_core_does_not_import_intelligence_services(path: Path) -> None:
    imports = _iter_imports(path)
    violations = [
        imp
        for imp in imports
        if any(imp.startswith(prefix) for prefix in DISALLOWED_PREFIXES)
    ]
    assert not violations, f"{path} imports intelligence services/tasks: {violations}"
