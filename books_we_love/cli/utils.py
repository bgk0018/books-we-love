from __future__ import annotations

from typing import Any, Dict

from jsonpath_ng.ext import parse as parse_jsonpath

from .. import datastore


def state_as_list(state: datastore.State) -> list[Dict[str, Any]]:
    """Convert datastore state dict to a list of records with _key for JSONPath queries."""
    items = []
    for key, payload in state.items():
        record = dict(payload)  # shallow copy
        record["_key"] = key
        items.append(record)
    return items


def filter_by_jsonpath(records: list[Dict[str, Any]], jsonpath_str: str) -> list[Dict[str, Any]]:
    """Filter records using a JSONPath expression."""
    try:
        expr = parse_jsonpath(jsonpath_str)
        matches = [m.value for m in expr.find(records)]
        return matches
    except Exception as e:
        raise ValueError(f"Invalid JSONPath expression: {e}") from e


def find_book_by_key(state: datastore.State, year: int | None, book_id: int | None) -> tuple[str, dict] | None:
    """Find a book record by year and id. Returns (key, payload) or None."""
    if year is None or book_id is None:
        return None
    key = f"{year}:{book_id}"
    payload = state.get(key)
    if payload is None:
        return None
    return (key, payload)


def find_books_by_jsonpath(state: datastore.State, records: list[Dict[str, Any]], jsonpath_str: str) -> list[tuple[str, dict]]:
    """Find book records using JSONPath. Returns list of (key, payload) tuples."""
    matches = filter_by_jsonpath(records, jsonpath_str)
    result = []
    for match in matches:
        key = match["_key"]
        payload = state[key]
        result.append((key, payload))
    return result

