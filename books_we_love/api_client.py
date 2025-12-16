from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Tuple

from readarr import (
    ApiClient,
    BookApi,
    BookResource,
    Configuration,
    SearchApi,
)


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


def _call_search(term: str) -> list[Dict[str, Any]]:
    """Call the search API for books or authors."""
    cfg = _load_config()
    with ApiClient(cfg) as api_client:
        api_instance = SearchApi(api_client)
        try:
            # Use with_http_info to get full response; response_type is None so we parse manually
            response = api_instance.get_search_with_http_info(term=term)
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
    """Pick the first item from search results and extract its ID."""
    if not items:
        return None
    first = items[0]
    # Try to get foreignBookId for books, or foreignAuthorId for authors
    api_id = (
        first.get("foreignBookId")
        or first.get("foreignAuthorId")
        or first.get("foreignId")
    )
    if api_id:
        return str(api_id), first
    return None


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
    goodreads_id -> isbn13 -> isbn10 -> author (search).

    Uses the generated client from readarr-py to hit Readarr's search
    endpoint: /api/v1/search.
    See: [`readarr-py`](https://github.com/devopsarr/readarr-py)
    """
    # 1) Try goodreads id against search.
    if goodreads_id:
        print(f"  -> Trying Goodreads ID: {goodreads_id}")
        items = _call_search(goodreads_id)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            print(f"  -> Found via Goodreads ID")
            return ApiResult(found=True, entity_type="book", api_id=api_id, extra=data)
        print(f"  -> No results for Goodreads ID")

    # 2) Try isbn13.
    if isbn13:
        print(f"  -> Trying ISBN-13: {isbn13}")
        items = _call_search(isbn13)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            print(f"  -> Found via ISBN-13")
            return ApiResult(found=True, entity_type="book", api_id=api_id, extra=data)
        print(f"  -> No results for ISBN-13")

    # 3) Try isbn10.
    if isbn10:
        print(f"  -> Trying ISBN-10: {isbn10}")
        items = _call_search(isbn10)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            print(f"  -> Found via ISBN-10")
            return ApiResult(found=True, entity_type="book", api_id=api_id, extra=data)
        print(f"  -> No results for ISBN-10")

    # 4) Fallback to author search if we have an author name.
    if author:
        print(f"  -> Trying author search: {author}")
        items = _call_search(author)
        picked = _pick_first(items)
        if picked is not None:
            api_id, data = picked
            # Determine entity type based on response structure
            entity_type = "author" if "foreignAuthorId" in data else "book"
            print(f"  -> Found via author search")
            return ApiResult(
                found=True, entity_type=entity_type, api_id=api_id, extra=data
            )
        print(f"  -> No results for author search")

    print("  -> No matches found after trying all available search values")
    return ApiResult(found=False)


def _transform_lookup_to_post(lookup_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform lookup response format to POST format for creating a book.

    Changes:
    - Extract 'book' object from lookup response
    - Set monitored=True for both book and author
    - Set qualityProfileId and metadataProfileId for author (if available)
    - Add addOptions to book and author
    - Add rootFolderPath to author
    - Preserve all other fields including author and editions
    """
    # Debug: print original lookup data structure
    print(
        "  -> Original lookup data keys:",
        list(lookup_data.keys()) if isinstance(lookup_data, dict) else "not a dict",
    )

    # Extract book object if wrapped (use deep copy to preserve nested structures)
    if "book" in lookup_data:
        book_data = copy.deepcopy(lookup_data["book"])
    else:
        book_data = copy.deepcopy(lookup_data)

    # Debug: print book data structure
    print(
        "  -> Book data keys:",
        list(book_data.keys()) if isinstance(book_data, dict) else "not a dict",
    )

    # Set book-level monitored
    book_data["monitored"] = True

    # Transform author if present
    if "author" in book_data:
        author = book_data["author"]
        author["monitored"] = True

        # Get quality profile ID (try env var first, then fetch default)
        quality_profile_id = os.getenv("READARR_QUALITY_PROFILE_ID")
        if quality_profile_id:
            try:
                author["qualityProfileId"] = int(quality_profile_id)
            except ValueError:
                pass

        # Metadata profile ID (try env var, default to 1 if not set)
        metadata_profile_id = os.getenv("READARR_METADATA_PROFILE_ID")
        if metadata_profile_id:
            try:
                author["metadataProfileId"] = int(metadata_profile_id)
            except ValueError:
                pass
        else:
            # Default to 1 if not configured
            if (
                "metadataProfileId" not in author
                or author.get("metadataProfileId") == 0
            ):
                author["metadataProfileId"] = 1

        # Add addOptions to author
        if "addOptions" not in author:
            author["addOptions"] = {"monitor": "all", "searchForMissingBooks": True}

        # Add rootFolderPath to author
        root_folder = os.getenv("READARR_ROOT_FOLDER_PATH", "/data/media/books")
        if "rootFolderPath" not in author:
            author["rootFolderPath"] = root_folder
    else:
        print("  -> WARNING: No 'author' field found in book data")

    # Add addOptions to book
    if "addOptions" not in book_data:
        book_data["addOptions"] = {"searchForNewBook": True}

    return book_data


def create_book(lookup_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Create a book in Readarr using the lookup response data.

    Transforms the lookup response to POST format and calls create_book_with_http_info.
    Returns the created book data or None on error.
    """
    cfg = _load_config()
    with ApiClient(cfg) as api_client:
        api_instance = BookApi(api_client)
        try:
            # Transform lookup data to POST format
            post_data = _transform_lookup_to_post(lookup_data)

            # Pretty print for debugging
            print("  -> POST payload:")
            print(json.dumps(post_data, indent=2, ensure_ascii=False))

            # Create BookResource from dict
            book_resource = BookResource.from_dict(post_data)

            # Call create_book_with_http_info
            response = api_instance.create_book_with_http_info(
                book_resource=book_resource
            )

            # Parse response
            if response.data is not None:
                result = response.data
            else:
                raw_json = response.raw_data.decode("utf-8")
                result = json.loads(raw_json) if raw_json else None

            if result is None:
                return None

            # Convert to dict if needed
            if hasattr(result, "to_dict"):
                return result.to_dict()
            if isinstance(result, dict):
                return result
            return None

        except Exception as e:
            print(f"  -> API error creating book: {type(e).__name__}: {e}")
            return None
