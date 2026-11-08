"""Turn simulation output into scenario probabilities and the dashboard's datasets."""
from __future__ import annotations

from collections import Counter

import numpy as np

from .allocation import INDEX, PARTIES, PARTY_NAMES

SCENARIOS = ["alone", "nat_needs_opp", "labour"]


def pc(m) -> float:
    return round(float(np.mean(m)) * 100, 1)


def lr(counts, total: float = 100.0, dp: int = 1) -> list[float]:
    """Round shares of `counts` so they sum exactly to `total` (largest-remainder method).

    Each share is rounded down to `dp` places, then the units left over go to the
    shares with the largest remainders. Used wherever a set of percentages is
    shown together, so it adds to 100 (or to its parent's figure).
    """
    counts = np.asarray(counts, float)
    tot = counts.sum()
    if tot <= 0:
        return [0.0] * len(counts)
    unit = 10 ** dp
    exact = counts / tot * total * unit
    floor = np.floor(exact + 1e-9)
    left = int(round(total * unit - floor.sum()))
    order = np.argsort(-(exact - floor), kind="stable")
    floor[order[:left]] += 1
    return [round(float(v) / unit, dp) for v in floor]


def split(scen) -> dict:
    """Scenario shares of a set of runs, summing to exactly 100.0, plus Opportunity pivotal."""
    scen = np.asarray(scen)
    if scen.size == 0:
        return {**{k: 0.0 for k in SCENARIOS}, "opp_pivotal": 0.0}
    out = dict(zip(SCENARIOS, lr([np.sum(scen == k) for k in SCENARIOS])))
    out["opp_pivotal"] = round(out["nat_needs_opp"] + out["labour"], 1)
    return out


def classify(sims: dict) -> dict:
    """Add derived columns: coalition seats, majority, scenario, flips of key seats."""
    S, T = sims["seats"], sims["total"]
    names = list(sims["names"])
    R = S[:, INDEX["NAT"]] + S[:, INDEX["ACT"]] + S[:, INDEX["NZF"]]
    maj = T // 2 + 1
    sc = np.where(R >= maj, "alone", np.where(T - R >= maj, "labour", "nat_needs_opp"))
    flip = lambda n: sims["flip"][:, names.index(n)]
    # National's party-vote entitlement = 120 minus the other qualifying parties' allocations
    # (Te Pāti Māori is assumed to keep an entitlement of 1, as in every run of the central case)
    ent = 120 - (S[:, INDEX["LAB"]] + S[:, INDEX["GP"]] + S[:, INDEX["ACT"]] + S[:, INDEX["NZF"]] + S[:, INDEX["OPP"]] + 1)
    return {**sims, "R": R, "maj": maj, "sc": sc, "flipf": flip, "ent": ent}


def scenario_shares(c: dict) -> dict:
    return split(c["sc"])


