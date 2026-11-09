#!/usr/bin/env python3
"""Backtest the candidate-flow electorate model against 2017-2023 special votes.

For every electorate, calibrate the flows to that year's ordinary votes (party
and candidate), then predict the special-vote margin between the top two
candidates and compare it with the actual special-vote margin:

  A  flows applied to the seat's *actual* special party votes (tests the
     party -> candidate step on its own)
  B  flows applied to *predicted* special party votes: the seat's ordinary party
     vote x that year's national special/ordinary ratio (what the model does)
  C  the previous pairwise method (Labour v National seats only): that year's
     mean swing + 0.75 x the seat's 2017-2023 lean (in-sample, so flattering)

Errors are in points of the special-vote margin. Writes outputs/backtest_flows.json.

    python scripts/backtest_flows.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nzspecials.allocation import PARTIES  # noqa: E402
from nzspecials.calibration import RAW, _files, read_text  # noqa: E402
from nzspecials.data import load_calibration  # noqa: E402
from nzspecials.flows import MAORI_SEATS, base_matrix, calibrate, candidate_type, flows, load_weights  # noqa: E402
from nzspecials.sources import parse_candidate_file, parse_party_file  # noqa: E402

SPECIAL = ["SP_before", "SP_on", "SP_overseas"]
OLD_MAORI = MAORI_SEATS | {"Te Tai Tokerau", "Waiariki", "Tainui"}


def seat_rows(year: str):
    party = {}
    for f in _files(year, "party"):
        d = parse_party_file(read_text(f))
        name = parse_candidate_file(read_text(RAW / year / "candidate" / f.name))["electorate"]
        party[name] = d
    for f in _files(year, "candidate"):
        c = parse_candidate_file(read_text(f))
        if c["electorate"] in party:
            yield c, party[c["electorate"]]


def vec(d: dict) -> np.ndarray:
    return np.array([d.get(p, 0) for p in PARTIES], float)


def swing(F, O, Sh, top):
    """Special minus ordinary margin rate (pts) between candidates top[0] and top[1] under flows F."""
    so, ss = (O @ F)[:-1], (Sh @ F)[:-1]
    return ((ss[top[0]] - ss[top[1]]) / ss.sum() - (so[top[0]] - so[top[1]]) / so.sum()) * 100


def field_delta(types, top, B, F, O, Sh, maori, W, majors=("NAT", "LAB", "GP", "ACT", "NZF", "OPP")):
    """Swing with the actual field minus swing with the absent major parties' candidates added."""
    miss = [t for t in majors if t not in types and O[PARTIES.index(t)] > 0.03 * O.sum()]
    if not miss:
        return 0.0
    m = (F[0] / B[0]) / (F[0, -1] / B[0, -1])
    Bc = base_matrix(types + miss, maori, W)
    mc = np.concatenate([m[:-1], np.ones(len(miss)), [1.0]])
    Fc = flows(Bc, mc)
    return swing(F, O, Sh, top) - swing(Fc, O, Sh, top)


