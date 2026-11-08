"""Seat allocation under New Zealand's MMP rules.

* 120 list-and-electorate seats are allocated by the Sainte-Laguë method among
  parties that clear the threshold: at least 5% of the party vote, or at least
  one electorate seat.
* A party that wins more electorates than its entitlement keeps them all
  (overhang); the House grows by the overhang and no other party loses seats.
"""
from __future__ import annotations

import numpy as np

PARTIES = ["NAT", "LAB", "GP", "ACT", "NZF", "OPP", "TPM", "OTH"]
PARTY_NAMES = {
    "NAT": "National", "LAB": "Labour", "GP": "Green", "ACT": "ACT",
    "NZF": "NZ First", "OPP": "Opportunity", "TPM": "Te Pāti Māori", "OTH": "Other",
}
INDEX = {p: i for i, p in enumerate(PARTIES)}
THRESHOLD = 0.05
LIST_SEATS = 120


def sainte_lague(votes, seats: int = LIST_SEATS) -> np.ndarray:
    """Allocate `seats` seats to parties in proportion to `votes` (Sainte-Laguë).

    Divisors are 1, 3, 5, ...; the highest `seats` quotients win.
    """
    quotients = []
    for i, v in enumerate(votes):
        if v > 0:
            quotients += [(v / (2 * k + 1), i) for k in range(seats)]
    quotients.sort(reverse=True)
    alloc = np.zeros(len(votes), int)
    for _, i in quotients[:seats]:
        alloc[i] += 1
    return alloc


def qualifying(party_votes, electorate_wins) -> np.ndarray:
    share = party_votes / party_votes.sum()
    return np.array([
        (share[i] >= THRESHOLD or electorate_wins[i] > 0) and PARTIES[i] != "OTH"
        for i in range(len(PARTIES))
    ])


def entitlements(party_votes, electorate_wins) -> np.ndarray:
    """Each party's share of the 120 seats from its party vote alone."""
    q = qualifying(party_votes, electorate_wins)
    return sainte_lague(np.where(q, party_votes, 0))


def seats_from(party_votes, electorate_wins) -> np.ndarray:
    """Final seats per party: entitlement, or electorates won if higher (overhang)."""
    return np.maximum(entitlements(party_votes, electorate_wins), electorate_wins)
