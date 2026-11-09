PY ?= python3

.PHONY: all fetch fetch-history fetch-2026 verify-raw check-prelim check-flows backtest calibrate check-calibration run test check serve clean

all: test run

## Data ------------------------------------------------------------------
fetch: fetch-history fetch-2026        ## download all source data from the Electoral Commission

fetch-history:                         ## 2008-2023 voting-place CSVs -> data/raw/history/
	$(PY) scripts/fetch_raw.py history

fetch-2026:                            ## dated snapshot of the 2026 results pages -> data/raw/ge2026/
	$(PY) scripts/fetch_raw.py ge2026

verify-raw:                            ## check data/raw against data/raw/manifest.json checksums
	$(PY) scripts/fetch_raw.py verify

check-prelim:                          ## compare prelim_2026.json with the latest 2026 snapshot
	$(PY) scripts/check_prelim.py

check-calibration:                     ## rebuild calibration from data/raw and diff with the committed file
	$(PY) scripts/build_calibration.py --check

check-flows:                           ## rebuild the party-to-candidate flow weights from data/raw/splitvotes and diff
	$(PY) scripts/build_flows.py --check

backtest:                              ## backtest the electorate model on 2017-2023 (needs data/raw); writes docs/data/backtest.json
	$(PY) scripts/backtest_flows.py

calibrate:                             ## rebuild and overwrite data/inputs/calibration.json
	$(PY) scripts/build_calibration.py

## Model -----------------------------------------------------------------
run:                                   ## run every config, write outputs/ and docs/data/
	$(PY) scripts/run_model.py

test:
	$(PY) -m pytest -q

check: test run                        ## rerun everything and fail if the published site data changes
	git diff --exit-code -- docs/data outputs/summary.json

serve:                                 ## preview the site at http://localhost:8000
	cd docs && $(PY) -m http.server 8000

clean:
	rm -rf outputs/runs .pytest_cache **/__pycache__
