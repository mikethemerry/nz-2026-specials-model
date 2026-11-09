# How special votes could change the 2026 NZ election result

A Monte Carlo model of the 2026 New Zealand general election special-vote count. It starts from the Electoral Commission's preliminary count and asks which of three worlds we end up in once about 399,000 special votes are added:

1. **National, ACT and NZ First govern alone** - the coalition holds a majority of the House.
2. **National needs Opportunity** - neither bloc has a majority, so Opportunity holds the balance of power.
3. **Labour could form a government** - Labour, Green, Te Pāti Māori and Opportunity together hold a majority.

**Live site:** https://mikethemerry.github.io/nz-2026-specials-model/

## Headline (central case, 20,000 runs)

| Outcome | Share of runs |
|---|---|
| Coalition governs alone | 50.3% |
| National needs Opportunity | 17.5% |
| Labour could form a government | 32.2% |
| **Opportunity pivotal (2 + 3)** | **49.7%** |

The result is close to a coin toss. It depends mostly on how strongly 2026's specials lean left compared with past elections. The sensitivity runs cover this: at 70% of the historical lean the coalition governs alone 59.3% of the time, and at 100% it does so 43.2% of the time. See `outputs/summary.json` for every variant.

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
5. **Candidates.** Every seat uses the candidates actually standing in 2026 (`data/inputs/candidates_2026.json`). The 2023 split-vote statistics give each party's voters a weight for each type of candidate, and a party with no candidate has its voters spread over those who are standing (`data/inputs/flows_2023.json`, `nzspecials/flows.py`). In each seat the flows are calibrated to reproduce the 2026 ordinary-vote candidate results exactly, then applied to the seat's special party vote. The difference from a field with every major party standing is added to the swing. Hamilton East, with no Green or ACT candidate, gets +1.4 points to Labour, which lifts Labour's chance there from 20% to 30%. A few other seats without a Green candidate move by a similar amount (Takanini, New Plymouth, Whangaparāoa, Manurewa), but their margins are over 1,000 votes, so none of them comes close to changing hands. Wairarapa, which has no ACT candidate, moves by 0.1 points.
6. **Seats.** Seats are allocated under MMP rules: Sainte-Laguë over 120 seats, a 5% or one-electorate threshold, and overhang. National's 42 electorates against a party-vote entitlement of about 35 is what makes the House 131 seats.

The full list of assumptions, with the basis for each, is in [`data/inputs/assumptions.json`](data/inputs/assumptions.json) and on the site. The parameters for every run are in [`configs/`](configs/).

### How well the electorate model predicts

`make backtest` tests the electorate model on 181 Labour v National seat results from 2017-2023. Each year is predicted using only the other years' data, and the error is the root-mean-square miss on the special-vote margin between the top two candidates:

| Method | Error |
|---|---|
| Swing (template average + seat lean), as used | 3.7 pts |
| Swing + candidate-field adjustment, as used | 3.6 pts |
| Flows only, from predicted special party votes | 4.7 pts |
| Flows only, given each seat's actual special party vote | 3.7 pts |
| Template average swing, no seat lean | 5.6 pts |

The candidate-field adjustment's improvement is within noise. In past elections a missing candidate moved the special-vote swing too little to detect against seat-to-seat variation, so the adjustment rests mainly on the split-vote evidence. Flows alone do worse, because special voters split their electorate vote somewhat differently from ordinary voters of the same party. That's why flows are used only for the effect of the candidate field. Full results are in `outputs/backtest_flows.json`.

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
                        # if the archive blocks scripted downloads, run scripts/browser_fetch.js (history + split votes)
                        # and scripts/browser_fetch_2026.js (2026 pages) in a browser instead; see their headers
make verify-raw         # SHA-256 check against data/raw/manifest.json
make check-calibration  # rebuilds data/inputs/calibration.json from data/raw/ and diffs it
make check-prelim       # compares prelim_2026.json and candidates_2026.json with the 2026 snapshot
make check-flows        # rebuilds the party-to-candidate flow weights from the 2023 split votes and diffs them
make backtest           # electorate-model backtest on 2017-2023 (writes docs/data/backtest.json)
```

## Audit trail

```
Electoral Commission
 ├─ archive.electionresults.govt.nz (2008-2023 voting-place CSVs)
 │     └─ scripts/fetch_raw.py ─► data/raw/history/ + manifest.json (sha256)
 │            └─ nzspecials/calibration.py ─► data/inputs/calibration.json
 ├─ 2023 split-vote statistics ─► data/raw/splitvotes/2023/
 │            └─ nzspecials/splitvotes.py ─► data/inputs/flows_2023.json
 ├─ electionresults.govt.nz/ge2026 (2026 preliminary count)
 │     └─ data/inputs/prelim_2026.json, candidates_2026.json   (checked by scripts/check_prelim.py)
 └─ elections.nz, vote.nz (special-vote estimate, enrolment)
       └─ data/inputs/context_2026.json, enrolment_2026.json  (hand-transcribed, each with source URL)

configs/*.json + data/inputs/ ─► nzspecials/model.py ─► outputs/runs/*.npz
                                    nzspecials/analysis.py ─► docs/data/*.json ─► docs/index.html
```

Every number on the site is read from `docs/data/*.json`; none is typed into the page. The places where human judgement enters are listed below, so those are where to push back:

- the central lean (`k_mean`) and valid share (`valid`) in `configs/central.json`
- the template-year weights
- the seat-lean shrink and noise parameters in `nzspecials/model.py` (`Config`)
- the predecessor mapping for seats redrawn in 2025 (`nzspecials/calibration.py`, `PREDECESSORS`)
- the candidate-field adjustment: on in the central case, off in the `no_field` variant (`candidate_field` in `configs/`).

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
  flows.py          party vote -> electorate candidate flows, seat calibration, candidate-field effect
  splitvotes.py     2023 split-vote CSVs -> flows_2023.json
  ge2026.py         parsers for the 2026 results pages
  model.py          the simulation
  analysis.py       scenario classification and the site's datasets
scripts/            fetch_raw.py, browser_fetch*.js, build_calibration.py, build_flows.py, check_prelim.py,
                    backtest_flows.py, run_model.py
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

## Changes

- **Candidates (9 Nov 2026).** The electorate model now uses the candidates actually standing in each seat (step 5 above). This moves the central case from 52.6 / 17.5 / 29.9 to 50.3 / 17.5 / 32.2, almost entirely through Hamilton East. The previous seat model is kept as the `no_field` variant.

## Corrections

- **Hamilton East specials.** An earlier version of the dashboard gave the model's expected Hamilton East specials as 5,093. That figure was computed at the old 91% valid share. At the revised 85% it is about 4,757, and this repo uses the corrected figure. The model runs themselves were unaffected.

- **Polling places named "Special".** The first calibration counted votes cast at polling places named "Special" or "Overseas" as special votes. These were Sunnydene Special School and Wairau Valley Special School, the Special Needs Library (Wellington) and the Overseas Terminal (Wellington). The parser now matches only the Commission's special-vote summary rows, and `tests/test_sources.py` covers this case. The fix changed seven seat-level calibration values; the largest was Mt Roskill's special-vote lean, which went from -3.6 to -4.2 pts. It also changed the 2011 mean swing. No scenario share moved by more than 0.2 points: the central case went from 52.5 / 17.6 / 30.0 to 52.6 / 17.5 / 29.9. The first published dashboard shows the earlier figures.

## Credits

Analysis and code developed by Mike Merry with Claude (Anthropic) as a coding and analysis assistant. Data © New Zealand Electoral Commission, used under its terms (see `data/README.md`). Code is MIT-licensed.
