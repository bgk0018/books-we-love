from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Iterable

import requests

FIRST_YEAR = 2013
DATA_DIR = Path("data")
BASE_URL = "https://apps.npr.org/best-books/{year}.json"


def _current_max_year(today: _dt.date | None = None) -> int:
    """Calculate the maximum year available based on current date."""
    today = today or _dt.date.today()
    if today.month >= 12:
        return today.year
    return today.year - 1


def available_years(today: _dt.date | None = None) -> list[int]:
    """Get list of available years from FIRST_YEAR to current max year."""
    last_year = _current_max_year(today)
    if last_year < FIRST_YEAR:
        return []
    return list(range(FIRST_YEAR, last_year + 1))


def _target_years(year: int | None) -> Iterable[int]:
    """Get target years - single year or all available years."""
    if year is not None:
        return [year]
    return available_years()


def _fetch_year(year: int) -> dict | None:
    """Download JSON for a specific year from NPR."""
    url = BASE_URL.format(year=year)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to download {year}: {exc}")
        return None


def _save_year_json(year: int, payload: dict) -> Path:
    """Save JSON payload to local file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / f"best-books-{year}.json"
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return target


def _ensure_local_year_json(year: int) -> None:
    """Ensure the JSON file for a year exists locally, downloading if needed."""
    path = DATA_DIR / f"best-books-{year}.json"
    if path.exists():
        return

    print(f"Downloading {year} ...")
    payload = _fetch_year(year)
    if payload is None:
        return
    saved = _save_year_json(year, payload)
    print(f"Saved {year} to {saved}")


def seed_books(year: int | None = None) -> None:
    """Download JSON for one year or all years and save to ./data."""
    years = list(_target_years(year))
    if not years:
        print("No years to download.")
        return

    for y in years:
        print(f"Downloading {y} ...")
        payload = _fetch_year(y)
        if payload is None:
            continue
        path = _save_year_json(y, payload)
        print(f"Saved {y} to {path}")

