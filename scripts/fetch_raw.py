#!/usr/bin/env python3
"""Download the source data from the Electoral Commission.

    python scripts/fetch_raw.py history     # 2008-2023 voting-place CSVs -> data/raw/history/
    python scripts/fetch_raw.py ge2026      # 2026 results pages -> data/raw/ge2026/<date>/
    python scripts/fetch_raw.py all
    python scripts/fetch_raw.py manifest    # checksum files downloaded with scripts/browser_fetch.js

Every file downloaded is recorded in data/raw/manifest.json with its URL,
SHA-256 and retrieval time, so anyone can check that their copy matches the
one the published results were built from (`python scripts/fetch_raw.py verify`).

Existing files are not downloaded again unless --force is given. Uses curl
if it is installed (the Commission's firewall blocks Python's HTTP client),
otherwise the standard library.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nzspecials.ge2026 import BASE as GE2026  # noqa: E402
from nzspecials.sources import MAX_ELECTORATES, YEARS, history_url  # noqa: E402

RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.json"
# The Commission's firewall rejects unfamiliar User-Agents with 403, so send ordinary browser headers.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "text/csv,text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-NZ,en;q=0.9",
}
GE2026_PAGES = ["index.html", "electorate-status.html"] + [f"electorate-details-{n:02d}.html" for n in range(1, 72)]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(dict(sorted(m.items())), indent=1) + "\n")


def _get_curl(url: str) -> tuple[int, bytes]:
    """Fetch with curl: the Commission's firewall blocks Python's own HTTP client but not curl."""
    with tempfile.NamedTemporaryFile(delete=False) as t:
        tmp = Path(t.name)
    try:
        args = ["curl", "-sSL", "--max-time", "60", "-o", str(tmp), "-w", "%{http_code}"]
        for k, v in HEADERS.items():
            args += ["-H", f"{k}: {v}"]
        r = subprocess.run(args + [url], capture_output=True, text=True)
        if r.returncode != 0:
            raise OSError(f"curl failed for {url}: {r.stderr.strip()}")
        return int(r.stdout.strip() or 0), tmp.read_bytes()
    finally:
        tmp.unlink(missing_ok=True)


def _get_urllib(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def get(url: str, tries: int = 3) -> bytes | None:
    """Return the body, or None on 404 (used to find the last electorate number)."""
    fetch = _get_curl if shutil.which("curl") else _get_urllib
    for i in range(tries):
        try:
            code, body = fetch(url)
        except OSError:
            if i == tries - 1:
                raise
            code, body = 0, b""
        if code == 200:
            if body.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")) and url.endswith(".csv"):
                sys.exit(f"Got an HTML page instead of a CSV from {url} (probably a firewall block page)")
            return body
        if code == 404:
            return None
        if code == 403 and i == tries - 1:
            sys.exit(f"403 Forbidden from {url}\nCheck the URL in a browser. If the browser also fails, the URL is wrong; "
                     "if it works, the server is blocking scripted downloads.")
        time.sleep(2 * (i + 1))
    raise OSError(f"Could not fetch {url} (last status {code})")


def save(rel: str, url: str, manifest: dict, force: bool) -> str:
    path = RAW / rel
    if path.exists() and not force:
        return "kept"
    body = get(url)
    if body is None:
        return "missing"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    manifest[rel] = {"url": url, "sha256": sha256(body), "bytes": len(body),
                     "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    time.sleep(0.15)  # be polite to the Commission's servers
    return "fetched"


def fetch_history(force: bool) -> None:
    m = load_manifest()
    for year in YEARS:
        counts = {"fetched": 0, "kept": 0}
        for kind in ("candidate", "party"):
            for n in range(1, MAX_ELECTORATES + 1):
                status = save(f"history/{year}/{kind}/{n}.csv", history_url(year, kind, n), m, force)
                if status == "missing":
                    break  # electorates are numbered 1..N with no gaps
                counts[status] += 1
        save_manifest(m)
        print(f"{year}: {counts['fetched']} fetched, {counts['kept']} already present")


def fetch_ge2026(force: bool) -> None:
    m = load_manifest()
    day = dt.date.today().isoformat()
    n = 0
    for page in GE2026_PAGES:
        if save(f"ge2026/{day}/{page}", f"{GE2026}/{page}", m, force) == "fetched":
            n += 1
    save_manifest(m)
    print(f"ge2026: {n} pages saved to data/raw/ge2026/{day}/")


def build_manifest() -> int:
    """Record checksums for history files obtained another way (e.g. scripts/browser_fetch.js)."""
    m = load_manifest()
    n = 0
    for year in YEARS:
        for kind in ("candidate", "party"):
            for f in sorted((RAW / "history" / year / kind).glob("*.csv"), key=lambda p: int(p.stem)):
                rel = f.relative_to(RAW).as_posix()
                if rel in m:
                    continue
                body = f.read_bytes()
                m[rel] = {"url": history_url(year, kind, int(f.stem)), "sha256": sha256(body), "bytes": len(body),
                          "retrieved_at": dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds"),
                          "via": "browser"}
                n += 1
    extra = [(f, f"https://archive.electionresults.govt.nz/electionresults_2023/statistics/csv/split-votes-electorate-{f.stem}.csv")
             for f in (RAW / "splitvotes" / "2023").glob("*.csv")]
    extra += [(f, f"{GE2026}/{f.name}") for f in (RAW / "ge2026").glob("*/*.html")]
    for f, url in extra:
        rel = f.relative_to(RAW).as_posix()
        if rel in m:
            continue
        body = f.read_bytes()
        m[rel] = {"url": url, "sha256": sha256(body), "bytes": len(body),
                  "retrieved_at": dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds"), "via": "browser"}
        n += 1
    save_manifest(m)
    print(f"Added {n} files to {MANIFEST.relative_to(ROOT)} ({len(m)} total)")
    return 0


def verify() -> int:
    m = load_manifest()
    bad = [rel for rel, e in m.items() if not (RAW / rel).exists() or sha256((RAW / rel).read_bytes()) != e["sha256"]]
    print(f"{len(m) - len(bad)}/{len(m)} files match the manifest")
    for rel in bad[:20]:
        print("  mismatch or missing:", rel)
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["history", "ge2026", "all", "verify", "manifest"])
    ap.add_argument("--force", action="store_true", help="download again even if the file exists")
    a = ap.parse_args()
    if a.what == "verify":
        return verify()
    if a.what == "manifest":
        return build_manifest()
    if a.what in ("history", "all"):
        fetch_history(a.force)
    if a.what in ("ge2026", "all"):
        fetch_ge2026(a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
