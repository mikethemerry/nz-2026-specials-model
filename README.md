# How special votes could change the 2026 NZ election result

A Monte Carlo model of the 2026 New Zealand general election special-vote count. It starts from the Electoral Commission's preliminary count and asks which of three worlds we end up in once about 399,000 special votes are added:

1. **National, ACT and NZ First govern alone** - the coalition holds a majority of the House.
2. **National needs Opportunity** - neither bloc has a majority, so Opportunity holds the balance of power.
3. **Labour could form a government** - Labour, Green, Te Pāti Māori and Opportunity together hold a majority.

**Live site:** https://mikethemerry.github.io/nz-2026-specials-model/

## Headline (revised central case, 20,000 runs)

| Outcome | Share of runs |
|---|---|
| Coalition governs alone | 52.6% |
| National needs Opportunity | 17.5% |
| Labour could form a government | 29.9% |
| **Opportunity pivotal (2 + 3)** | **47.4%** |

The result is close to a coin toss. It depends mostly on how strongly 2026's specials lean left compared with past elections. The sensitivity runs cover this: at 70% of the historical lean the coalition governs alone 61.6% of the time, and at 100% it does so 45.7% of the time. See `outputs/summary.json` for every variant.

Percentages that are shown together, such as the three scenarios or a row of a table, are rounded with the largest-remainder method so they always add to 100. A share that is above zero but rounds to nothing shows as "<1%".

This is a model, not a forecast from inside information. The official result is due on **27 November 2026**.

## How it works

Each simulated run makes one set of draws, and that set drives everything in the run. This keeps correlated events together, so National losing marginal seats and losing a list seat on the party vote happen in the same run, as they would on the night.

1. **Template year.** The run picks one past election (2014 15%, 2017 25%, 2020 25%, 2023 35%). Each party's special-vote share relative to its ordinary-vote share in that year is applied to 2026, separately for domestic and overseas specials.
2. **2026 adjustments.** The draws cover:
   - how strongly 2026's domestic specials lean compared with the template (85% ± 20 pts; election-day enrolment ended in 2026, but the youth enrolment surge moved late enrolment earlier rather than removing it)
   - how strongly overseas specials lean compared with the template
   - what share of specials will be valid (85% ± 2 pts, because the Commission expects about 55,000 to be disallowed).
3. **Party vote.** Specials are added to the preliminary party vote.
4. **Electorates.** Each seat draws its specials, using the 2023 special-to-ordinary ratio of the seat (or its predecessor seat) scaled to the 2026 total. It also draws a swing on specials: the template year's average swing, plus 75% of the seat's own 2017-2023 lean, plus noise. The candidate ahead after specials wins the seat.
5. **Seats.** Seats are allocated under MMP rules: Sainte-Laguë over 120 seats, a 5% or one-electorate threshold, and overhang. National's 42 electorates against a party-vote entitlement of about 35 is what makes the House 131 seats.

The full list of assumptions, with the basis for each, is in [`data/inputs/assumptions.json`](data/inputs/assumptions.json) and on the site. The parameters for every run are in [`configs/`](configs/).

## Reproduce it

You need Python 3.10+ and numpy.

```sh
git clone https://github.com/mikethemerry/nz-2026-specials-model
cd nz-2026-specials-model
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

make test        # parser, seat-allocation and reproduction tests (~10 s)
make run         # all 11 configurations, 20,000 runs each (~30 s); rewrites docs/data/
make check       # test + run, then fail if docs/data/ differs from the committed copy
make serve       # view the site at http://localhost:8000
```

The simulation is seeded (`seed: 2026`), so `make run` reproduces the published figures exactly. CI ([`.github/workflows/check.yml`](.github/workflows/check.yml)) reruns everything on each push and fails if any published number moves.

### Rebuilding from the original Electoral Commission files

```sh
make fetch              # downloads ~850 CSVs (2008-2023) and a dated 2026 snapshot into data/raw/
                        # (if the archive blocks scripted downloads, see scripts/browser_fetch.js)
make verify-raw         # SHA-256 check against data/raw/manifest.json
make check-calibration  # rebuilds data/inputs/calibration.json from data/raw/ and diffs it
make check-prelim       # compares data/inputs/prelim_2026.json with the 2026 snapshot
```

