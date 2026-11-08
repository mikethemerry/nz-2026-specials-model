"""Seat allocation and simulation tests."""
import json
from pathlib import Path

import numpy as np

from nzspecials.allocation import INDEX, PARTIES, sainte_lague, seats_from
from nzspecials.data import load_prelim
from nzspecials.model import Config, simulate

ROOT = Path(__file__).resolve().parent.parent


def prelim_inputs():
    p = load_prelim()
    pv = np.array([p["party_votes"][k] for k in PARTIES], float)
    wins = np.zeros(len(PARTIES), int)
    for e in p["electorates"].values():
        wins[INDEX[e["leader"]]] += 1
    return p, pv, wins


def test_sainte_lague_simple():
    # Textbook example: 3 seats, votes 100/80/30 -> 2/1/0 (quotients 100, 80, 33.3)
    assert list(sainte_lague([100, 80, 30], 3)) == [2, 1, 0]


def test_preliminary_count_reproduces_commission_projection():
    """The preliminary result must give the Commission's projected 131-seat House."""
    p, pv, wins = prelim_inputs()
    seats = seats_from(pv, wins)
    printed = p["seats_projected_printed"]
    for k in PARTIES:
        if k in printed:
            assert seats[INDEX[k]] == printed[k], k
    assert seats.sum() == printed["total"] == 131


def test_electorate_count():
    p, _, wins = prelim_inputs()
    assert wins.sum() == 71 == len(p["electorates"])
    assert wins[INDEX["NAT"]] == 42


def test_small_simulation_is_deterministic_and_sane():
    a = simulate(Config(n=300, seed=1))
    b = simulate(Config(n=300, seed=1))
    assert np.array_equal(a["seats"], b["seats"])
    total = a["seats"].sum(axis=1)
    assert np.array_equal(total, a["total"])
    assert ((total >= 126) & (total <= 134)).all()
    # every run gives National/ACT/NZ First between 60 and 70 seats
    gov = a["seats"][:, [INDEX["NAT"], INDEX["ACT"], INDEX["NZF"]]].sum(axis=1)
    assert ((gov >= 60) & (gov <= 70)).all()


def test_coalition_rule_matches_simulation():
    """Coalition seats = 67 - net National electorates lost - 1 if NZ First drops to 11.

    This is the rule the dashboard uses to explain the outcomes (ACT almost never moves).
    """
    s = simulate(Config(n=2000, seed=7))
    el = load_prelim()["electorates"]
    flip = s["flip"]
    lost = np.array([el[n]["leader"] == "NAT" for n in s["names"]])
    gained = np.array([el[n]["runner_up"] == "NAT" for n in s["names"]])
    net_lost = flip[:, lost].sum(axis=1) - flip[:, gained].sum(axis=1)
    gov = s["seats"][:, [INDEX["NAT"], INDEX["ACT"], INDEX["NZF"]]].sum(axis=1)
    nzf11 = s["seats"][:, INDEX["NZF"]] == 11
    assert np.mean(gov == 67 - net_lost - nzf11) > 0.995


def test_central_run_reproduces_published_headline():
    """A full 20,000-run central simulation must give exactly the published figures."""
    from nzspecials.analysis import classify, scenario_shares
    cfg = json.loads((ROOT / "configs" / "central.json").read_text())
    got = scenario_shares(classify(simulate(Config.from_dict(cfg))))
    published = json.loads((ROOT / "outputs" / "summary.json").read_text())["central"]
    for k in ("alone", "nat_needs_opp", "labour", "opp_pivotal"):
        assert got[k] == published[k], k


def test_largest_remainder_rounding_sums_exactly():
    from nzspecials.analysis import lr, split
    assert lr([526, 175, 299]) == [52.6, 17.5, 29.9]
    assert round(sum(lr([1, 1, 1])), 1) == 100.0 and lr([1, 1, 1]) == [33.4, 33.3, 33.3]
    assert lr([5, 0, 0]) == [100.0, 0.0, 0.0]
    assert round(sum(lr([7, 3, 1], total=47.4)), 1) == 47.4
    s = split(np.array(["alone"] * 2 + ["labour"] * 1))
    assert s["opp_pivotal"] == round(s["nat_needs_opp"] + s["labour"], 1)


def test_site_percentage_groups_add_to_100():
    """Every set of shares the site shows together must sum to exactly 100.0."""
    D = lambda f: json.loads((ROOT / "docs" / "data" / f"{f}.json").read_text())
    k3 = ["alone", "nat_needs_opp", "labour"]
    sc = {r["scenario"]: r["pct"] for r in D("scenarios")}
    assert round(sum(sc[k] for k in k3), 1) == 100.0
    assert sc["opp_pivotal"] == round(sc["nat_needs_opp"] + sc["labour"], 1)
    for f in ("grid", "template_years", "variants", "sensitivity"):
        for r in D(f):
            assert round(sum(r[k] for k in k3), 1) == 100.0, (f, r)
    for f, key in (("grid", "p_runs"), ("opp_by_nat", "p_runs"), ("outcomes", "pct"), ("paths", "pct")):
        assert round(sum(r[key] for r in D(f)), 1) == 100.0, f
    for k in k3:
        assert round(sum(r["pct"] for r in D("paths") if r["scenario"] == k), 1) == sc[k]
