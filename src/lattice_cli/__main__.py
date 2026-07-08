"""lattice CLI — offline status over consolidated stores."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lattice", description="lattice consolidation CLI")
    parser.add_argument(
        "--root",
        default=".lattice",
        help="consolidated memory root (default: .lattice)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="show consolidation cursor state")
    status.set_defaults(func=_status)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _status(args: argparse.Namespace) -> int:
    root = Path(args.root)
    cursor_path = root / ".cursor.json"
    if not cursor_path.exists():
        print(f"no consolidation state at {cursor_path}")
        return 0
    print(cursor_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
