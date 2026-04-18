"""Download the open international football results dataset (no login required).

Source: github.com/martj42/international_results
~47,000 international matches from 1872 to present, updated regularly.

Usage:
    python -m src.data.download_open_data
    python -m src.data.download_open_data --output-csv data/raw/results.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from src.utils import PROJECT_ROOT, ensure_parent_dir

# Public raw GitHub URL — no authentication needed
_RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)
_CHUNK = 1024 * 64  # 64 KB chunks


def download_results(output_csv: str = "data/raw/results.csv") -> Path:
    """Download results.csv from the martj42 open dataset."""
    out = PROJECT_ROOT / output_csv
    ensure_parent_dir(out)

    print(f"Downloading international results -> {out}")
    print(f"Source: {_RESULTS_URL}")

    try:
        resp = requests.get(_RESULTS_URL, stream=True, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"\nERROR: Could not download data — {exc}", file=sys.stderr)
        print(
            "If the download fails, get the file manually:\n"
            "  1. Open https://github.com/martj42/international_results\n"
            "  2. Click results.csv → Download raw file\n"
            "  3. Save it to data/raw/results.csv",
            file=sys.stderr,
        )
        raise

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    with out.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=_CHUNK):
            fh.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = 100 * downloaded / total
                print(f"\r  {pct:.0f}%  ({downloaded // 1024} KB)", end="", flush=True)

    print(f"\nSaved {downloaded // 1024} KB to {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Download open international football data.")
    parser.add_argument("--output-csv", default="data/raw/results.csv")
    args = parser.parse_args()
    download_results(args.output_csv)


if __name__ == "__main__":
    main()
