from __future__ import annotations

import argparse

from dotenv import load_dotenv
from . import book, init


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="books-we-love",
        description=(
            "Work with NPR 'Books We Love' data: download JSON and "
            "track external book/author lookups."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Download JSON for one year or all years and store them under ./data",
    )
    init_parser.add_argument(
        "--year",
        type=int,
        help="Year to download (e.g. 2025). If omitted, download all available years.",
    )
    init_parser.add_argument(
        "--output",
        type=str,
        choices=["json", "table", "list"],
        default="json",
        help="Output format (default: json).",
    )

    book_parser = subparsers.add_parser(
        "book",
        help="Operations on books.",
    )
    book_subparsers = book_parser.add_subparsers(dest="book_command", required=True)

    show_book = book_subparsers.add_parser(
        "show",
        help="Show the full datastore record for a single book.",
    )
    show_book.add_argument(
        "--year", type=int, help="Source year (required if not using --jsonpath)."
    )
    show_book.add_argument(
        "--id", type=int, help="Local NPR book id (required if not using --jsonpath)."
    )
    show_book.add_argument(
        "--jsonpath",
        type=str,
        help="JSONPath expression to select book(s). Overrides --year and --id.",
    )
    show_book.add_argument(
        "--output",
        type=str,
        choices=["json", "table", "list"],
        default="json",
        help="Output format (default: json).",
    )

    reset_book = book_subparsers.add_parser(
        "reset",
        help="Reset tracking attempts and status for a single book.",
    )
    reset_book.add_argument(
        "--year", type=int, help="Source year (required if not using --jsonpath)."
    )
    reset_book.add_argument(
        "--id", type=int, help="Local NPR book id (required if not using --jsonpath)."
    )
    reset_book.add_argument(
        "--jsonpath",
        type=str,
        help="JSONPath expression to select book(s). Overrides --year and --id.",
    )
    reset_book.add_argument(
        "--output",
        type=str,
        choices=["json", "table", "list"],
        default="json",
        help="Output format (default: json).",
    )

    list_book = book_subparsers.add_parser(
        "list",
        help="List books filtered by status and optionally by year, or use JSONPath for advanced queries.",
    )
    list_book.add_argument(
        "--status",
        type=str,
        choices=["pending", "in_progress", "tracked", "failed"],
        help="Filter by status. Ignored if --jsonpath is provided.",
    )
    list_book.add_argument(
        "--year",
        type=int,
        help="Limit to books from this year. Ignored if --jsonpath is provided.",
    )
    list_book.add_argument(
        "--jsonpath",
        type=str,
        help="JSONPath expression for advanced filtering. Overrides --status and --year.",
    )
    list_book.add_argument(
        "--output",
        type=str,
        choices=["json", "table", "list"],
        default="json",
        help="Output format (default: json).",
    )

    acquire_book = book_subparsers.add_parser(
        "acquire",
        help="Call a slow external API for local books and maintain datastore state.",
    )
    acquire_book.add_argument(
        "--year",
        type=int,
        help="Only process books from a single year.",
    )
    acquire_book.add_argument(
        "--status",
        type=str,
        choices=["pending", "in_progress", "tracked", "failed"],
        help="Filter by status. Combined with --year as an AND filter.",
    )
    acquire_book.add_argument(
        "--id",
        type=int,
        help="Local NPR book id. If provided, --year is required and only this specific book will be processed.",
    )
    acquire_book.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of books to process in this run (default: 10).",
    )
    acquire_book.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Maximum attempts before giving up on a book (default: 5).",
    )
    acquire_book.add_argument(
        "--dry-run",
        action="store_true",
        help="Populate/refresh datastore but do not call the external API.",
    )
    acquire_book.add_argument(
        "--output",
        type=str,
        choices=["json", "table", "list"],
        default="json",
        help="Output format (default: json).",
    )

    return parser


def main() -> None:
    """Main CLI entry point."""
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    match args.command:
        case "init":
            init.handle_init(args)
            return

        case "book":
            match args.book_command:
                case "show":
                    book.handle_book_show(args)
                    return
                case "reset":
                    book.handle_book_reset(args)
                    return
                case "list":
                    book.handle_book_list(args)
                    return
                case "acquire":
                    book.handle_book_acquire(args)
                    return


if __name__ == "__main__":
    main()