def main() -> int:
    W = load_weights()
    calib = load_calibration()
    lean = calib["seat_lean_2017_2023_pp"]
    mean_sw = calib["mean_seat_swing_lab_minus_nat_pp"]
    results, rows = {}, []
    # pass 1: per-seat data, national ratios, seat-level special-composition leans and pairwise residuals
    seats, natr, devs, resid = {}, {}, {}, {}
    for year in ["2017", "2020", "2023"]:
        data = list(seat_rows(year))
        if not data:
            print(f"{year}: no raw data (run make fetch)")
            continue
        natS = sum(sum(vec(p.get(k, {})) for k in SPECIAL) for _, p in data)
        natO = sum(vec(p["TOTAL"]) for _, p in data) - natS
        natr[year] = (natS / natS.sum()) / np.maximum(natO / natO.sum(), 1e-9)
        seats[year] = []
        for c, p in data:
            S = sum(vec(p.get(k, {})) for k in SPECIAL)
            O = vec(p["TOTAL"]) - S
            if S.sum() < 100 or O.sum() < 1000 or "Cancelled" in c["electorate"]:
                continue
            seats[year].append((c, S, O))
            dev = np.log(((S + 5) / S.sum()) / ((O + 5) / O.sum())) - np.log(natr[year])
            devs.setdefault(c["electorate"], {})[year] = dev
            cands = c["candidates"]
            ordc = np.array([x["total"] - x["special"] for x in cands], float)
            spc = np.array([x["special"] for x in cands], float)
            top = np.argsort(-(ordc + spc))[:2]
            if {cands[top[0]]["party"], cands[top[1]]["party"]} == {"LAB", "NAT"} and c["electorate"] not in OLD_MAORI:
                sgn = 1 if cands[top[0]]["party"] == "LAB" else -1
                d = sgn * ((spc[top[0]] - spc[top[1]]) / spc.sum() - (ordc[top[0]] - ordc[top[1]]) / ordc.sum()) * 100
                resid.setdefault(year, {})[c["electorate"]] = d
    for y in resid:
        mu = np.mean(list(resid[y].values()))
        resid[y] = {k: v - mu for k, v in resid[y].items()}

    for year, items in seats.items():
        ratio = natr[year]
        for c, S, O in items:
            nm = c["electorate"]
            cands = c["candidates"]
            types = [candidate_type(x["party"], x.get("party_name", "")) for x in cands]
            ordc = np.array([x["total"] - x["special"] for x in cands], float)
            spc = np.array([x["special"] for x in cands], float)
            maori = nm in OLD_MAORI
            B = base_matrix(types, maori, W)
            F = flows(B, calibrate(B, O, ordc, O.sum() - ordc.sum()))
            top = np.argsort(-(ordc + spc))[:2]
            act = (spc[top[0]] - spc[top[1]]) / spc.sum() * 100
            marg = lambda v: (v[top[0]] - v[top[1]]) / v.sum() * 100 - act
            def comp(lean):
                Sh = O * ratio * np.exp(lean)
                return (Sh * S.sum() / Sh.sum()) @ F
            other = [devs[nm][y] for y in devs.get(nm, {}) if y != year]     # leave this year out
            lean_oo = np.mean(other, axis=0) if other else np.zeros(len(PARTIES))
            row = {"year": int(year), "seat": nm, "maori": maori,
                   "top2": [cands[top[0]]["party"], cands[top[1]]["party"]],
                   "missing": [t for t in ("NAT", "LAB", "GP", "ACT", "NZF", "OPP") if t not in types and O[PARTIES.index(t)] > 0.03 * O.sum()],
                   "actual": round(act, 2),
                   "A": round(marg((S @ F)[:-1]), 2),
                   "B": round(marg(comp(0)[:-1]), 2)}
            for sh in (0.5, 0.75, 1.0):
                row[f"B_lean{sh}"] = round(marg(comp(sh * lean_oo)[:-1]), 2)
            pair = {cands[top[0]]["party"], cands[top[1]]["party"]}
            if pair == {"LAB", "NAT"} and not maori:
                sgn = 1 if cands[top[0]]["party"] == "LAB" else -1
                om = (ordc[top[0]] - ordc[top[1]]) / ordc.sum() * 100
                oth = [resid[y][nm] for y in resid if y != year and nm in resid[y]]
                lean_c = 0.75 * np.mean(oth) if oth else 0.0
                row["C"] = round(sgn * (sgn * om + mean_sw[year] + 0.75 * lean.get(nm, 0)) - act, 2)
                row["C_loyo"] = round(sgn * (sgn * om + mean_sw[year] + lean_c) - act, 2)
                row["C_no_lean"] = round(sgn * (sgn * om + mean_sw[year]) - act, 2)
                # candidate-field adjustment: flows with the actual field minus flows with the missing parties added
                Sh = O * ratio * np.exp(0.75 * lean_oo); Sh *= S.sum() / Sh.sum()
                row["delta"] = round(field_delta(types, top, B, F, O, Sh, maori, W), 2)
                row["C_loyo_adj"] = round(row["C_loyo"] + row["delta"], 2)
            rows.append(row)

    def rmse(key, sel=lambda r: True):
        v = [r[key] for r in rows if key in r and sel(r)]
        return (round(float(np.sqrt(np.mean(np.square(v)))), 2), len(v)) if v else None

    labnat = lambda r: "C" in r
    miss = lambda r: bool(r["missing"])
    K = ["A", "B", "B_lean0.5", "B_lean0.75", "B_lean1.0"]
    results = {
        "note": "RMSE in points of the special-vote margin between the top two; [rmse, seats]. B_lean* and C_loyo use only the other years' data for the seat lean (out of sample); C uses the published in-sample 2017-2023 lean.",
        "all_seats": {k: rmse(k) for k in K},
        "lab_v_nat_seats": {**{k: rmse(k, labnat) for k in K}, "C_in_sample": rmse("C", labnat), "C_loyo": rmse("C_loyo", labnat), "C_no_lean": rmse("C_no_lean", labnat)},
        "lab_v_nat_with_a_missing_candidate": {"B_lean0.75": rmse("B_lean0.75", lambda r: labnat(r) and miss(r)), "C_loyo": rmse("C_loyo", lambda r: labnat(r) and miss(r)), "C_loyo_adj": rmse("C_loyo_adj", lambda r: labnat(r) and miss(r))},
        "lab_v_nat_all_with_adjustment": {"C_loyo": rmse("C_loyo", labnat), "C_loyo_adj": rmse("C_loyo_adj", labnat)},
        "by_year": {y: {"C_loyo": rmse("C_loyo", lambda r, y=y: r["year"] == y), "C_loyo_adj": rmse("C_loyo_adj", lambda r, y=y: r["year"] == y)} for y in (2017, 2020, 2023)},
        "key_seats": [r for r in rows if r["seat"] in ("Hamilton East", "Wairarapa", "Mt Roskill")],
        "rows": rows,
    }
    # numbers quoted in the site's methodology (docs/data/backtest.json)
    lv = [r for r in rows if "C" in r]
    ms = [r for r in lv if r["missing"]]
    f = lambda k, sel: round(float(np.sqrt(np.mean([r[k] ** 2 for r in sel]))), 1)
    site = [{"key": k, "value": v} for k, v in [
        ("seat_years", len(lv)), ("seat_years_missing", len(ms)),
        ("swing_rmse", f("C_loyo", lv)), ("swing_field_rmse", f("C_loyo_adj", lv)),
        ("swing_missing_rmse", f("C_loyo", ms)), ("swing_field_missing_rmse", f("C_loyo_adj", ms)),
        ("flows_only_rmse", f("B_lean0.75", lv)), ("flows_actual_specials_rmse", f("A", lv))]]
    (ROOT / "docs" / "data" / "backtest.json").write_text(json.dumps(site, indent=1) + "\n")
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "backtest_flows.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in results.items() if k != "rows"}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
