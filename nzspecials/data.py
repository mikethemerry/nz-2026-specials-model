"""Load the model's input data from the JSON files in /data."""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "inputs"


def load_json(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_prelim() -> dict:
    """2026 preliminary count: party votes, electorate leaders and margins, special-vote estimate."""
    return load_json("prelim_2026.json")


def load_calibration() -> dict:
    """Historical special-vote calibration derived from the 2008-2023 official counts."""
    return load_json("calibration.json")
