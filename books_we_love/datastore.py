from __future__ import annotations

import dataclasses
import datetime as _dt
import enum
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Literal, Tuple

DATA_DIR = Path("data")
STATE_PATH = DATA_DIR / "datastore.json"


def _utc_now() -> _dt.datetime:
    # Naive UTC timestamps keep things simple for comparison.
    return _dt.datetime.utcnow().replace(microsecond=0)


def _parse_dt(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _isoformat(dt: _dt.datetime | None) -> str | None:
    return None if dt is None else dt.isoformat()


class Status(str, enum.Enum):
    """Tracking status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    TRACKED = "tracked"
    FAILED = "failed"


@dataclasses.dataclass(slots=True)
class BookRecord:
    key: str
    source_year: int
    local_id: int
    title: str
    author: str
    isbn10: str | None
    isbn13: str | None = None
    goodreads_id: str | None = None
    status: Status = Status.PENDING
    attempts: int = 0
    last_attempt_at: _dt.datetime | None = None
    next_retry_at: _dt.datetime | None = None
    last_error: str | None = None
    remote_tracked: bool = False
    remote_entity_type: Literal["book", "author"] | None = None
    remote_api_id: str | None = None
    remote_extra: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_state(cls, key: str, payload: Dict[str, Any]) -> BookRecord:
        status_str = payload.get("status", Status.PENDING.value)
        try:
            status = Status(status_str)
        except ValueError:
            status = Status.PENDING

        return cls(
            key=key,
            source_year=payload["source_year"],
            local_id=payload["local_id"],
            title=payload["title"],
            author=payload["author"],
            isbn10=payload.get("identifiers", {}).get("isbn10"),
            isbn13=payload.get("identifiers", {}).get("isbn13"),
            goodreads_id=payload.get("identifiers", {}).get("goodreads_id"),
            status=status,
            attempts=payload.get("attempts", 0),
            last_attempt_at=_parse_dt(payload.get("last_attempt_at")),
            next_retry_at=_parse_dt(payload.get("next_retry_at")),
            last_error=payload.get("last_error"),
            remote_tracked=payload.get("remote", {}).get("tracked", False),
            remote_entity_type=payload.get("remote", {}).get("entity_type"),
            remote_api_id=payload.get("remote", {}).get("api_id"),
            remote_extra=payload.get("remote", {}).get("extra", {}) or {},
        )

    def to_state(self) -> Dict[str, Any]:
        return {
            "source_year": self.source_year,
            "local_id": self.local_id,
            "title": self.title,
            "author": self.author,
            "identifiers": {
                "isbn10": self.isbn10,
                "isbn13": self.isbn13,
                "goodreads_id": self.goodreads_id,
            },
            "status": self.status.value,
            "attempts": self.attempts,
            "last_attempt_at": _isoformat(self.last_attempt_at),
            "next_retry_at": _isoformat(self.next_retry_at),
            "last_error": self.last_error,
            "remote": {
                "tracked": self.remote_tracked,
                "entity_type": self.remote_entity_type,
                "api_id": self.remote_api_id,
                "extra": self.remote_extra,
            },
        }


type State = Dict[str, Dict[str, Any]]


def load_state(path: Path = STATE_PATH) -> State:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Prefer starting clean over crashing a long-lived process.
        return {}
    return {str(k): v for k, v in data.items()}


def save_state_atomic(state: State, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _book_key(year: int, local_id: int) -> str:
    return f"{year}:{local_id}"


def ensure_book_entry(state: State, *, year: int, book: Dict[str, Any]) -> None:
    local_id = int(book["id"])
    key = _book_key(year, local_id)
    if key in state:
        return

    record = BookRecord(
        key=key,
        source_year=year,
        local_id=local_id,
        title=str(book.get("title", "")).strip(),
        author=str(book.get("author", "")).strip(),
        isbn10=str(book.get("cover") or "").strip() or None,
    )
    state[key] = record.to_state()


def iter_pending(
    state: State,
    *,
    now: _dt.datetime | None = None,
    limit: int | None = None,
    year: int | None = None,
    status: str | Status | None = None,
) -> Iterator[Tuple[str, BookRecord]]:
    now = now or _utc_now()

    status_value = status.value if isinstance(status, Status) else status
    if status_value is None:
        # Default behavior: only PENDING and FAILED
        allowed_statuses = (Status.PENDING, Status.FAILED)
    else:
        # If status is specified, use only that status
        try:
            allowed_statuses = (Status(status_value),)
        except ValueError:
            return

    count = 0
    for key, payload in state.items():
        record = BookRecord.from_state(key, payload)

        # Filter by year if specified
        if year is not None and record.source_year != year:
            continue

        # Filter by status
        if record.status not in allowed_statuses:
            continue

        # Check retry time for FAILED status
        if (
            record.status == Status.FAILED
            and record.next_retry_at is not None
            and record.next_retry_at > now
        ):
            continue

        yield key, record
        count += 1
        if limit is not None and count >= limit:
            return


def mark_in_progress(record: BookRecord, *, now: _dt.datetime | None = None) -> None:
    now = now or _utc_now()
    record.status = Status.IN_PROGRESS
    record.last_attempt_at = now


def mark_tracked(
    record: BookRecord,
    *,
    entity_type: Literal["book", "author"],
    api_id: str,
    extra: Dict[str, Any] | None = None,
    now: _dt.datetime | None = None,
) -> None:
    now = now or _utc_now()
    record.status = Status.TRACKED
    record.remote_tracked = True
    record.remote_entity_type = entity_type
    record.remote_api_id = api_id
    record.remote_extra = extra or {}
    record.next_retry_at = None
    record.last_attempt_at = now
    record.last_error = None


def _backoff_for_attempt(attempts: int) -> _dt.timedelta:
    # Simple stepped backoff: 15m, 1h, 6h, 24h, then 24h cap.
    if attempts <= 1:
        return _dt.timedelta(minutes=15)
    if attempts == 2:
        return _dt.timedelta(hours=1)
    if attempts == 3:
        return _dt.timedelta(hours=6)
    return _dt.timedelta(hours=24)


def mark_failed_with_backoff(
    record: BookRecord,
    *,
    error: str,
    max_attempts: int | None = None,
    now: _dt.datetime | None = None,
) -> None:
    now = now or _utc_now()

    record.attempts += 1
    record.last_error = error
    record.last_attempt_at = now

    if max_attempts is not None and record.attempts >= max_attempts:
        record.status = Status.FAILED
        record.next_retry_at = None
        return

    record.status = Status.FAILED
    record.next_retry_at = now + _backoff_for_attempt(record.attempts)


def list_pending_summary(
    state: State,
    *,
    year: int | None = None,
    now: _dt.datetime | None = None,
) -> Iterable[Tuple[str, BookRecord]]:
    now = now or _utc_now()

    for key, payload in state.items():
        record = BookRecord.from_state(key, payload)
        if year is not None and record.source_year != year:
            continue
        if record.status == Status.TRACKED:
            continue
        if record.next_retry_at is not None and record.next_retry_at > now:
            continue
        yield key, record


def list_by_status(
    state: State,
    *,
    status: Status | str | None = None,
    year: int | None = None,
) -> Iterable[Tuple[str, BookRecord]]:
    """
    List books filtered by status and optionally by year.

    Args:
        state: The tracking state dictionary
        status: Filter by status (pending, in_progress, tracked, failed). If None, shows all.
        year: Filter by source year. If None, shows all years.

    Yields:
        Tuples of (key, BookRecord) matching the filters.
    """
    status_value = status.value if isinstance(status, Status) else status

    for key, payload in state.items():
        record = BookRecord.from_state(key, payload)
        if year is not None and record.source_year != year:
            continue
        if status_value is not None and record.status.value != status_value:
            continue
        yield key, record


def reset_record(record: BookRecord) -> None:
    record.status = Status.PENDING
    record.attempts = 0
    record.last_attempt_at = None
    record.next_retry_at = None
    record.last_error = None
