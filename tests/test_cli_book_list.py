from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from books_we_love.cli import build_parser, main


class TestBookListCommand:
    """Tests for the book list command."""

    @pytest.fixture
    def sample_state(self):
        """Sample datastore state for testing."""
        return {
            "2023:1": {
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "status": "pending",
                "attempts": 0,
                "next_retry_at": None,
            },
            "2023:2": {
                "source_year": 2023,
                "local_id": 2,
                "title": "Another Book",
                "author": "Another Author",
                "status": "tracked",
                "attempts": 1,
                "next_retry_at": None,
            },
            "2024:1": {
                "source_year": 2024,
                "local_id": 1,
                "title": "Year 2024 Book",
                "author": "Year 2024 Author",
                "status": "failed",
                "attempts": 2,
                "next_retry_at": "2024-01-01T00:00:00",
            },
            "2024:2": {
                "source_year": 2024,
                "local_id": 2,
                "title": "Year 2024 Book 2",
                "author": "Year 2024 Author 2",
                "status": "pending",
                "attempts": 0,
                "next_retry_at": None,
            },
        }

    @pytest.fixture
    def sample_records(self):
        """Sample records list for testing."""
        return [
            {
                "_key": "2023:1",
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "status": "pending",
                "attempts": 0,
                "next_retry_at": None,
            },
            {
                "_key": "2023:2",
                "source_year": 2023,
                "local_id": 2,
                "title": "Another Book",
                "author": "Another Author",
                "status": "tracked",
                "attempts": 1,
                "next_retry_at": None,
            },
            {
                "_key": "2024:1",
                "source_year": 2024,
                "local_id": 1,
                "title": "Year 2024 Book",
                "author": "Year 2024 Author",
                "status": "failed",
                "attempts": 2,
                "next_retry_at": "2024-01-01T00:00:00",
            },
            {
                "_key": "2024:2",
                "source_year": 2024,
                "local_id": 2,
                "title": "Year 2024 Book 2",
                "author": "Year 2024 Author 2",
                "status": "pending",
                "attempts": 0,
                "next_retry_at": None,
            },
        ]

    def test_books_list_no_filters(self, sample_state, sample_records, capsys):
        """Test book list without any filters."""
        parser = build_parser()
        args = parser.parse_args(["book", "list"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                from books_we_love.cli import book

                book.handle_book_list(args)

                captured = capsys.readouterr()
                output_data = json.loads(captured.out)
                # Check that results are sorted: year descending, then id descending
                # Expected order: 2024:2, 2024:1, 2023:2, 2023:1
                assert len(output_data) == 4
                assert output_data[0]["_key"] == "2024:2"
                assert output_data[1]["_key"] == "2024:1"
                assert output_data[2]["_key"] == "2023:2"
                assert output_data[3]["_key"] == "2023:1"

    def test_books_list_with_status_filter(self, sample_state, sample_records, capsys):
        """Test book list filtered by status."""
        parser = build_parser()
        args = parser.parse_args(["book", "list", "--status", "pending"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                from books_we_love.cli import book

                book.handle_book_list(args)

                captured = capsys.readouterr()
                output_data = json.loads(captured.out)
                # Should have 2024:2 and 2023:1, sorted by year descending then id descending
                assert len(output_data) == 2
                assert output_data[0]["_key"] == "2024:2"
                assert output_data[1]["_key"] == "2023:1"
                assert all(r["status"] == "pending" for r in output_data)
                assert not any(r["_key"] == "2023:2" for r in output_data)
                assert not any(r["_key"] == "2024:1" for r in output_data)

    def test_books_list_with_year_filter(self, sample_state, sample_records, capsys):
        """Test book list filtered by year."""
        parser = build_parser()
        args = parser.parse_args(["book", "list", "--year", "2023"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                from books_we_love.cli import book

                book.handle_book_list(args)

                captured = capsys.readouterr()
                output_data = json.loads(captured.out)
                # Should have 2023:2 and 2023:1, sorted by id descending
                assert len(output_data) == 2
                assert output_data[0]["_key"] == "2023:2"
                assert output_data[1]["_key"] == "2023:1"
                assert all(r["source_year"] == 2023 for r in output_data)
                assert not any(r["source_year"] == 2024 for r in output_data)

    def test_books_list_with_status_and_year(
        self, sample_state, sample_records, capsys
    ):
        """Test book list filtered by both status and year."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "list", "--status", "tracked", "--year", "2023"]
        )

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                from books_we_love.cli import book

                book.handle_book_list(args)

                captured = capsys.readouterr()
                output_data = json.loads(captured.out)
                assert len(output_data) == 1
                assert output_data[0]["_key"] == "2023:2"
                assert output_data[0]["status"] == "tracked"

    def test_books_list_with_jsonpath(self, sample_state, sample_records, capsys):
        """Test book list with JSONPath expression."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "list", "--jsonpath", "$[?(@.status == 'failed')]"]
        )

        filtered_records = [sample_records[2]]  # Only the failed one

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                with patch(
                    "books_we_love.cli.book.utils.filter_by_jsonpath",
                    return_value=filtered_records,
                ):
                    from books_we_love.cli import book

                    book.handle_book_list(args)

                    captured = capsys.readouterr()
                    output_data = json.loads(captured.out)
                    assert len(output_data) == 1
                    assert output_data[0]["_key"] == "2024:1"
                    assert output_data[0]["status"] == "failed"

    def test_books_list_with_jsonpath_ignores_status_and_year(
        self, sample_state, sample_records, capsys
    ):
        """Test that JSONPath overrides status and year filters."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "book",
                "list",
                "--jsonpath",
                "$[?(@.local_id == 1)]",
                "--status",
                "tracked",
                "--year",
                "2024",
            ]
        )

        filtered_records = [
            sample_records[0],
            sample_records[2],
        ]  # Both with local_id == 1

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                with patch(
                    "books_we_love.cli.book.utils.filter_by_jsonpath",
                    return_value=filtered_records,
                ):
                    from books_we_love.cli import book

                    book.handle_book_list(args)

                    captured = capsys.readouterr()
                    output_data = json.loads(captured.out)
                    # Should match both 2023:1 and 2024:1, sorted by year descending then id descending
                    assert len(output_data) == 2
                    assert output_data[0]["_key"] == "2024:1"  # 2024 before 2023
                    assert output_data[1]["_key"] == "2023:1"

    def test_books_list_with_jsonpath_simple_filter(
        self, sample_state, sample_records, capsys
    ):
        """Test book list with simple JSONPath filter."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "list", "--jsonpath", "$[?(@.source_year == 2024)]"]
        )

        filtered_records = [sample_records[2], sample_records[3]]  # Both 2024 records

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                with patch(
                    "books_we_love.cli.book.utils.filter_by_jsonpath",
                    return_value=filtered_records,
                ):
                    from books_we_love.cli import book

                    book.handle_book_list(args)

                    captured = capsys.readouterr()
                    output_data = json.loads(captured.out)
                    # Should have both 2024 records, sorted by id descending
                    assert len(output_data) == 2
                    assert output_data[0]["_key"] == "2024:2"
                    assert output_data[1]["_key"] == "2024:1"
                    assert all(r["source_year"] == 2024 for r in output_data)
                    assert not any(r["source_year"] == 2023 for r in output_data)

    def test_books_list_empty_results(self, sample_state, capsys):
        """Test book list with filters that match nothing."""
        parser = build_parser()
        args = parser.parse_args(["book", "list", "--status", "in_progress"])

        empty_records = []
        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list", return_value=empty_records
            ):
                from books_we_love.cli import book

                book.handle_book_list(args)

                captured = capsys.readouterr()
                output_data = json.loads(captured.out)
                assert output_data == []

    def test_books_list_main_entry_point(self, sample_state, sample_records, capsys):
        """Test book list through main entry point."""
        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                with patch(
                    "sys.argv", ["books-we-love", "book", "list", "--status", "pending"]
                ):
                    from books_we_love.cli import main
                    import sys

                    main()

                    captured = capsys.readouterr()
                    output_data = json.loads(captured.out)
                    # Should have 2024:2 and 2023:1, sorted by year descending then id descending
                    assert len(output_data) == 2
                    assert output_data[0]["_key"] == "2024:2"
                    assert output_data[1]["_key"] == "2023:1"
                    assert all(r["status"] == "pending" for r in output_data)

    def test_books_list_sort_order(self, sample_state, sample_records, capsys):
        """Test that book list sorts by year descending, then id descending."""
        parser = build_parser()
        args = parser.parse_args(["book", "list"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list",
                return_value=sample_records,
            ):
                from books_we_love.cli import book

                book.handle_book_list(args)

                captured = capsys.readouterr()
                output_data = json.loads(captured.out)
                # Verify exact sort order: year descending, then id descending
                # Expected: 2024:2, 2024:1, 2023:2, 2023:1
                assert len(output_data) == 4
                assert output_data[0]["_key"] == "2024:2"
                assert output_data[1]["_key"] == "2024:1"
                assert output_data[2]["_key"] == "2023:2"
                assert output_data[3]["_key"] == "2023:1"
