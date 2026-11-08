"""Parse the Electoral Commission's 2026 results pages (electionresults.govt.nz/ge2026/).

These pages show the preliminary count until the official result is
published on 27 November 2026, when the same URLs switch to official
figures. data/inputs/prelim_2026.json is the snapshot of the preliminary
count the model uses; `make fetch-2026` saves a dated copy of the pages so
the official result can be compared with the model afterwards.
"""
from __future__ import annotations

import html as htmllib
import re

BASE = "https://electionresults.govt.nz/ge2026"
PARTY_CODES = {"NAT": "NAT", "LAB": "LAB", "GP": "GP", "ACT": "ACT", "NZF": "NZF", "OPP": "OPP", "TPMAO": "TPM"}


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _cells(row_html: str) -> list[str]:
    return [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]


def parse_electorate_status(page: str) -> dict:
    """electorate-status.html -> {electorate: {leader, runner_up, margin, details}}"""
    out = {}
    for row in re.findall(r"<tr[^>]*electorate-row[^>]*>(.*?)</tr>", page, re.S):
        c = _cells(row)
        link = re.search(r'href="\./(electorate-details-\d+\.html)"', row)
        lead = re.search(r"\(([A-Z]+)\)\s*$", c[1].replace("Leading Candidate:", "").strip())
        second = re.search(r"\(([A-Z]+)\)\s*$", c[2].replace("2nd Candidate:", "").strip())
        margin = int(re.sub(r"[^\d]", "", c[3]))
        out[c[0]] = {
            "leader": PARTY_CODES.get(lead.group(1), "OTH") if lead else None,
            "runner_up": PARTY_CODES.get(second.group(1), "OTH") if second else None,
            "margin": margin,
            "details": link.group(1) if link else None,
        }
    return out


def parse_overall(page: str) -> dict:
    """index.html overall-results table -> {party name: votes}, plus the total."""
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        c = _cells(row)
        if len(c) >= 2 and re.fullmatch(r"[\d,]+", c[1] or ""):
            out[c[0]] = int(c[1].replace(",", ""))
    return out


def parse_votes_counted(page: str) -> int | None:
    """electorate-details-NN.html -> total votes counted in the electorate."""
    m = re.search(r"VOTES COUNTED:\s*(?:</[^>]+>\s*<[^>]+>\s*)*([\d,]+)", page) or re.search(r"VOTES COUNTED:[^\d]*([\d,]+)", _text(page))
    return int(m.group(1).replace(",", "")) if m else None
