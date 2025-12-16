from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

from . import datastore
from .api_client import ApiResult, search_book
from .downloader import DATA_DIR, _target_years

FIRST_YEAR = 2013


def _iter_local_books(year: int | None = None) -> Iterable[Tuple[int, Dict]]:
    """Iterate over books from local JSON files."""
    years = list(_target_years(year))
    for y in years:
        path = DATA_DIR / f"best-books-{y}.json"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            try:
                payload = json.load(f)
            except Exception:  # noqa: BLE001
                continue
        if not isinstance(payload, list):
            continue
        for book in payload:
            if isinstance(book, dict):
                yield y, book


def track_books(
    year: int | None = None,
    *,
    status: str | None = None,
    book_id: int | None = None,
    limit: int = 10,
    max_attempts: int = 5,
    dry_run: bool = False,
    output_format: str = "json",
) -> None:
    """Process books: populate datastore and call external API for tracking."""
    from .cli import output
    from .downloader import _ensure_local_year_json

    # Ensure local JSON exists for all years we intend to process.
    target_years = list(_target_years(year))
    for y in target_years:
        _ensure_local_year_json(y)

    state = datastore.load_state()

    total_books = 0
    for y, book in _iter_local_books(year):
        datastore.ensure_book_entry(state, year=y, book=book)
        total_books += 1
    datastore.save_state_atomic(state)

    if total_books == 0:
        print("No local books found under ./data.")
        return

    now = _dt.datetime.utcnow().replace(microsecond=0)

    # Handle specific book if both year and book_id are provided
    if book_id is not None:
        if year is None:
            print("Error: --year is required when --id is specified.")
            return
        key = f"{year}:{book_id}"
        payload = state.get(key)
        if payload is None:
            print(f"No datastore record found for {year}:{book_id}.")
            return
        rec = datastore.BookRecord.from_state(key, payload)

        # Check status filter if specified
        if status is not None:
            if rec.status.value != status:
                print(
                    f"Book {year}:{book_id} does not match status filter (status: {rec.status.value}, filter: {status})."
                )
                return

        # Check if book is eligible for processing (default: only PENDING and FAILED)
        if status is None and rec.status not in (
            datastore.Status.PENDING,
            datastore.Status.FAILED,
        ):
            print(
                f"Book {year}:{book_id} is not eligible for processing (status: {rec.status.value})."
            )
            return

        # Check retry time for FAILED status
        if (
            rec.status == datastore.Status.FAILED
            and rec.next_retry_at is not None
            and rec.next_retry_at > now
        ):
            print(
                f"Book {year}:{book_id} is not yet eligible for retry (next_retry_at: {rec.next_retry_at})."
            )
            return

        if dry_run:
            results = [
                {
                    "source_year": rec.source_year,
                    "local_id": rec.local_id,
                    "title": rec.title,
                    "author": rec.author,
                    "status": rec.status.value,
                    "attempts": rec.attempts,
                    "next_retry_at": (
                        rec.next_retry_at.isoformat() if rec.next_retry_at else None
                    ),
                }
            ]
            print(f"1 book eligible for processing (dry run, no API calls).")
            output.format_output(results, output_format)
            return

        # Process the specific book
        print(f"Processing {rec.source_year}:{rec.local_id} {rec.title} ...")
        datastore.mark_in_progress(rec, now=now)
        state[key] = rec.to_state()
        datastore.save_state_atomic(state)

        result_data = {
            "source_year": rec.source_year,
            "local_id": rec.local_id,
            "title": rec.title,
            "author": rec.author,
        }

        try:
            result: ApiResult = search_book(
                isbn10=rec.isbn10,
                isbn13=rec.isbn13,
                goodreads_id=rec.goodreads_id,
                author=rec.author,
                title=rec.title,
            )
            if result.found and result.api_id and result.entity_type:
                datastore.mark_tracked(
                    rec,
                    entity_type=result.entity_type,
                    api_id=result.api_id,
                    extra=result.extra,
                    now=now,
                )
                print("  -> marked as tracked in external system.")
                result_data.update(
                    {
                        "status": "tracked",
                        "entity_type": result.entity_type,
                        "api_id": result.api_id,
                    }
                )
            else:
                datastore.mark_failed_with_backoff(
                    rec,
                    error="not found",
                    max_attempts=max_attempts,
                    now=now,
                )
                print(
                    f"  -> not found (attempts={rec.attempts}, next_retry_at={rec.next_retry_at})."
                )
                result_data.update(
                    {
                        "status": "not_found",
                        "attempts": rec.attempts,
                        "next_retry_at": (
                            rec.next_retry_at.isoformat() if rec.next_retry_at else None
                        ),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            datastore.mark_failed_with_backoff(
                rec,
                error=str(exc),
                max_attempts=max_attempts,
                now=now,
            )
            print(
                f"  -> error calling external API: {exc} "
                f"(attempts={rec.attempts}, next_retry_at={rec.next_retry_at})."
            )
            result_data.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "attempts": rec.attempts,
                    "next_retry_at": (
                        rec.next_retry_at.isoformat() if rec.next_retry_at else None
                    ),
                }
            )

        state[key] = rec.to_state()
        datastore.save_state_atomic(state)
        output.format_output([result_data], output_format)
        return

    if dry_run:
        pending = list(
            datastore.iter_pending(
                state, now=now, limit=limit, year=year, status=status
            )
        )
        print(f"{len(pending)} books eligible for processing (dry run, no API calls).")
        results = []
        for _, rec in pending:
            results.append(
                {
                    "source_year": rec.source_year,
                    "local_id": rec.local_id,
                    "title": rec.title,
                    "author": rec.author,
                    "status": rec.status.value,
                    "attempts": rec.attempts,
                    "next_retry_at": (
                        rec.next_retry_at.isoformat() if rec.next_retry_at else None
                    ),
                }
            )
        output.format_output(results, output_format)
        return

    processed = 0
    results = []
    for key, rec in datastore.iter_pending(
        state, now=now, limit=limit, year=year, status=status
    ):
        print(f"Processing {rec.source_year}:{rec.local_id} {rec.title} ...")
        datastore.mark_in_progress(rec, now=now)
        state[key] = rec.to_state()
        datastore.save_state_atomic(state)

        result_data = {
            "source_year": rec.source_year,
            "local_id": rec.local_id,
            "title": rec.title,
            "author": rec.author,
        }

        try:
            result: ApiResult = search_book(
                isbn10=rec.isbn10,
                isbn13=rec.isbn13,
                goodreads_id=rec.goodreads_id,
                author=rec.author,
                title=rec.title,
            )
            if result.found and result.api_id and result.entity_type:
                datastore.mark_tracked(
                    rec,
                    entity_type=result.entity_type,
                    api_id=result.api_id,
                    extra=result.extra,
                    now=now,
                )
                print("  -> marked as tracked in external system.")
                result_data.update(
                    {
                        "status": "tracked",
                        "entity_type": result.entity_type,
                        "api_id": result.api_id,
                    }
                )
            else:
                datastore.mark_failed_with_backoff(
                    rec,
                    error="not found",
                    max_attempts=max_attempts,
                    now=now,
                )
                print(
                    f"  -> not found (attempts={rec.attempts}, next_retry_at={rec.next_retry_at})."
                )
                result_data.update(
                    {
                        "status": "not_found",
                        "attempts": rec.attempts,
                        "next_retry_at": (
                            rec.next_retry_at.isoformat() if rec.next_retry_at else None
                        ),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            datastore.mark_failed_with_backoff(
                rec,
                error=str(exc),
                max_attempts=max_attempts,
                now=now,
            )
            print(
                f"  -> error calling external API: {exc} "
                f"(attempts={rec.attempts}, next_retry_at={rec.next_retry_at})."
            )
            result_data.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "attempts": rec.attempts,
                    "next_retry_at": (
                        rec.next_retry_at.isoformat() if rec.next_retry_at else None
                    ),
                }
            )

        state[key] = rec.to_state()
        datastore.save_state_atomic(state)
        processed += 1
        results.append(result_data)

    if processed == 0:
        print("No pending books eligible for processing at this time.")
    else:
        output.format_output(results, output_format)
