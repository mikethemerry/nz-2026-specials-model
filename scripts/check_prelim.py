#!/usr/bin/env python3
"""Compare data/inputs/prelim_2026.json with a saved snapshot of the 2026 results pages.

    python scripts/check_prelim.py                     # latest snapshot in data/raw/ge2026/
    python scripts/check_prelim.py data/raw/ge2026/2026-11-08

Checks party votes, each electorate's leader, runner-up and margin, and votes
counted. Run against a snapshot taken before 27 November 2026 it should report
no differences; against the official result it lists what changed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nzspecials.calibration import read_text  # noqa: E402
from nzspecials.ge2026 import parse_electorate_status, parse_overall, parse_votes_counted  # noqa: E402
from nzspecials.sources import party_key  # noqa: E402

SNAPS = ROOT / "data" / "raw" / "ge2026"
PRELIM = ROOT / "data" / "inputs" / "prelim_2026.json"


def main() -> int:
    if len(sys.argv) > 1:
        snap = Path(sys.argv[1])
    else:
        dated = sorted(p for p in SNAPS.glob("*") if p.is_dir()) if SNAPS.exists() else []
        if not dated:
            print("No snapshot found. Run: python scripts/fetch_raw.py ge2026", file=sys.stderr)
            return 2
        snap = dated[-1]
    prelim = json.loads(PRELIM.read_text())
    diffs = []

    votes: dict = {}
    for name, v in parse_overall(read_text(snap / "index.html")).items():
        if any(w in name.lower() for w in ("total", "informal", "disallowed")):
            continue
        k = party_key(name)
        votes[k] = votes.get(k, 0) + v
    for k, v in prelim["party_votes"].items():
        if votes.get(k) != v:
            diffs.append(f"party vote {k}: snapshot {votes.get(k)} vs prelim {v}")

    status = parse_electorate_status(read_text(snap / "electorate-status.html"))
    for name, e in prelim["electorates"].items():
        s = status.get(name)
        if not s:
            diffs.append(f"{name}: not in snapshot")
            continue
        for f in ("leader", "runner_up", "margin"):
            if s[f] != e[f]:
                diffs.append(f"{name} {f}: snapshot {s[f]} vs prelim {e[f]}")
        if s.get("details") and (snap / s["details"]).exists():
            vc = parse_votes_counted(read_text(snap / s["details"]))
            if vc != e["votes_counted"]:
                diffs.append(f"{name} votes counted: snapshot {vc} vs prelim {e['votes_counted']}")

    print(f"Snapshot {snap.relative_to(ROOT) if snap.is_relative_to(ROOT) else snap}: {len(diffs)} differences")
    for d in diffs:
        print("  ", d)
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
