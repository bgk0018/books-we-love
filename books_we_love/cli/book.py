from __future__ import annotations

from . import output, utils
from .. import datastore
from ..tracker import track_books


def handle_book_show(args) -> None:
    """Handle the book show command."""
    state = datastore.load_state()
    records = utils.state_as_list(state)

    if args.jsonpath:
        matches = utils.filter_by_jsonpath(records, args.jsonpath)
        if not matches:
            print("No matching records found.")
            return
        payloads = [state[match["_key"]] for match in matches]
        if len(payloads) == 1:
            output.format_output(payloads[0], args.output)
        else:
            output.format_output(payloads, args.output)
    else:
        if args.year is None or args.id is None:
            print("Error: must supply either --year and --id, or --jsonpath")
            return
        result = utils.find_book_by_key(state, args.year, args.id)
        if result is None:
            print(f"No datastore record found for {args.year}:{args.id}.")
            return
        key, payload = result
        output.format_output(payload, args.output)


def handle_book_reset(args) -> None:
    """Handle the book reset command."""
    state = datastore.load_state()
    records = utils.state_as_list(state)

    if args.jsonpath:
        matches = utils.find_books_by_jsonpath(state, records, args.jsonpath)
        if not matches:
            print("No matching records found.")
            return
        reset_keys = []
        for key, payload in matches:
            rec = datastore.BookRecord.from_state(key, payload)
            datastore.reset_record(rec)
            state[key] = rec.to_state()
            reset_keys.append(key)
        datastore.save_state_atomic(state)
        result = {"count": len(reset_keys), "keys": reset_keys}
        output.format_output(result, args.output)
    else:
        if args.year is None or args.id is None:
            print("Error: must supply either --year and --id, or --jsonpath")
            return
        result = utils.find_book_by_key(state, args.year, args.id)
        if result is None:
            print(f"No datastore record found for {args.year}:{args.id}.")
            return
        key, payload = result
        rec = datastore.BookRecord.from_state(key, payload)
        datastore.reset_record(rec)
        state[key] = rec.to_state()
        datastore.save_state_atomic(state)
        result_data = {"count": 1, "keys": [key]}
        output.format_output(result_data, args.output)


def handle_book_list(args) -> None:
    """Handle the book list command."""
    state = datastore.load_state()
    records = utils.state_as_list(state)

    if args.jsonpath:
        matches = utils.filter_by_jsonpath(records, args.jsonpath)
    else:
        matches = records
        if args.status:
            matches = [r for r in matches if r.get("status") == args.status]
        if args.year:
            matches = [r for r in matches if r.get("source_year") == args.year]

    matches.sort(
        key=lambda r: (
            r.get("source_year") or 0,
            r.get("local_id") or 0,
        ),
        reverse=True,
    )

    output.format_output(matches, args.output)


def handle_book_acquire(args) -> None:
    """Handle the book acquire command."""
    if args.id is not None and args.year is None:
        print("Error: --year is required when --id is specified.")
        return
    track_books(
        year=args.year,
        status=args.status,
        book_id=args.id,
        limit=args.limit,
        max_attempts=args.max_attempts,
        dry_run=args.dry_run,
        output_format=args.output,
    )
