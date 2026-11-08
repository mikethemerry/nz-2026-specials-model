# Data

```
data/
  raw/                                   untouched downloads - never edited by hand
    manifest.json                        url, sha256, bytes, retrieved_at for every file below
    history/
      2008/ 2011/ 2014/ 2017/ 2020/ 2023/
        candidate/{n}.csv                candidate votes by voting place, electorate n
        party/{n}.csv                    party votes by voting place, electorate n
    ge2026/
      YYYY-MM-DD/                        dated snapshot of electionresults.govt.nz/ge2026
        index.html                       overall party vote
        electorate-status.html           leader, runner-up and margin in every seat
        electorate-details-NN.html       per-seat detail (votes counted)
  inputs/                                what the model reads
    calibration.json                     DERIVED from raw/history by `make calibrate`
    prelim_2026.json                     TRANSCRIBED from the 2026 preliminary count (8 Nov 2026)
    context_2026.json                    TRANSCRIBED figures, each with its source URL and date
    enrolment_2026.json                  TRANSCRIBED enrolment statistics (30 Sep and Oct snapshots)
    assumptions.json                     the assumptions table shown on the site
```

## Sources

| Data | Publisher | URL |
|---|---|---|
| Votes by voting place, 2017-2023 | Electoral Commission | `archive.electionresults.govt.nz/electionresults_<year>/statistics/csv/{candidate,party}-votes-by-voting-place-<n>.csv` |
| Votes by voting place, 2008-2014 | Electoral Commission | `archive.electionresults.govt.nz/electionresults_<year>/e9/csv/e9_part8_{cand,party}_<n>.csv` |
| 2026 preliminary count | Electoral Commission | https://electionresults.govt.nz/ge2026/ |
| Special-vote estimate (399,365; 96,947 overseas) | Electoral Commission | https://elections.nz/media-and-news/2026/2026-general-election-preliminary-results |
| Enrolment by electorate, 30 Sep 2026 | Electoral Commission | https://elections.nz/stats-and-research/enrolment-statistics/enrolment-by-general-electorate |
| Enrolment updates, Oct 2026 | Electoral Commission | https://vote.nz/2026-general-election/resources/enrolment-updates |
| Expected disallowed specials (about 55,000) | 1News | see `context_2026.json` |
| Hamilton East specials claim (8,000, unverified) | Candidate's public page | see `context_2026.json` |

## How each input file is produced

- **calibration.json** is fully reproducible: `make fetch-history`, then `make check-calibration`, which rebuilds it from `raw/history/` and reports any difference. It contains:
  - each party's nationwide votes by special-vote category and year
  - the mean swing on specials in Labour v National and Labour v Te Pāti Māori seats
  - each seat's 2023 special-to-ordinary ratio
  - each seat's lean relative to the national swing
  - the history of the key marginals.
- **prelim_2026.json** was transcribed from the results pages on 8 November 2026. `make fetch-2026` saves a dated snapshot of those pages, and `make check-prelim` compares the snapshot with this file. The pages switch from the preliminary count to the official result on 27 November 2026. A snapshot taken before then should match this file exactly; a later snapshot shows what the specials changed.
- **context_2026.json** and **enrolment_2026.json** hold figures from press releases and statistics pages that are not machine-readable. Each value carries its source URL and date.

## Notes on the raw files

- Older files (2008-2014) are Windows-1252 encoded; newer ones are UTF-8. `nzspecials.calibration.read_text` handles both.
- Each file ends with summary rows for special votes cast before polling day, on polling day and overseas, then the electorate total. 2023 also has a separate "Overseas ... for Party Only" row, which is counted as overseas.
- Electorates are numbered 1..N within each election. Numbers are not stable across elections, so the model matches seats by name.

## Licence

The election data is published by the New Zealand Electoral Commission. Check the Commission's copyright terms before redistributing it. The MIT licence on this repository covers the code only.
