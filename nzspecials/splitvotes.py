"""Build data/inputs/flows_2023.json from the Commission's 2023 split-vote statistics.

Raw files: data/raw/splitvotes/2023/{n}.csv, one per electorate
(archive.electionresults.govt.nz/electionresults_2023/statistics/csv/split-votes-electorate-N.csv).
Each row is a party vote; columns give the percentage of that party's voters who
gave their electorate vote to each candidate, informal, or party vote only.

The fit is the one described in nzspecials/flows.py: for voters of party p, the
chance of choosing candidate type c from the set A standing in a seat is
w[p][c] / sum(w[p][a] for a in A), with ABS (informal or party vote only) always
available at weight 1. Weights are fitted by maximum likelihood with the
minorisation-maximisation (Luce / Bradley-Terry) update, separately for general
and Māori electorates.
"""
from __future__ import annotations

import csv
import io
import math
from pathlib import Path

from .allocation import PARTIES
from .flows import MAORI_SEATS

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "splitvotes" / "2023"
TYPES = ["NAT", "LAB", "GP", "ACT", "NZF", "OPP", "TPM", "OTH", "IND", "ABS"]


def code(party: str) -> str:
    p = (party or "").strip()
    for prefix, k in (("National", "NAT"), ("Labour", "LAB"), ("Green", "GP"), ("ACT", "ACT"), ("New Zealand First", "NZF")):
        if p.startswith(prefix):
            return k
    if "Opportunit" in p:
        return "OPP"
    if p.startswith("Te Pāti Māori") or p.startswith("Māori Party"):
        return "TPM"
    if p in ("", "Independent"):
        return "IND"
    return "OTH"


def last_paren(x: str) -> str:
    """Party from 'NAME (Party (ABBR))': the contents of the last top-level brackets."""
    x = x.strip()
    if not x.endswith(")"):
        return ""
    depth = 0
    for i in range(len(x) - 1, -1, -1):
        if x[i] == ")":
            depth += 1
        elif x[i] == "(":
            depth -= 1
            if depth == 0:
                return x[i + 1:-1]
    return ""


def parse(text: str) -> tuple[str, list[str], dict]:
    """-> (electorate name, column types, {party code: [counts per column]})."""
    rows = list(csv.reader(io.StringIO(text.strip())))
    head = rows[0]
    name = head[0].split(" ", 1)[1].strip() if " " in head[0] else head[0]
    cand = []
    for x in head[2:-1]:
        if x.startswith("Informal"):
            cand.append("INF")
        elif x.startswith("Party Vote Only"):
            cand.append("PVO")
        else:
            cand.append(code(last_paren(x)))
    cols = list(dict.fromkeys(cand))
    M: dict = {}
    for r in rows[1:]:
        if r[0].startswith("Informal Party") or r[0].startswith("Total"):
            continue
        p, n = code(r[0]), float(r[1])
        M.setdefault(p, [0.0] * len(cols))
        for i, c in enumerate(cand):
            M[p][cols.index(c)] += n * float(r[2 + i]) / 100
    M = {p: [math.floor(v + 0.5) for v in row] for p, row in M.items()}    # as JavaScript Math.round
    return name, cols, M


def fit(seats: list[tuple[list[str], dict]], iters: int = 500) -> dict:
    W = {}
    for p in PARTIES:
        data = []
        for cols, M in seats:
            row = M.get(p, [0] * len(cols))
            cnt: dict = {}
            for c, v in zip(cols, row):
                k = "ABS" if c in ("INF", "PVO") else c
                cnt[k] = cnt.get(k, 0) + v
            data.append(cnt)
        w = {c: 1.0 for c in TYPES}
        N = {c: sum(s.get(c, 0) for s in data) for c in TYPES}
        for _ in range(iters):
            den = {c: 0.0 for c in TYPES}
            for s in data:
                n = sum(s.values())
                sw = sum(w[c] for c in s)
                if n > 0:
                    for c in s:
                        den[c] += n / sw
            nw = {c: (max(N[c], 0.5) / den[c] if den[c] > 0 else 0.0) for c in TYPES}
            z = nw["ABS"] or 1.0
            w = {c: v / z for c, v in nw.items()}
        W[p] = {c: float(f"{w[c]:.4g}") for c in TYPES}
    return W


def build(raw: Path = RAW) -> dict:
    files = sorted(raw.glob("*.csv"), key=lambda f: int(f.stem))
    gen, mao = [], []
    for f in files:
        name, cols, M = parse(f.read_text(encoding="utf-8-sig"))
        (mao if name in MAORI_SEATS else gen).append((cols, M))
    return {"general": fit(gen), "maori": fit(mao)}


def compare(new: dict, committed: dict, rel: float = 2e-3) -> list[str]:
    diffs = []
    for region in ("general", "maori"):
        for p in PARTIES:
            for c in TYPES:
                a, b = new[region][p][c], committed[region][p][c]
                if abs(a - b) > rel * max(abs(b), 1e-9) and abs(a - b) > 1e-4:
                    diffs.append(f"{region}/{p}/{c}: rebuilt {a} vs committed {b}")
    return diffs
