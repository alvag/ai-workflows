"""Requires exactly one final STATUS: done signal.

This descriptive docstring has no historical predicate span.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:status raw", file=sys.stderr)
        return 2
    try:
        lineas = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        lineas = []
    no_vacias = [linea for linea in lineas if linea.strip()]
    return 0 if lineas.count("STATUS: done") == 1 and no_vacias and no_vacias[-1] == "STATUS: done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
