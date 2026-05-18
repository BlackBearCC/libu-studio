#!/usr/bin/env python3
"""Compare exported manifest vs original main-repo manifest, field-level."""
import json
import sys
from pathlib import Path


def diff(a, b, path=""):
    """Yield (path, kind, a_val, b_val) for every mismatch."""
    if type(a) != type(b):
        yield (path or "/", "TYPE", a, b)
        return
    if isinstance(a, dict):
        keys = sorted(set(a) | set(b))
        for k in keys:
            sub = f"{path}.{k}" if path else k
            if k not in a:
                yield (sub, "MISSING_A", None, b[k])
            elif k not in b:
                yield (sub, "MISSING_B", a[k], None)
            else:
                yield from diff(a[k], b[k], sub)
    elif isinstance(a, list):
        if len(a) != len(b):
            yield (path or "/", "LEN", len(a), len(b))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            yield from diff(x, y, f"{path}[{i}]")
    else:
        if a != b:
            yield (path or "/", "VAL", a, b)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: verify-roundtrip.py <original> <exported>")
    a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    b = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    diffs = list(diff(a, b))
    if not diffs:
        print("OK  round-trip is field-level identical")
        return
    print(f"DIFF  {len(diffs)} mismatches:")
    for p, kind, av, bv in diffs:
        print(f"  [{kind}] {p}")
        print(f"    original: {av!r}")
        print(f"    exported: {bv!r}")
    sys.exit(1)


if __name__ == "__main__":
    main()
