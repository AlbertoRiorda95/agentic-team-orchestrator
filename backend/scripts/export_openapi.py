"""Export the API contract from FastAPI to docs/api/openapi.yaml.

Usage (from the repository root):
    uv run --directory backend python scripts/export_openapi.py [--output PATH] [--check]

--check exits with status 1 when the file differs from the export, without writing it.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from app.main import contract

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.yaml"


class _NoAliasDumper(yaml.SafeDumper):
    """Write repeated values in full: no &id001 anchors in the contract."""

    def ignore_aliases(self, data: Any) -> bool:
        return True


def render(document: dict[str, Any]) -> str:
    return yaml.dump(
        document,
        Dumper=_NoAliasDumper,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if the file is out of date")
    args = parser.parse_args(argv)

    text = render(contract())
    output: Path = args.output
    if args.check:
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        if current != text:
            print(f"{output} is out of date: run 'make openapi' and commit it.", file=sys.stderr)
            return 1
        return 0
    output.write_text(text, encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
