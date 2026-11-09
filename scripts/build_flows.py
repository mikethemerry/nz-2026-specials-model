#!/usr/bin/env python3
"""Rebuild data/inputs/flows_2023.json from the raw split-vote CSVs in data/raw/splitvotes/2023/.

    python scripts/build_flows.py --check   # compare with the committed file, change nothing
    python scripts/build_flows.py           # overwrite data/inputs/flows_2023.json (keeps its _source note)

Get the raw files with scripts/browser_fetch.js (the archive blocks scripted downloads).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nzspecials.splitvotes import RAW, build, compare  # noqa: E402

TARGET = ROOT / "data" / "inputs" / "flows_2023.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not RAW.exists() or not any(RAW.glob("*.csv")):
        print("No split-vote files in data/raw/splitvotes/2023/. Run scripts/browser_fetch.js in a browser (see its header).", file=sys.stderr)
        return 2
    new = build()
    committed = json.loads(TARGET.read_text())
    diffs = compare(new, committed)
    if a.check:
        if diffs:
            print(f"{len(diffs)} differences from the committed flow weights:")
            for d in diffs[:40]:
                print("  ", d)
            return 1
        print("Rebuilt flow weights match data/inputs/flows_2023.json")
        return 0
    TARGET.write_text(json.dumps({"_source": committed.get("_source", ""), **new}, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {TARGET.relative_to(ROOT)} ({len(diffs)} values changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
