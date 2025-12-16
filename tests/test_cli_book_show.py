from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from books_we_love.cli import build_parser, main


class TestBookShowCommand:
    """Tests for the book show command."""

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
            },
            "2023:2": {
                "source_year": 2023,
                "local_id": 2,
                "title": "Another Book",
                "author": "Another Author",
                "status": "tracked",
                "attempts": 1,
            },
        }

    def test_book_show_with_year_and_id(self, sample_state, capsys):
        """Test book show with year and id."""
        parser = build_parser()
        args = parser.parse_args(["book", "show", "--year", "2023", "--id", "1"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch("books_we_love.cli.book.utils.find_book_by_key") as mock_find:
                mock_find.return_value = ("2023:1", sample_state["2023:1"])
                from books_we_love.cli import book

                book.handle_book_show(args)

                captured = capsys.readouterr()
                output = json.loads(captured.out)
                assert output["source_year"] == 2023
                assert output["local_id"] == 1
                assert output["title"] == "Test Book"

    def test_book_show_not_found(self, sample_state, capsys):
        """Test book show when book is not found."""
        parser = build_parser()
        args = parser.parse_args(["book", "show", "--year", "2023", "--id", "999"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch("books_we_love.cli.book.utils.find_book_by_key") as mock_find:
                mock_find.return_value = None
                from books_we_love.cli import book

                book.handle_book_show(args)

                captured = capsys.readouterr()
                assert "No datastore record found" in captured.out

    def test_book_show_missing_args(self, sample_state, capsys):
        """Test book show with missing year or id."""
        parser = build_parser()
        args = parser.parse_args(["book", "show", "--year", "2023"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            from books_we_love.cli import book

            book.handle_book_show(args)

            captured = capsys.readouterr()
            assert (
                "Error: must supply either --year and --id, or --jsonpath"
                in captured.out
            )

    def test_book_show_with_jsonpath_single_match(self, sample_state, capsys):
        """Test book show with JSONPath expression (single match)."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "show", "--jsonpath", "$[?(@.local_id == 1)]"]
        )

        records = [
            {
                "_key": "2023:1",
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
            },
            {
                "_key": "2023:2",
                "source_year": 2023,
                "local_id": 2,
                "title": "Another Book",
            },
        ]

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list", return_value=records
            ):
                with patch(
                    "books_we_love.cli.book.utils.filter_by_jsonpath"
                ) as mock_filter:
                    mock_filter.return_value = [records[0]]
                    from books_we_love.cli import book

                    book.handle_book_show(args)

                    captured = capsys.readouterr()
                    output = json.loads(captured.out)
                    assert output["local_id"] == 1

    def test_book_show_with_jsonpath_multiple_matches(self, sample_state, capsys):
        """Test book show with JSONPath expression (multiple matches)."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "show", "--jsonpath", "$[?(@.source_year == 2023)]"]
        )

        records = [
            {
                "_key": "2023:1",
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
            },
            {
                "_key": "2023:2",
                "source_year": 2023,
                "local_id": 2,
                "title": "Another Book",
            },
        ]

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list", return_value=records
            ):
                with patch(
                    "books_we_love.cli.book.utils.filter_by_jsonpath"
                ) as mock_filter:
                    mock_filter.return_value = records
                    from books_we_love.cli import book

                    book.handle_book_show(args)

                    captured = capsys.readouterr()
                    import json

                    output_data = json.loads(captured.out)
                    assert len(output_data) == 2
                    titles = [r["title"] for r in output_data]
                    assert "Test Book" in titles
                    assert "Another Book" in titles

    def test_book_show_with_jsonpath_no_matches(self, sample_state, capsys):
        """Test book show with JSONPath expression (no matches)."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "show", "--jsonpath", "$[?(@.local_id == 999)]"]
        )

        records = [
            {
                "_key": "2023:1",
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
            },
        ]

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.utils.state_as_list", return_value=records
            ):
                with patch(
                    "books_we_love.cli.book.utils.filter_by_jsonpath"
                ) as mock_filter:
                    mock_filter.return_value = []
                    from books_we_love.cli import book

                    book.handle_book_show(args)

                    captured = capsys.readouterr()
                    assert "No matching records found" in captured.out

    def test_book_show_main_entry_point(self, sample_state, capsys):
        """Test book show through main entry point."""
        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch("books_we_love.cli.book.utils.find_book_by_key") as mock_find:
                mock_find.return_value = ("2023:1", sample_state["2023:1"])
                with patch(
                    "sys.argv",
                    ["books-we-love", "book", "show", "--year", "2023", "--id", "1"],
                ):
                    from books_we_love.cli import main
                    import sys

                    main()

                    captured = capsys.readouterr()
                    output = json.loads(captured.out)
                    assert output["local_id"] == 1
