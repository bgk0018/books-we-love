from __future__ import annotations

from unittest.mock import patch

import pytest

from books_we_love.cli import build_parser, main


class TestAcquireCommand:
    """Tests for the book acquire command."""

    def test_acquire_default_args(self):
        """Test book acquire command with default arguments."""
        parser = build_parser()
        args = parser.parse_args(["book", "acquire"])

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=None,
                status=None,
                book_id=None,
                limit=10,
                max_attempts=5,
                dry_run=False,
                output_format="json",
            )

    def test_acquire_with_year(self):
        """Test book acquire command with year specified."""
        parser = build_parser()
        args = parser.parse_args(["book", "acquire", "--year", "2023"])

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=2023,
                status=None,
                book_id=None,
                limit=10,
                max_attempts=5,
                dry_run=False,
                output_format="json",
            )

    def test_acquire_with_limit(self):
        """Test book acquire command with custom limit."""
        parser = build_parser()
        args = parser.parse_args(["book", "acquire", "--limit", "20"])

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=None,
                status=None,
                book_id=None,
                limit=20,
                max_attempts=5,
                dry_run=False,
                output_format="json",
            )

    def test_acquire_with_max_attempts(self):
        """Test book acquire command with custom max attempts."""
        parser = build_parser()
        args = parser.parse_args(["book", "acquire", "--max-attempts", "10"])

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=None,
                status=None,
                book_id=None,
                limit=10,
                max_attempts=10,
                dry_run=False,
                output_format="json",
            )

    def test_acquire_with_dry_run(self):
        """Test book acquire command with dry run flag."""
        parser = build_parser()
        args = parser.parse_args(["book", "acquire", "--dry-run"])

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=None,
                status=None,
                book_id=None,
                limit=10,
                max_attempts=5,
                dry_run=True,
                output_format="json",
            )

    def test_acquire_all_options(self):
        """Test book acquire command with all options specified."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "book",
                "acquire",
                "--year",
                "2022",
                "--limit",
                "5",
                "--max-attempts",
                "3",
                "--dry-run",
            ]
        )

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=2022,
                status=None,
                book_id=None,
                limit=5,
                max_attempts=3,
                dry_run=True,
                output_format="json",
            )

    def test_acquire_with_status(self):
        """Test book acquire command with status specified."""
        parser = build_parser()
        args = parser.parse_args(["book", "acquire", "--status", "pending"])

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=None,
                status="pending",
                book_id=None,
                limit=10,
                max_attempts=5,
                dry_run=False,
                output_format="json",
            )

    def test_acquire_with_year_and_status(self):
        """Test book acquire command with both year and status specified."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "acquire", "--year", "2023", "--status", "failed"]
        )

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=2023,
                status="failed",
                book_id=None,
                limit=10,
                max_attempts=5,
                dry_run=False,
                output_format="json",
            )

    def test_acquire_with_all_filters(self):
        """Test book acquire command with year, status, and other options."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "book",
                "acquire",
                "--year",
                "2022",
                "--status",
                "pending",
                "--limit",
                "5",
                "--max-attempts",
                "3",
                "--dry-run",
            ]
        )

        with patch("books_we_love.cli.book.track_books") as mock_track:
            from books_we_love.cli import book

            book.handle_book_acquire(args)
            mock_track.assert_called_once_with(
                year=2022,
                status="pending",
                book_id=None,
                limit=5,
                max_attempts=3,
                dry_run=True,
                output_format="json",
            )

    def test_acquire_main_entry_point(self):
        """Test book acquire command through main entry point."""
        with patch("books_we_love.cli.book.track_books") as mock_track:
            with patch(
                "sys.argv",
                ["books-we-love", "book", "acquire", "--year", "2023", "--limit", "15"],
            ):
                from books_we_love.cli import main
                import sys

                main()
                mock_track.assert_called_once_with(
                    year=2023,
                    status=None,
                    book_id=None,
                    limit=15,
                    max_attempts=5,
                    dry_run=False,
                    output_format="json",
                )
