"""Monte Carlo simulation of the 2026 special-vote count.

Each run (one "draw"):

1. Picks a template year (2014/2017/2020/2023 by default) whose pattern of
   special votes vs ordinary votes is applied to 2026.
2. Draws how strongly 2026's domestic specials lean compared with that year
   (``k``) and how strongly overseas specials do (``ko``), and how many
   specials are valid.
3. Turns those into party special-vote shares and adds them to the
   preliminary party vote.
4. For every electorate, draws its number of specials and the swing in the
   two-candidate margin on specials, and decides the winner.
5. Allocates seats (Sainte-Laguë, threshold, overhang).

All of a run's party-vote and electorate outcomes come from the same draw, so
correlated events (e.g. National losing marginals *and* its party-vote
entitlement) combine as they would on the night.

The random-number order is part of the published results: changing the order
of draws changes individual runs (but not the statistics, beyond noise).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .allocation import INDEX, PARTIES, seats_from
from .data import load_calibration, load_prelim

CATEGORIES = ["SP_before", "SP_on", "SP_overseas"]


@dataclass
class Config:
    """Model settings. Defaults are the revised central case."""
    n: int = 20000
    seed: int = 2026
    years: list = field(default_factory=lambda: ["2014", "2017", "2020", "2023"])
    weights: list = field(default_factory=lambda: [0.15, 0.25, 0.25, 0.35])
    k_mean: float = 0.85          # domestic special-vote lean as a share of the template year's
    k_sd: float = 0.20
    k_by_year: dict = field(default_factory=dict)   # optional per-template override of k_mean
    ko_mean: float = 1.0          # overseas lean as a share of the template year's
    ko_sd: float = 0.15
    valid: float = 0.85           # share of the special-vote estimate that will count
    valid_sd: float = 0.02
    specials_sd: float = 0.05     # uncertainty in the Commission's special-vote estimate
    party_noise: float = 0.04     # extra noise on each party's special/ordinary ratio (log scale)
    seat_specials_noise: float = 0.12
    seat_lean_shrink: float = 0.75
    labnat_noise: float = 0.035
    labtpm_noise: float = 0.045
    tpmgp_noise: float = 0.06
    other_pair_mult: float = 1.5
    other_pair_noise: float = 0.05
    seat_lean_2008: bool = False  # use 2008-2023 seat lean for Wairarapa, Hamilton East, Mt Roskill
    se_override: dict = field(default_factory=dict)  # e.g. {"Hamilton East": 8000} specials cast

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        return cls(**{k: v for k, v in d.items() if not k.startswith("_")})


def party_ratios(hist_year: dict) -> dict:
    """Per party: (domestic special share / ordinary share, overseas special share / ordinary share)."""
    tot = {p: hist_year["TOTAL"].get(p, 0) for p in PARTIES}
    sp = {c: {p: hist_year[c].get(p, 0) for p in PARTIES} for c in CATEGORIES}
    ordv = {p: tot[p] - sum(sp[c][p] for c in CATEGORIES) for p in PARTIES}
    O = sum(ordv.values())
    dom = {p: sp["SP_before"][p] + sp["SP_on"][p] for p in PARTIES}
    D = sum(dom.values())
    ov = sp["SP_overseas"]
    V = sum(ov.values())
    out = {}
    for p in PARTIES:
        if ordv[p] <= 0:  # party absent that year (Opportunity before 2017)
            out[p] = (1.15, 1.4)
            continue
        o = ordv[p] / O
        out[p] = (dom[p] / D / o, ov[p] / V / o)
    return out


def simulate(cfg: Config | None = None, prelim: dict | None = None, calib: dict | None = None) -> dict:
    """Run the simulation. Returns arrays, one row per run."""
    cfg = cfg or Config()
    prelim = prelim or load_prelim()
    calib = calib or load_calibration()
    rng = np.random.default_rng(cfg.seed)

    hist = calib["party_votes_by_special_category"]
    labnat = calib["mean_seat_swing_lab_minus_nat_pp"]
    labtpm = calib["mean_seat_swing_lab_minus_tpm_pp"]
    ratio23 = calib["special_to_ordinary_ratio_2023"]
    lean = dict(calib["seat_lean_2017_2023_pp"])
    if cfg.seat_lean_2008:
        lean.update(calib["seat_lean_2008_2023_pp"])
    pred_map = calib["predecessor_seats"]

    years = list(cfg.years)
    yw = np.array(cfg.weights, float)
    yw /= yw.sum()
    rat = {y: party_ratios(hist[y]) for y in years}

    specials_est = prelim["specials_estimate"]
    f_os = prelim["overseas_estimate"] / specials_est
    pv = np.array([prelim["party_votes"][p] for p in PARTIES], float)
    pre_sh = pv / pv.sum()

    names = list(prelim["electorates"])
    el = prelim["electorates"]
    lead = [el[n]["leader"] for n in names]
    runr = [el[n]["runner_up"] for n in names]
    marg = np.array([el[n]["margin"] for n in names], float)
    Oe = np.array([el[n]["votes_counted"] for n in names], float)
    pred = [pred_map.get(n, n) for n in names]
    r23 = np.array([ratio23.get(p, np.nan) for p in pred])
    r23 = np.where(np.isnan(r23), np.nanmedian(r23), r23)
    fe = np.array([lean.get(p, 0.0) for p in pred]) / 100

    n_seats = len(names)
    seats = np.zeros((cfg.n, len(PARTIES)), int)
    share = np.zeros((cfg.n, len(PARTIES)))
    flips = np.zeros((cfg.n, n_seats), bool)
    year = np.empty(cfg.n, dtype="<U4")
    kk = np.zeros(cfg.n)

    for it in range(cfg.n):
        y = years[rng.choice(len(years), p=yw)]
        k = float(np.clip(rng.normal(cfg.k_by_year.get(y, cfg.k_mean), cfg.k_sd), 0.2, 1.2))
        ko = float(np.clip(rng.normal(cfg.ko_mean, cfg.ko_sd), 0.5, 1.5))
        valid = rng.normal(cfg.valid, cfg.valid_sd) * specials_est * rng.normal(1, cfg.specials_sd)

        # party vote
        rr = np.array([(1 - f_os) * (1 + k * (rat[y][p][0] - 1)) + f_os * (1 + ko * (rat[y][p][1] - 1)) for p in PARTIES])
        rr *= np.exp(rng.normal(0, cfg.party_noise, len(PARTIES)))
        sp_sh = pre_sh * rr
        sp_sh /= sp_sh.sum()
        final = pv + valid * sp_sh
        dlean = sp_sh - pre_sh

        # specials per electorate
        Se = Oe * r23 * np.exp(rng.normal(0, cfg.seat_specials_noise, n_seats))
        Se *= valid * rng.normal(0.97, 0.02) / Se.sum()
        for seat, cast in cfg.se_override.items():
            Se[names.index(seat)] = cast * rng.normal(cfg.valid, cfg.valid_sd)
        scale = (1 - f_os) * k + f_os * ko
        mu_ln = labnat[y] / 100 * scale
        mu_lt = labtpm[y] / 100 * scale

        wins = np.zeros(len(PARTIES), int)
        for j in range(n_seats):
            A, B = lead[j], runr[j]
            mo = marg[j] / Oe[j]
            pair = {A, B}
            if pair == {"LAB", "NAT"}:
                d_lab = mu_ln + cfg.seat_lean_shrink * fe[j] + rng.normal(0, cfg.labnat_noise)
                d = d_lab if A == "LAB" else -d_lab
            elif pair == {"LAB", "TPM"}:
                d_lab = mu_lt + rng.normal(0, cfg.labtpm_noise)
                d = d_lab if A == "LAB" else -d_lab
            elif pair == {"TPM", "GP"}:
                # Te Pāti Māori v Green = (TPM v Labour swing) + (Labour v Green party lean)
                sw_tpm = -mu_lt + cfg.other_pair_mult * (dlean[INDEX["LAB"]] - dlean[INDEX["GP"]]) + rng.normal(0, cfg.tpmgp_noise)
                d = sw_tpm if A == "TPM" else -sw_tpm
            else:
                d = cfg.other_pair_mult * (dlean[INDEX[A]] - dlean[INDEX[B]]) + rng.normal(0, cfg.other_pair_noise)
            final_margin = marg[j] + (mo + d) * Se[j]
            winner = A if final_margin > 0 else B
            flips[it, j] = winner != A
            wins[INDEX[winner]] += 1

        seats[it] = seats_from(final, wins)
        share[it] = final / final.sum()
        year[it] = y
        kk[it] = k

    return {"seats": seats, "total": seats.sum(1), "share": share, "flip": flips,
            "year": year, "k": kk, "names": np.array(names)}
