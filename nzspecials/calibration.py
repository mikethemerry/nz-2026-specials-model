"""Build data/inputs/calibration.json from the raw historical CSVs.

Reproduces exactly the derivation used for the published dashboard:

* party_votes_by_special_category: nationwide sums of each party's votes in
  each special-vote category and in total, per election.
* mean_seat_swing_lab_minus_nat_pp / _lab_minus_tpm_pp: average swing on
  specials in seats where Labour and National (or Te Pāti Māori) are the top
  two, per election.
* seat_lean_2017_2023_pp: each seat's average deviation from that year's
  mean Labour-v-National swing, over 2017-2023 (by seat name).
* seat_lean_2008_2023_pp: the same over 2008-2023 for the three key
  marginals (sensitivity check only).
* special_to_ordinary_ratio_2023: special / ordinary candidate votes per seat in 2023.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .sources import YEARS, parse_candidate_file, parse_party_file, swing_lab_minus, top_two

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "history"
KEY_MARGINALS = ["Wairarapa", "Hamilton East", "Mt Roskill"]
PREDECESSORS = {"East Cape": "East Coast", "Glendene": "Kelston", "Henderson": "Te Atatū",
                "Kapiti": "Ōtaki", "Kenepuru": "Mana", "Mt Maunganui": "Bay of Plenty",
                "Ōtāhuhu": "Panmure-Ōtāhuhu", "Waitākere": "New Lynn",
                "Wellington Bays": "Rongotai", "Wellington North": "Wellington Central"}


def read_text(path: Path) -> str:
    """Older Commission CSVs are Windows-1252; newer ones are UTF-8 (sometimes with a BOM)."""
    b = path.read_bytes()
    try:
        return b.decode("utf-8-sig")
    except UnicodeDecodeError:
        return b.decode("cp1252")


def _files(year: str, kind: str):
    d = RAW / year / kind
    return sorted(d.glob("*.csv"), key=lambda p: int(p.stem)) if d.exists() else []


def build(raw: Path = RAW) -> dict:
    global RAW
    RAW = raw
    party_hist, seat_rows = {}, {}
    for y in YEARS:
        cats: dict = {}
        for f in _files(y, "party"):
            for cat, d in parse_party_file(read_text(f)).items():
                for p, v in d.items():
                    cats.setdefault(cat, {})
                    cats[cat][p] = cats[cat].get(p, 0) + v
        party_hist[y] = cats
        rows = []
        for f in _files(y, "candidate"):
            t = top_two(parse_candidate_file(read_text(f)))
            if t:
                rows.append(t)
        seat_rows[y] = rows

    labnat, labtpm, resid = {}, {}, {}
    for y, rows in seat_rows.items():
        ln = {r["electorate"]: swing_lab_minus(r, "NAT") for r in rows}
        ln = {k: v for k, v in ln.items() if v is not None}
        lt = [v for v in (swing_lab_minus(r, "TPM") for r in rows) if v is not None]
        if ln:
            m = float(np.mean(list(ln.values())))
            labnat[y] = round(m, 2)
            resid[y] = {k: v - m for k, v in ln.items()}
        if len(lt) >= 3:
            labtpm[y] = round(float(np.mean(lt)), 2)

    names = set(resid.get("2023", {})) | set(resid.get("2020", {}))
    lean = {}
    for n in names:
        v = [resid[y][n] for y in ["2017", "2020", "2023"] if n in resid.get(y, {})]
        lean[n] = round(float(np.mean(v)), 1)
    lean6 = {}
    for n in (m for m in KEY_MARGINALS if m in lean):
        old = [resid[y][n] for y in ["2008", "2011", "2014"] if n in resid.get(y, {})]
        lean6[n] = round((lean[n] * 3 + sum(old)) / 6, 1)

    ratio23 = {r["electorate"]: round(r["S"] / r["O"], 3) for r in seat_rows.get("2023", [])}

    # net special-vote gain, Labour minus National, in the key marginals
    hist_rows = []
    for n in KEY_MARGINALS:
        for y in YEARS:
            r = next((r for r in seat_rows.get(y, []) if r["electorate"] == n and {r["a"], r["b"]} == {"LAB", "NAT"}), None)
            if r:
                lab, nat = (r["sa"], r["sb"]) if r["a"] == "LAB" else (r["sb"], r["sa"])
                hist_rows.append({"seat": n, "year": int(y), "labour_net": lab - nat})

    # The model's templates are 2014-2023 (2008/2011 included for the sensitivity run)
    return {
        "_source": "Derived from Electoral Commission voting-place statistics 2008-2023 (archive.electionresults.govt.nz) by `make calibrate`",
        "party_votes_by_special_category": party_hist,
        "mean_seat_swing_lab_minus_nat_pp": labnat,
        "mean_seat_swing_lab_minus_tpm_pp": labtpm,
        "special_to_ordinary_ratio_2023": ratio23,
        "seat_lean_2017_2023_pp": lean,
        "seat_lean_2008_2023_pp": lean6,
        "predecessor_seats": PREDECESSORS,
        "marginal_history": hist_rows,
    }


def compare(new: dict, committed: dict, tol: float = 0.051) -> list[str]:
    """Differences between a rebuilt calibration and the committed one."""
    diffs = []

    def walk(a, b, path):
        if isinstance(b, dict):
            for k in b:
                if k.startswith("_"):
                    continue
                if not isinstance(a, dict) or k not in a:
                    diffs.append(f"missing {path}/{k}")
                else:
                    walk(a[k], b[k], f"{path}/{k}")
        elif isinstance(b, (int, float)):
            if not isinstance(a, (int, float)) or abs(a - b) > tol:
                diffs.append(f"{path}: rebuilt {a} vs committed {b}")
        elif a != b:
            diffs.append(f"{path}: rebuilt {a!r} vs committed {b!r}")
    walk(new, committed, "")
    return diffs
