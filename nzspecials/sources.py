"""Download and parse Electoral Commission results files.

Historical data: the "votes recorded at each voting place" CSVs published in
the official-results statistics for each general election. Each file covers
one electorate and ends with summary rows for special votes (before polling
day, on polling day, overseas) and the electorate total.

* 2017-2023: archive.electionresults.govt.nz/electionresults_<year>/statistics/csv/
  candidate-votes-by-voting-place-<n>.csv and party-votes-by-voting-place-<n>.csv
* 2008-2014: archive.electionresults.govt.nz/electionresults_<year>/e9/csv/
  e9_part8_cand_<n>.csv and e9_part8_party_<n>.csv
"""
from __future__ import annotations

import csv
import io
import re

ARCHIVE = "https://archive.electionresults.govt.nz"
YEARS = ["2008", "2011", "2014", "2017", "2020", "2023"]
MAX_ELECTORATES = 72


def history_url(year: str, kind: str, n: int) -> str:
    """kind is 'candidate' or 'party'."""
    if int(year) >= 2017:
        return f"{ARCHIVE}/electionresults_{year}/statistics/csv/{kind}-votes-by-voting-place-{n}.csv"
    short = "cand" if kind == "candidate" else "party"
    return f"{ARCHIVE}/electionresults_{year}/e9/csv/e9_part8_{short}_{n}.csv"


def party_key(name: str) -> str:
    """Map a party name as printed in the results to the model's party codes."""
    n = (name or "").lower()
    if "national" in n:
        return "NAT"
    if "labour" in n:
        return "LAB"
    if "green" in n:
        return "GP"
    if n.startswith("act"):
        return "ACT"
    if "new zealand first" in n or "nz first" in n:
        return "NZF"
    if "opportunit" in n:
        return "OPP"
    if "māori" in n or "maori" in n:
        return "TPM"
    return "OTH"


def _rows(text: str):
    return list(csv.reader(io.StringIO(text)))


def _num(x) -> int:
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def _header(rows):
    """The header row starts with two empty cells; returns (index, names, total-column index)."""
    hi = next(i for i, r in enumerate(rows) if len(r) > 2 and r[0] == "" and r[1] == "")
    h = rows[hi]
    total_col = next(i for i, c in enumerate(h) if re.search(r"Total Valid", c, re.I))
    return hi, h[2:total_col], total_col


# Special-vote summary rows start with these words. Match from the start of the
# label: some polling places have "Special" or "Overseas" in their name
# ("Sunnydene Special School", "Special Needs Library", "Overseas Terminal")
# and must be counted as ordinary votes. Overseas rows include 2020's
# "Overseas Votes Allowed for Party Only" and 2023's "Overseas Special Votes
# for Party Only".
SPECIAL_ROW = re.compile(r"\s*(Special Votes|Overseas (Special )?Votes)", re.I)


def is_special_row(label: str) -> bool:
    return bool(SPECIAL_ROW.match(label or ""))


def category(label: str, first_cell: str) -> str | None:
    """Classify a summary row: SP_overseas, SP_before, SP_on, TOTAL or None."""
    if is_special_row(label):
        if re.match(r"\s*Overseas", label, re.I):
            return "SP_overseas"
        if re.search(r"\bBEFORE\b", label, re.I):
            return "SP_before"
        if re.search(r"\bON\b", label, re.I):
            return "SP_on"
    if first_cell == "" and re.search(r" Total$", label):
        return "TOTAL"
    return None


def parse_party_file(text: str) -> dict:
    """Party votes by special-vote category for one electorate.

    Returns {"SP_before": {party: votes}, "SP_on": ..., "SP_overseas": ..., "TOTAL": ...}.
    Overseas includes the 2023 'Overseas Special Votes for Party Only' row.
    """
    rows = _rows(text)
    _, names, tc = _header(rows)
    keys = [party_key(n) for n in names]
    out: dict = {}
    for r in rows:
        if len(r) < 2:
            continue
        lab = r[1]
        if r[0] != "" and not re.search(r"Special|Ordinary|less than", lab, re.I):
            continue
        cat = category(lab, r[0])
        if not cat:
            continue
        for p, v in zip(keys, r[2:tc]):
            out.setdefault(cat, {})
            out[cat][p] = out[cat].get(p, 0) + _num(v)
    return out


def parse_candidate_file(text: str) -> dict:
    """Candidate votes for one electorate: total and special votes per candidate, with party."""
    rows = _rows(text)
    name = re.sub(r"\s*\d+$", "", rows[1][0])
    _, cands, tc = _header(rows)
    special = [0] * len(cands)
    total = None
    total_valid = special_valid = 0
    for r in rows:
        if len(r) < 2 or r[0] != "":
            continue
        if is_special_row(r[1]):
            for i, v in enumerate(r[2:tc]):
                special[i] += _num(v)
            special_valid += _num(r[tc])
        elif re.search(r" Total$", r[1]):
            total = [_num(v) for v in r[2:tc]]
            total_valid = _num(r[tc])
    party = {}
    for r in rows:
        if r and r[0] in cands and len(r) > 1:
            party[r[0]] = party_key(r[1])
    pname = {}
    for r in rows:
        if r and r[0] in cands and len(r) > 1:
            pname[r[0]] = r[1]
    cand = [{"name": c, "party": party.get(c, "IND"), "party_name": pname.get(c, ""), "total": (total or [0] * len(cands))[i], "special": special[i]}
            for i, c in enumerate(cands)]
    return {"electorate": name, "candidates": cand, "total_valid": total_valid, "special_valid": special_valid}


def top_two(parsed: dict) -> dict | None:
    """Leader and runner-up with ordinary and special votes, or None if the electorate has no data."""
    c = sorted(parsed["candidates"], key=lambda x: -x["total"])
    O = parsed["total_valid"] - parsed["special_valid"]
    S = parsed["special_valid"]
    if len(c) < 2 or not O or not S:
        return None
    a, b = c[0], c[1]
    return {"electorate": parsed["electorate"], "a": a["party"], "b": b["party"], "O": O, "S": S,
            "oa": a["total"] - a["special"], "ob": b["total"] - b["special"], "sa": a["special"], "sb": b["special"]}


def swing_lab_minus(row: dict, other: str) -> float | None:
    """Swing on specials in the Labour-minus-`other` margin share, in points.

    (special-vote margin share) minus (ordinary-vote margin share), signed so
    positive means specials favoured Labour.
    """
    if {row["a"], row["b"]} != {"LAB", other}:
        return None
    sign = 1 if row["a"] == "LAB" else -1
    return sign * ((row["sa"] - row["sb"]) / row["S"] - (row["oa"] - row["ob"]) / row["O"]) * 100
