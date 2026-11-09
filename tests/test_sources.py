"""Parser tests against real Electoral Commission files (trimmed to their summary rows)."""
from pathlib import Path

from nzspecials.ge2026 import parse_electorate_status, parse_overall
from nzspecials.sources import parse_candidate_file, parse_party_file, swing_lab_minus, top_two

FIX = Path(__file__).parent / "fixtures"


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_candidate_2023_format():
    p = parse_candidate_file(read("2023_cand_58.csv"))
    assert p["electorate"] == "Wairarapa"
    assert p["special_valid"] == 708 + 2520 + 2302
    t = top_two(p)
    assert (t["a"], t["b"]) == ("NAT", "LAB")
    assert (t["sa"], t["sb"]) == (2281, 1965)          # Butterick, McAnulty specials
    assert t["O"] == 44050 - 5530
    assert t["oa"] - t["ob"] == 2500                   # ordinary-vote margin
    assert round(swing_lab_minus(t, "NAT"), 2) == round(((1965 - 2281) / 5530 + 2500 / 38520) * 100, 2)


def test_candidate_2014_format():
    p = parse_candidate_file(read("2014_cand_58.csv"))
    t = top_two(p)
    assert (t["a"], t["b"]) == ("NAT", "LAB")
    assert (t["sa"], t["sb"]) == (1314, 753)
    assert t["S"] == 3055 and t["O"] == 33903


def test_party_2023_includes_party_only_overseas_row():
    p = parse_party_file(read("2023_party_58.csv"))
    assert p["SP_overseas"]["NAT"] == 256
    assert p["SP_overseas"]["LAB"] == 1 + 143
    assert p["SP_before"]["NAT"] == 910 and p["SP_on"]["LAB"] == 600
    assert p["TOTAL"]["NAT"] == 17397
    assert p["TOTAL"]["OPP"] == 708 and p["TOTAL"]["TPM"] == 455


def test_party_2014_format_ignores_ordinary_rows():
    p = parse_party_file(read("2014_party_58.csv"))
    assert set(p) == {"SP_before", "SP_on", "SP_overseas", "TOTAL"}
    assert p["SP_before"]["NAT"] == 478 and p["SP_on"]["NAT"] == 815 and p["SP_overseas"]["NAT"] == 243
    assert p["TOTAL"]["TPM"] == 209


def test_ge2026_pages():
    s = parse_electorate_status(read("ge2026_electorate_status_sample.html"))
    assert s["Wairarapa"] == {"leader": "NAT", "runner_up": "LAB", "margin": 139, "details": "electorate-details-55.html"}
    assert s["Te Tai Tokerau"]["leader"] == "TPM" and s["Te Tai Tokerau"]["runner_up"] == "GP"
    o = parse_overall(read("ge2026_overall_sample.html"))
    assert o["National Party"] == 706680 and o["Total"] == 2418565


def test_calibration_build_runs_on_fixture(tmp_path):
    """Build calibration from a one-seat raw tree laid out like data/raw/history/."""
    import shutil
    from nzspecials import calibration
    for y in ("2014", "2023"):
        for kind, short in (("candidate", "cand"), ("party", "party")):
            d = tmp_path / y / kind
            d.mkdir(parents=True)
            shutil.copy(FIX / f"{y}_{short}_58.csv", d / "58.csv")
    try:
        out = calibration.build(tmp_path)
    finally:
        calibration.RAW = calibration.Path(calibration.__file__).resolve().parent.parent / "data" / "raw" / "history"
    assert out["party_votes_by_special_category"]["2023"]["TOTAL"]["NAT"] > 0
    assert "Wairarapa" in out["special_to_ordinary_ratio_2023"]
    assert out["marginal_history"][0]["seat"] == "Wairarapa"


def test_polling_place_named_special_is_not_a_special_vote():
    """Mt Roskill's 'Sunnydene Special School' polling place must count as ordinary votes."""
    from nzspecials.sources import category, is_special_row
    assert not is_special_row("Sunnydene Special School, 48 Smallfield Avenue")
    assert category("Sunnydene Special School, 48 Smallfield Avenue", "") is None
    assert category("Special Votes BEFORE polling day", "") == "SP_before"
    assert category("Special Votes ON Polling Day - Mt Roskill", "") == "SP_on"
    assert category("Overseas Special Votes Including Defence Force - Mt Roskill", "") == "SP_overseas"
    assert category("Overseas Votes Allowed for Party Only - Wigram", "") == "SP_overseas"
    for place in ("Special Needs Library, 109 Huxley Street", "Wairau Valley Special School, 102 Hillside Road",
                  "Overseas Terminal, 1 Herd Street (off Oriental Parade)"):
        assert category(place, "") is None, place
    text = read("2014_cand_58.csv")
    lines = text.splitlines()
    i = next(k for k, l in enumerate(lines) if "Special Votes BEFORE" in l)
    cols = lines[i].split(",")
    fake = ",\"Sunnydene Special School, 48 Smallfield Avenue\"," + ",".join(["100"] * (len(cols) - 2))
    p0 = parse_candidate_file(text)
    p1 = parse_candidate_file("\n".join(lines[:i] + [fake] + lines[i:]))
    assert p1["special_valid"] == p0["special_valid"]
    assert [c["special"] for c in p1["candidates"]] == [c["special"] for c in p0["candidates"]]


def test_split_vote_parser_hamilton_east_2023():
    """2023 Hamilton East split votes (no Green candidate): matches the browser extraction used for flows_2023.json."""
    from nzspecials.splitvotes import last_paren, parse
    assert last_paren("CORKIN, Alexander James (The Opportunities Party (TOP))") == "The Opportunities Party (TOP)"
    assert last_paren("HOWARD, Thomas Edward (Ted) (Independent)") == "Independent"
    name, cols, M = parse(read("2023_split_12.csv"))
    assert name == "Hamilton East"
    assert cols == ["ACT", "OTH", "LAB", "NAT", "NZF", "TPM", "OPP", "INF", "PVO"]
    assert M["GP"] == [40, 149, 3292, 233, 48, 468, 345, 55, 88]
    assert M["NAT"] == [632, 87, 449, 14448, 142, 57, 141, 190, 228]


def test_flow_fit_recovers_known_weights():
    """The Luce fit recovers the weights that generated synthetic seats with different candidate line-ups."""
    from nzspecials.splitvotes import fit
    true = {"NAT": 40.0, "LAB": 2.0, "GP": 1.0, "ACT": 4.0}
    seats = []
    for line_up in (["NAT", "LAB", "GP", "ACT"], ["NAT", "LAB"], ["LAB", "GP", "ACT"], ["NAT", "GP"]):
        tot = sum(true[c] for c in line_up) + 1.0
        row = [round(100000 * true[c] / tot) for c in line_up] + [round(100000 / tot)]
        seats.append((line_up + ["INF"], {"NAT": row}))
    W = fit(seats, iters=3000)["NAT"]
    for c, v in true.items():
        assert abs(W[c] - v) / v < 0.01, (c, W[c])


def test_ge2026_candidate_table():
    from nzspecials.ge2026 import parse_candidates
    c, p = parse_candidates(read("ge2026_candidates_sample.html"))
    assert c == [("BOONEN, Roy Peter", "Green Party", 1643), ("HEDLEY, Alex", "Labour Party", 11952), ("LAWRENCE, Te Kira", "New Zealand First Party", 1975)]
    assert p == {"Green Party": 3091, "Labour Party": 9355, "New Zealand First Party": 3785}
