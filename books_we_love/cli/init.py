from __future__ import annotations

import json
from pathlib import Path

from . import output
from .. import datastore
from ..downloader import DATA_DIR, _target_years, seed_books


def handle_init(args) -> None:
    """Handle the init command."""
    seed_books(year=args.year)

    # Populate datastore with downloaded books
    state = datastore.load_state()
    total_books = 0
    years_processed = []

    years = list(_target_years(args.year))
    for year in years:
        path = DATA_DIR / f"best-books-{year}.json"
        if not path.exists():
            continue

        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, list):
                continue

            year_count = 0
            for book in payload:
                if isinstance(book, dict):
                    datastore.ensure_book_entry(state, year=year, book=book)
                    total_books += 1
                    year_count += 1
            if year_count > 0:
                years_processed.append(year)
        except Exception:  # noqa: BLE001
            continue

    if total_books > 0:
        datastore.save_state_atomic(state)
        result = {
            "total_books": total_books,
            "years_processed": sorted(years_processed),
        }
        output.format_output(result, args.output)
    else:
        result = {
            "total_books": 0,
            "years_processed": [],
        }
        output.format_output(result, args.output)
