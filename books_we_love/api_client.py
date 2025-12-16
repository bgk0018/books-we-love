from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Tuple

from readarr import ApiClient, AuthorLookupApi, BookLookupApi, Configuration


@dataclass(slots=True)
class ApiResult:
    found: bool
    entity_type: Literal["book", "author"] = "book"
    api_id: str | None = None
    extra: Dict[str, Any] = field(default_factory=dict)


def _load_config() -> Configuration:
    endpoint = os.getenv("READARR_API_ENDPOINT")
    api_key = os.getenv("READARR_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError(
            "READARR_API_ENDPOINT and READARR_API_KEY must be set in the environment."
        )

    # Ensure endpoint doesn't have trailing slash for consistency
    endpoint = endpoint.rstrip("/")
    cfg = Configuration(host=endpoint)
    # readarr-py supports both header and query-string auth; header is preferred.
    cfg.api_key["X-Api-Key"] = api_key
    return cfg


def _call_book_lookup(term: str) -> list[Dict[str, Any]]:
    """Call the book lookup API."""
    cfg = _load_config()
    with ApiClient(cfg) as api_client:
        api_instance = BookLookupApi(api_client)
        try:
            # Use with_http_info to get full response; response_type is None so we parse manually
            response = api_instance.get_book_lookup_with_http_info(term=term)
            if response.data is not None:
                # If data was deserialized, use it
                result = response.data
            else:
                # Otherwise parse raw_data as JSON
                raw_json = response.raw_data.decode("utf-8")
                result = json.loads(raw_json) if raw_json else []

            if not result:
                return []
            if isinstance(result, list):
                return [
                    item if isinstance(item, dict) else item.to_dict()
                    for item in result
                ]
            return []
        except Exception as e:
            print(f"  -> API error: {type(e).__name__}: {e}")
            return []


def _call_author_lookup(term: str) -> list[Dict[str, Any]]:
    """Call the author lookup API."""
    cfg = _load_config()
    with ApiClient(cfg) as api_client:
        api_instance = AuthorLookupApi(api_client)
        try:
            # Use with_http_info to get full response; response_type is None so we parse manually
            response = api_instance.get_author_lookup_with_http_info(term=term)
            if response.data is not None:
                # If data was deserialized, use it
                result = response.data
            else:
                # Otherwise parse raw_data as JSON
                raw_json = response.raw_data.decode("utf-8")
                result = json.loads(raw_json) if raw_json else []

            if not result:
                return []
            if isinstance(result, list):
                return [
                    item if isinstance(item, dict) else item.to_dict()
                    for item in result
                ]
            return []
        except Exception as e:
            print(f"  -> API error: {type(e).__name__}: {e}")
            return []


def _pick_first(items: list[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]] | None:
    if not items:
        return None
    first = items[0]
    api_id = first.get("foreignBookId")
    return str(api_id), first


def search_book(
    *,
    isbn10: str | None = None,
    isbn13: str | None = None,
    goodreads_id: str | None = None,
    author: str | None = None,
    title: str | None = None,
) -> ApiResult:
    """
    Look up a book or author in Readarr, trying identifiers in this order:
    goodreads_id -> isbn13 -> isbn10 -> author (author lookup).

    Uses the generated client from readarr-py to hit Readarr's lookup
    endpoints: /api/v1/book/lookup and /api/v1/author/lookup.
    See: [`readarr-py`](https://github.com/devopsarr/readarr-py)
    """
    # 1) Try goodreads id against book lookup.
    if goodreads_id:
        print(f"  -> Trying Goodreads ID: {goodreads_id}")
        items = _call_book_lookup(goodreads_id)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            print(f"  -> Found via Goodreads ID")
            return ApiResult(found=True, entity_type="book", api_id=api_id, extra=data)
        print(f"  -> No results for Goodreads ID")

    # 2) Try isbn13.
    if isbn13:
        print(f"  -> Trying ISBN-13: {isbn13}")
        items = _call_book_lookup(isbn13)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            print(f"  -> Found via ISBN-13")
            return ApiResult(found=True, entity_type="book", api_id=api_id, extra=data)
        print(f"  -> No results for ISBN-13")

    # 3) Try isbn10.
    if isbn10:
        print(f"  -> Trying ISBN-10: {isbn10}")
        items = _call_book_lookup(isbn10)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            print(f"  -> Found via ISBN-10")
            return ApiResult(found=True, entity_type="book", api_id=api_id, extra=data)
        print(f"  -> No results for ISBN-10")

    # 4) Fallback to author lookup if we have an author name.
    if author:
        print(f"  -> Trying author lookup: {author}")
        items = _call_author_lookup(author)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            print(f"  -> Found via author lookup")
            return ApiResult(
                found=True, entity_type="author", api_id=api_id, extra=data
            )
        print(f"  -> No results for author lookup")

    print("  -> No matches found after trying all available search values")
    return ApiResult(found=False)
