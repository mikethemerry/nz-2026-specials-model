#!/usr/bin/env python3
"""Rebuild data/inputs/calibration.json from the raw CSVs in data/raw/history/.

    python scripts/build_calibration.py --check   # compare with the committed file, change nothing
    python scripts/build_calibration.py           # overwrite data/inputs/calibration.json

Run `python scripts/fetch_raw.py history` first.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nzspecials.calibration import RAW, build, compare  # noqa: E402

TARGET = ROOT / "data" / "inputs" / "calibration.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report differences from the committed file and exit")
    a = ap.parse_args()
    if not RAW.exists() or not any(RAW.iterdir()):
        print("No raw data in data/raw/history/. Run: python scripts/fetch_raw.py history", file=sys.stderr)
        return 2
    new = build()
    committed = json.loads(TARGET.read_text()) if TARGET.exists() else {}
    diffs = compare(new, committed)
    if a.check:
        if diffs:
            print(f"{len(diffs)} differences from the committed calibration:")
            for d in diffs[:50]:
                print("  ", d)
            return 1
        print("Rebuilt calibration matches data/inputs/calibration.json")
        return 0
    TARGET.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {TARGET.relative_to(ROOT)} ({len(diffs)} values changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