def site_datasets(c: dict, variants: dict, sensitivity: dict, he8000: dict, prelim: dict, ctx: dict, enrol: dict, calib: dict) -> dict:
    """All datasets the dashboard reads, keyed by dataset id (rows are lists of dicts)."""
    S, T, R, sc = c["seats"], c["total"], c["R"], c["sc"]
    N = len(T)
    g = c["flipf"]
    w_, h_, mr, ttt = g("Wairarapa"), g("Hamilton East"), g("Mt Roskill"), g("Te Tai Tokerau")
    nzl = S[:, INDEX["NZF"]] == 11
    ed = c["ent"] == 34
    nl = w_.astype(int) + h_.astype(int) - mr.astype(int)
    piv = sc != "alone"
    ds = {}

    shares = scenario_shares(c)
    ds["scenarios"] = [{"scenario": k, "pct": v} for k, v in shares.items()]

    pv = prelim["party_votes"]
    tot = sum(pv.values())
    el = prelim["electorates"]
    n_elec = Counter(v["leader"] for v in el.values())
    prelim_seats = {k: v for k, v in prelim["seats_projected_printed"].items() if k != "total"}
    specials = ctx["specials_estimate"]["value"]
    ds["inputs"] = [{"key": k, "value": v} for k, v in [
        ("specials", specials), ("overseas", ctx["overseas_estimate"]["value"]), ("ordinary", ctx["ordinary_votes"]["value"]),
        ("house", 131), ("majority", 66), ("coalition_prelim", 67), ("left_opp_prelim", 64),
        ("nat_electorates", n_elec["NAT"]), ("nat_entitlement", 35), ("tpm_electorates", n_elec["TPM"]), ("tpm_entitlement", 1), ("overhang", 11),
        ("sims", N), ("k_central", 0.85), ("k_previous", 0.7), ("valid_central", 85), ("valid_previous", 91),
        ("disallowed_est", ctx["disallowed_specials_estimate"]["value"]), ("specials_2023", ctx["specials_counted_2023"]["value"]),
        ("late_enrol_2023", ctx["late_enrolments_2023_voting_period"]["value"]), ("eday_enrol_2023", ctx["election_day_enrolments_2023"]["value"]),
        ("post_writ_2023", ctx["post_writ_enrolments_2023"]["value"]), ("advance_ordinary", ctx["advance_ordinary_votes"]["value"]),
        ("advance_pct_2026", ctx["advance_pct_2026"]["value"]), ("advance_pct_2023", ctx["advance_pct_2023"]["value"]),
        ("special_share_2026", round(specials * 0.85 / (ctx["ordinary_votes"]["value"] + specials * 0.85) * 100, 1)), ("special_share_2023", 19.0),
        ("he_specials_claim", ctx["hamilton_east_specials_claim"]["value"]), ("he_specials_model", he8000["he_model_specials"]),
        ("wai_specials_model", he8000["wai_model_specials"])]]

    rows = []
    for p in ["NAT", "LAB", "GP", "ACT", "NZF", "OPP", "TPM"]:
        col = S[:, INDEX[p]]
        q = [np.percentile(c["share"][:, INDEX[p]], x) * 100 for x in (10, 50, 90)]
        pre = prelim.get("party_pct_printed", {}).get(p, round(pv[p] / tot * 100, 2))
        rows.append({"party": PARTY_NAMES[p], "votes": pv[p], "prelim_pct": pre, "electorates": n_elec.get(p, 0), "prelim_seats": prelim_seats[p],
                     "final_pct_p10": round(q[0], 2), "final_pct_median": round(q[1], 2), "final_pct_p90": round(q[2], 2),
                     "share_change": round(q[1] - pre, 2), "mean_seats": round(float(col.mean()), 2),
                     "p_up": pc(col > prelim_seats[p]), "p_down": pc(col < prelim_seats[p])})
    ds["parties"] = rows
    ds["compare_2023"] = [{"party": n, "prelim_2023": a, "final_2023": b, "change_2023": round(b - a, 2)} for n, a, b in ctx["party_shares_2023"]["rows"]]

    cnt = Counter(zip(T.tolist(), R.tolist(), sc.tolist()))
    cells = sorted(cnt.items())
    ds["outcomes"] = [{"house": t, "coalition": r, "scenario": s, "pct": p}
                      for ((t, r, s), _), p in zip(cells, lr([v for _, v in cells])) if p > 0]

    ks = [("Wairarapa", "National", "Labour", "Labour", "Coalition loses a seat; House shrinks by one"),
          ("Hamilton East", "National", "Labour", "Labour", "Coalition loses a seat; House shrinks by one"),
          ("Te Tai Tokerau", "Te Pāti Māori", "Green", "Green", "Te Pāti Māori loses an overhang seat; House shrinks by one"),
          ("Mt Roskill", "Labour", "National", "National", "Coalition gains a seat; House grows by one"),
          ("Wellington Bays", "Labour", "Green", "Green", "No change: both parties' seats come from the list")]
    ds["key_seats"] = [{"seat": s, "leader": l, "runner_up": ru, "margin": el[s]["margin"], "flips_to": f, "flip_pct": pc(g(s)),
                        "flip_pct_he8000": pc(he8000["c"]["flipf"](s)), "effect": e} for s, l, ru, f, e in ks]

    grid, masks = [], []
    for o, (sid, lab, m0) in enumerate([("hold", "National holds both", ~w_ & ~h_), ("wai", "Labour takes Wairarapa only", w_ & ~h_),
                                        ("he", "Labour takes Hamilton East only", ~w_ & h_), ("both", "Labour takes both", w_ & h_)]):
        for z in [12, 11]:
            m = m0 & (S[:, INDEX["NZF"]] == z)
            masks.append(m)
            g3 = split(sc[m])
            grid.append({"id": f"{sid}_{z}", "seats": lab, "seat_order": o, "nzf": f"NZ First {'keeps 12' if z == 12 else 'drops to 11'}",
                         "nzf_seats": z, "p_runs": None, **{k: g3[k] for k in SCENARIOS}})
    for row, p in zip(grid, lr([m.sum() for m in masks])):
        row["p_runs"] = p
    ds["grid"] = grid

    ds["switches"] = [{"id": i, "switch": t, "coalition_change": cc, "house_change": hc, "p": pc(m)} for i, t, cc, hc, m in [
        ("wai", "Labour takes Wairarapa", -1, -1, w_), ("he", "Labour takes Hamilton East", -1, -1, h_), ("mr", "National takes Mt Roskill", 1, 1, mr),
        ("nzf", "NZ First drops to 11 seats", -1, 0, nzl), ("natent", "National's party-vote entitlement falls from 35 to 34", 0, 1, ed),
        ("ttt", "Greens take Te Tai Tokerau", 0, -1, ttt)]]

    paths = [
        ("alone", "a1", "Holds both, NZ First drops", (nl == 0) & nzl & ~ttt & ~ed),
        ("alone", "a2", "Holds both, NZ First keeps 12", (nl == 0) & ~nzl),
        ("alone", "a3", "Holds both, NZ First drops, Greens take Te Tai Tokerau", (nl == 0) & nzl & ttt & ~ed),
        ("alone", "a4", "Loses one, NZ First keeps 12", (nl == 1) & ~nzl),
        ("alone", "a5", "Loses one, NZ First drops, Greens take Te Tai Tokerau", (nl == 1) & nzl & ttt & ~ed),
        ("alone", "a6", "National gains Mt Roskill", nl < 0),
        ("alone", "a7", "Holds both, NZ First drops, Te Tai Tokerau and entitlement drop cancel", (nl == 0) & nzl & ttt & ed),
        ("labour", "l1", "Loses one, NZ First drops, entitlement drops", (nl == 1) & nzl & ed),
        ("labour", "l2", "Loses both, NZ First drops", (nl == 2) & nzl),
        ("nat_needs_opp", "n1", "Loses one, NZ First drops, no entitlement drop", (nl == 1) & nzl & ~ttt & ~ed),
        ("nat_needs_opp", "n2", "Holds both, NZ First drops, entitlement drops", (nl == 0) & nzl & ~ttt & ed),
        ("nat_needs_opp", "n3", "Loses one, NZ First drops, Te Tai Tokerau and entitlement drop", (nl == 1) & nzl & ttt & ed),
        ("nat_needs_opp", "n4", "Loses both, NZ First keeps 12", (nl == 2) & ~nzl)]
    # Paths within each scenario are rounded to add up to that scenario's headline share.
    by_s = {k: [] for k in SCENARIOS}
    cov = {k: np.zeros(N, bool) for k in SCENARIOS}
    for s, i, lab, m in paths:
        mm = m & (sc == s) & ~cov[s]
        cov[s] |= mm
        if mm.any():
            by_s[s].append(({"id": i, "scenario": s, "path": lab, "coalition": int(np.median(R[mm])), "house": int(np.median(T[mm]))}, mm.sum()))
    for s in SCENARIOS:
        rest = (sc == s) & ~cov[s]
        if rest.any():
            by_s[s].append(({"id": f"{s}_other", "scenario": s, "path": "Other small combinations", "coalition": None, "house": None}, rest.sum()))
    prow = []
    for s in SCENARIOS:
        items = by_s[s]
        for (row, _), p in zip(items, lr([n for _, n in items], total=shares[s])):
            if p > 0:
                prow.append({**row, "pct": p})
    ds["paths"] = prow

    nat = c["share"][:, INDEX["NAT"]] * 100
    bands = [("Below 28.4%", nat < 28.4), ("28.4-28.6%", (nat >= 28.4) & (nat < 28.6)), ("28.6-28.8%", (nat >= 28.6) & (nat < 28.8)), ("28.8% or higher", nat >= 28.8)]
    band_p = lr([m.sum() for _, m in bands])
    ds["opp_by_nat"] = [{"band": b, "order": i, "p_runs": band_p[i], "opp_pivotal": pc(piv[m]) if m.any() else None, "ent_drop": pc(ed[m]) if m.any() else None}
                        for i, (b, m) in enumerate(bands)]
    ds["opp_stats"] = [{"key": k, "value": v} for k, v in [
        ("pivotal", shares["opp_pivotal"]), ("piv_with_nzf11", pc(nzl[piv])), ("piv_with_lab_marginal", pc((w_ | h_)[piv])), ("piv_with_entdrop", pc(ed[piv])),
        ("piv_given_nzf12", pc(piv[~nzl])), ("piv_given_nzf11_and_marginal", pc(piv[nzl & (w_ | h_)])),
        ("nzf_lose_hold_both", pc(nzl[nl == 0])), ("nzf_lose_lose_both", pc(nzl[nl == 2])), ("lab_takes_one_or_more", pc(w_ | h_)),
        ("ent_drop", pc(ed)), ("ent_given_hold", pc(ed[nl == 0])), ("ent_given_lose1", pc(ed[nl == 1])), ("ent_given_lose2", pc(ed[nl == 2])),
        ("corr", round(float(np.corrcoef(nl, nzl)[0, 1]), 2)), ("hold_both", pc(~w_ & ~h_)), ("lose_both", pc(w_ & h_)),
        ("wai", pc(w_)), ("he", pc(h_)), ("nzf11", pc(nzl))]]

    weights = {"2014": 15, "2017": 25, "2020": 25, "2023": 35}
    ds["template_years"] = [{"year": int(y), "weight": weights[y], **split(sc[c["year"] == y])}
                            for y in ["2014", "2017", "2020", "2023"]]

    ds["variants"] = [{"id": vid, "variant": v["label"], "order": i + 1, **split(v["c"]["sc"]), "wai": pc(v["c"]["flipf"]("Wairarapa")), "he": pc(v["c"]["flipf"]("Hamilton East")),
                       "nzf11": pc(v["c"]["seats"][:, INDEX["NZF"]] == 11)} for i, (vid, v) in enumerate(variants.items())]
    ds["sensitivity"] = [{"k": k, **{s: x for s, x in split(v["sc"]).items() if s in SCENARIOS}} for k, v in sensitivity.items()]

    ds["enrolment"] = enrol["series"]
    oct_ = round(enrol["eligible_18_24"] * enrol["series"][-1]["rate_18_24"] / 100)
    ds["enrol_stats"] = [{"key": k, "value": v} for k, v in [
        ("eligible_18_24", enrol["eligible_18_24"]), ("enrolled_18_24_sep", enrol["enrolled_18_24_30sep"]), ("enrolled_18_24_oct", oct_),
        ("youth_gain", oct_ - enrol["enrolled_18_24_30sep"]), ("total_gain", enrol["series"][-1]["total_electors"] - enrol["total_enrolled_30sep"]),
        ("youth_share_of_gain", round((oct_ - enrol["enrolled_18_24_30sep"]) / (enrol["series"][-1]["total_electors"] - enrol["total_enrolled_30sep"]) * 100, 1))]]

    hist = calib["party_votes_by_special_category"]
    hp = []
    for y in sorted(hist):
        h = hist[y]
        sp = {p: sum(h[k].get(p, 0) for k in ["SP_before", "SP_on", "SP_overseas"]) for p in PARTIES}
        o = {p: h["TOTAL"].get(p, 0) - sp[p] for p in PARTIES}
        Ssum, Osum = sum(sp.values()), sum(o.values())
        row = {"year": int(y), "special_share": round(Ssum / (Ssum + Osum) * 100, 1)}
        for p in ["NAT", "LAB", "GP", "ACT", "NZF", "OPP", "TPM"]:
            row[p] = round((sp[p] / Ssum - o[p] / Osum) * 100, 2) if h["TOTAL"].get(p) else None
        hp.append(row)
    ds["history_party"] = hp
    ds["history_seats"] = calib.get("marginal_history", [])
    return ds
