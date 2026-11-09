"""Candidate-level electorate votes: party vote -> electorate candidate flows.

Each electorate is modelled with the candidates actually standing in it.

1. **Flow weights.** For voters of each party, every type of candidate has a
   weight (``data/inputs/flows_2023.json``, estimated from the 2023 split-vote
   statistics). In a given seat, the probability that a party's voter backs
   candidate *j* is ``m_j * w[party][type_j] / sum_k m_k * w[party][type_k]``,
   summed over the candidates standing there, plus an "ABS" option (informal
   or party vote only). A party with no candidate in the seat simply has its
   voters spread over the candidates who are standing, by those weights.
2. **Seat calibration.** The candidate multipliers ``m_j`` capture personal and
   tactical votes (an incumbent, Epsom, Auckland Central). They are fitted so
   that the flows reproduce the seat's actual ordinary-vote candidate results
   exactly, given its ordinary party votes.
3. **Specials.** The same flows applied to the seat's special *party* votes give
   each candidate's special votes.
"""
from __future__ import annotations

import numpy as np

from .allocation import PARTIES
from .data import load_json

TYPES = ["NAT", "LAB", "GP", "ACT", "NZF", "OPP", "TPM", "OTH", "IND"]
MAORI_SEATS = {"Hauraki-Waikato", "Ikaroa-Rāwhiti", "Tāmaki Makaurau", "Te Tai Hauāuru",
               "Te Tai Tokerau", "Te Tai Tonga", "Waiariki"}


def load_weights() -> dict:
    return load_json("flows_2023.json")


def candidate_type(party_code: str, party_name: str = "") -> str:
    """Candidate type for the flow weights. Independents are kept apart from minor parties."""
    if party_code in TYPES and party_code != "OTH":
        return party_code
    n = (party_name or "").strip().lower()
    if n in ("", "independent"):
        return "IND"
    return "OTH"


def base_matrix(types: list[str], maori: bool, W: dict) -> np.ndarray:
    """B[p, j]: weight of candidate j for voters of party p; last column is ABS (weight 1)."""
    g, m = W["general"], W["maori"]
    B = np.zeros((len(PARTIES), len(types) + 1))
    for i, p in enumerate(PARTIES):
        for j, t in enumerate(types):
            w = m[p][t] if maori else g[p][t]
            if maori and w == 0:          # type never stood in a Māori seat in 2023
                w = g[p][t]
            B[i, j] = max(w, 1e-6)
        B[i, -1] = 1.0
    return B


def calibrate(B: np.ndarray, party_votes: np.ndarray, cand_votes: np.ndarray, abs_votes: float,
              tol: float = 0.01, max_iter: int = 20000) -> np.ndarray:
    """Candidate multipliers m (ABS fixed at 1) so the flows reproduce each candidate's share.

    Targets are scaled to the party-vote total. Where a seat has more candidate
    votes than party votes, the informal / party-only share is floored at 0.5%.
    """
    total = party_votes.sum()
    a = max(abs_votes, 0.005 * total)
    target = np.append(np.maximum(cand_votes, 0.5) * (total - a) / max(cand_votes.sum(), 1), a)
    m = np.ones(B.shape[1])
    for _ in range(max_iter):
        pred = party_votes @ flows(B, m)
        if np.abs(pred - target).max() < tol:
            break
        m[:-1] *= (target[:-1] / np.maximum(pred[:-1], 1e-12)) ** 1.5   # over-relaxed scaling
    return m


def flows(B: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Row-normalised flow matrix F[p, j] (rows sum to 1, last column ABS)."""
    X = B * m[None, :]
    return X / X.sum(axis=1, keepdims=True)


class Seat:
    """One electorate's candidates, calibrated flows and preliminary candidate votes."""

    def __init__(self, name: str, candidates: list[dict], party_votes: dict, W: dict):
        self.name = name
        self.candidates = candidates
        self.types = [candidate_type(c["party"], c.get("party_name", "")) for c in candidates]
        self.parties = [c["party"] for c in candidates]
        self.votes = np.array([c["votes"] for c in candidates], float)
        pv = np.array([party_votes.get(p, 0) for p in PARTIES], float)
        self.B = base_matrix(self.types, name in MAORI_SEATS, W)
        abs_votes = pv.sum() - self.votes.sum()
        self.m = calibrate(self.B, pv, self.votes, abs_votes)
        self.F = flows(self.B, self.m)
        self.ord_party = pv

    def specials(self, special_party_votes: np.ndarray) -> np.ndarray:
        """Special votes for each candidate (ABS dropped) from special party votes."""
        return (special_party_votes @ self.F)[:-1]


MAJORS = ("NAT", "LAB", "GP", "ACT", "NZF", "OPP")


def field_adjustment(seat: "Seat", ratio: np.ndarray, a: int, b: int) -> tuple[float, list[str]]:
    """Effect of the actual candidate field on the special-vote swing between candidates a and b.

    Swing = special-vote margin rate minus ordinary margin rate (points, a minus b), with the
    seat's special party votes taken as its ordinary party votes x ``ratio`` (the national
    special/ordinary ratio by party). Returned: swing with the candidates actually standing
    minus swing if every major party that won at least 3% of the seat's party vote had a
    candidate (absent ones added at their base weight), and the list of absent parties.
    """
    O = seat.ord_party
    miss = [t for t in MAJORS if t not in seat.types and O[PARTIES.index(t)] > 0.03 * O.sum()]
    if not miss:
        return 0.0, miss
    S = O * ratio

    def swing(F):
        so, ss = (O @ F)[:-1], (S @ F)[:-1]
        return ((ss[a] - ss[b]) / ss.sum() - (so[a] - so[b]) / so.sum()) * 100

    Bc = base_matrix(seat.types + miss, seat.name in MAORI_SEATS, load_weights_cached())
    Fc = flows(Bc, np.concatenate([seat.m[:-1], np.ones(len(miss)), [1.0]]))
    return swing(seat.F) - swing(Fc), miss


_W = None


def load_weights_cached() -> dict:
    global _W
    if _W is None:
        _W = load_weights()
    return _W
