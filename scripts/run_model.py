#!/usr/bin/env python3
"""Run every configuration in configs/, write results and the dashboard's datasets.

    python scripts/run_model.py            # all configs, writes outputs/ and docs/data/
    python scripts/run_model.py central    # just one config (prints scenario shares)
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nzspecials.analysis import classify, scenario_shares, site_datasets  # noqa: E402
from nzspecials.data import load_calibration, load_json, load_prelim  # noqa: E402
from nzspecials.model import Config, simulate  # noqa: E402

CONFIGS = ROOT / "configs"
OUT = ROOT / "outputs"
SITE_DATA = ROOT / "docs" / "data"
VARIANT_ORDER = ["prev", "k085_v91", "central", "he8000", "k07_he", "k10_he", "hist0823", "fe6"]
SENSITIVITY = {0.55: "k055", 0.7: "k07", 0.85: "central", 1.0: "k10"}


def load_config(name: str) -> dict:
    return json.loads((CONFIGS / f"{name}.json").read_text())


def run_one(name: str) -> str:
    d = load_config(name)
    sims = simulate(Config.from_dict(d))
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "runs" / f"{name}.npz", **sims)
    return name


def load_run(name: str) -> dict:
    z = np.load(OUT / "runs" / f"{name}.npz", allow_pickle=False)
    return {k: z[k] for k in z.files}


def expected_specials(seat: str, valid: float) -> int:
    """Model's expected specials in a seat before noise (2023 ratio, scaled to the 2026 total)."""
    prelim, calib = load_prelim(), load_calibration()
    names = list(prelim["electorates"])
    pred = [calib["predecessor_seats"].get(n, n) for n in names]
    r = np.array([calib["special_to_ordinary_ratio_2023"].get(p, np.nan) for p in pred])
    r = np.where(np.isnan(r), np.nanmedian(r), r)
    se = np.array([prelim["electorates"][n]["votes_counted"] for n in names]) * r
    se *= prelim["specials_estimate"] * valid * 0.97 / se.sum()
    return int(round(se[names.index(seat)]))


def main(argv):
    names = argv or sorted(p.stem for p in CONFIGS.glob("*.json"))
    with ProcessPoolExecutor() as ex:
        for n in ex.map(run_one, names):
            print("ran", n, flush=True)
    summary = {}
    for n in sorted(p.stem for p in CONFIGS.glob("*.json")):
        if (OUT / "runs" / f"{n}.npz").exists():
            summary[n] = {"label": load_config(n).get("_label"), **scenario_shares(classify(load_run(n)))}
    OUT.mkdir(exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    for n, s in summary.items():
        print(f"{n:10} alone {s['alone']:5} needs-Opp {s['nat_needs_opp']:5} labour {s['labour']:5} | {s['label']}")
    if argv:
        return
    c = classify(load_run("central"))
    variants = {v: {"label": load_config(v)["_label"], "c": classify(load_run(v))} for v in VARIANT_ORDER}
    sens = {k: classify(load_run(v)) for k, v in SENSITIVITY.items()}
    he = {"c": classify(load_run("he8000")), "he_model_specials": expected_specials("Hamilton East", 0.85),
          "wai_model_specials": expected_specials("Wairarapa", 0.85)}
    ds = site_datasets(c, variants, sens, he, load_prelim(), load_json("context_2026.json"), load_json("enrolment_2026.json"), load_calibration())
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    for k, rows in ds.items():
        (SITE_DATA / f"{k}.json").write_text(json.dumps(rows, ensure_ascii=False))
    (SITE_DATA / "assumptions.json").write_text((ROOT / "data" / "inputs" / "assumptions.json").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {len(ds) + 1} datasets to {SITE_DATA.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
