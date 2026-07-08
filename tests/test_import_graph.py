"""Import graph — lattice must not import chorus."""

from __future__ import annotations

import ast
from pathlib import Path


def test_lattice_package_never_imports_chorus() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "lattice"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "chorus" or alias.name.startswith("chorus."):
                        offenders.append(f"{path}:{node.lineno} import {alias.name}")
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "chorus" or node.module.startswith("chorus."):
                    offenders.append(f"{path}:{node.lineno} from {node.module}")
    assert offenders == [], "\n".join(offenders)