## Audit trail

```
Electoral Commission
 ├─ archive.electionresults.govt.nz (2008-2023 voting-place CSVs)
 │     └─ scripts/fetch_raw.py ─► data/raw/history/ + manifest.json (sha256)
 │            └─ nzspecials/calibration.py ─► data/inputs/calibration.json
 ├─ electionresults.govt.nz/ge2026 (2026 preliminary count)
 │     └─ data/inputs/prelim_2026.json      (checked by scripts/check_prelim.py)
 └─ elections.nz, vote.nz (special-vote estimate, enrolment)
       └─ data/inputs/context_2026.json, enrolment_2026.json  (hand-transcribed, each with source URL)

configs/*.json + data/inputs/ ─► nzspecials/model.py ─► outputs/runs/*.npz
                                    nzspecials/analysis.py ─► docs/data/*.json ─► docs/index.html
```

Every number on the site is read from `docs/data/*.json`; none is typed into the page. The places where human judgement enters are listed below, so those are where to push back:

- the central lean (`k_mean`) and valid share (`valid`) in `configs/central.json`
- the template-year weights
- the seat-lean shrink and noise parameters in `nzspecials/model.py` (`Config`)
- the predecessor mapping for seats redrawn in 2025 (`nzspecials/calibration.py`, `PREDECESSORS`).

## Repository layout

```
configs/            one JSON file per model run (central case, sensitivities, scenarios)
data/
  raw/              untouched Electoral Commission downloads + manifest.json   (see data/README.md)
  inputs/           what the model reads: calibration, 2026 preliminary count, context, assumptions
docs/               the GitHub Pages site (static HTML + d3; reads docs/data/*.json)
nzspecials/         the Python package
  allocation.py     MMP seat allocation
  sources.py        parsers for the historical Commission CSVs
  calibration.py    raw CSVs -> calibration.json
  ge2026.py         parsers for the 2026 results pages
  model.py          the simulation
  analysis.py       scenario classification and the site's datasets
scripts/            fetch_raw.py, build_calibration.py, check_prelim.py, run_model.py
tests/              pytest suite with trimmed real Commission files as fixtures
outputs/            summary.json (committed); runs/*.npz (raw simulation output, not committed)
```

## Publishing the site

Use one of these:

- **Settings → Pages → Source: GitHub Actions.** [`.github/workflows/pages.yml`](.github/workflows/pages.yml) deploys `docs/` on every push to `main`.
- **Settings → Pages → Deploy from a branch → `main` / `docs`.** If you use this option, delete `pages.yml`.

## Limitations

- Special votes are modelled by analogy with past elections. 2026 is the first election without election-day enrolment, so no past year matches it exactly.
- Seat-level specials come from 2023 ratios. A local enrolment drive, such as the reported 8,000 specials in Hamilton East, would not show up in those ratios, so it is run as a separate scenario (`configs/he8000.json`).
- Boundaries were redrawn in 2025. New seats borrow the history of their closest predecessor.
- Recounts, judicial recounts and post-count coalition negotiations are out of scope.

## Corrections

- **Hamilton East specials.** An earlier version of the dashboard gave the model's expected Hamilton East specials as 5,093. That figure was computed at the old 91% valid share. At the revised 85% it is about 4,757, and this repo uses the corrected figure. The model runs themselves were unaffected.

- **Polling places named "Special".** The first calibration counted votes cast at polling places named "Special" or "Overseas" as special votes. These were Sunnydene Special School and Wairau Valley Special School, the Special Needs Library (Wellington) and the Overseas Terminal (Wellington). The parser now matches only the Commission's special-vote summary rows, and `tests/test_sources.py` covers this case. The fix changed seven seat-level calibration values; the largest was Mt Roskill's special-vote lean, which went from -3.6 to -4.2 pts. It also changed the 2011 mean swing. No scenario share moved by more than 0.2 points: the central case went from 52.5 / 17.6 / 30.0 to 52.6 / 17.5 / 29.9. The first published dashboard shows the earlier figures.

## Credits

Analysis and code developed by Mike Merry with Claude (Anthropic) as a coding and analysis assistant. Data © New Zealand Electoral Commission, used under its terms (see `data/README.md`). Code is MIT-licensed.
