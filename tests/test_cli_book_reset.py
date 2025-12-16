from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from books_we_love.cli import build_parser, main
from books_we_love.datastore import BookRecord, Status


class TestBookResetCommand:
    """Tests for the book reset command."""

    @pytest.fixture
    def sample_state(self):
        """Sample datastore state for testing."""
        return {
            "2023:1": {
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "status": "failed",
                "attempts": 3,
                "last_error": "not found",
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

    def test_book_reset_with_year_and_id(self, sample_state, capsys):
        """Test book reset with year and id."""
        parser = build_parser()
        args = parser.parse_args(["book", "reset", "--year", "2023", "--id", "1"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.datastore.save_state_atomic"
            ) as mock_save:
                with patch(
                    "books_we_love.cli.book.utils.find_book_by_key"
                ) as mock_find:
                    mock_find.return_value = ("2023:1", sample_state["2023:1"])
                    from books_we_love.cli import book

                    book.handle_book_reset(args)

                    mock_save.assert_called_once()
                    captured = capsys.readouterr()
                    import json

                    output_data = json.loads(captured.out)
                    assert output_data["count"] == 1
                    assert "2023:1" in output_data["keys"]

                    # Verify the record was reset
                    saved_state = mock_save.call_args[0][0]
                    record = BookRecord.from_state("2023:1", saved_state["2023:1"])
                    assert record.status == Status.PENDING
                    assert record.attempts == 0
                    assert record.last_error is None

    def test_book_reset_not_found(self, sample_state, capsys):
        """Test book reset when book is not found."""
        parser = build_parser()
        args = parser.parse_args(["book", "reset", "--year", "2023", "--id", "999"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch("books_we_love.cli.book.utils.find_book_by_key") as mock_find:
                mock_find.return_value = None
                from books_we_love.cli import book

                book.handle_book_reset(args)

                captured = capsys.readouterr()
                assert "No datastore record found" in captured.out

    def test_book_reset_missing_args(self, sample_state, capsys):
        """Test book reset with missing year or id."""
        parser = build_parser()
        args = parser.parse_args(["book", "reset", "--year", "2023"])

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            from books_we_love.cli import book

            book.handle_book_reset(args)

            captured = capsys.readouterr()
            assert (
                "Error: must supply either --year and --id, or --jsonpath"
                in captured.out
            )

    def test_book_reset_with_jsonpath_single_match(self, sample_state, capsys):
        """Test book reset with JSONPath expression (single match)."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "reset", "--jsonpath", "$[?(@.local_id == 1)]"]
        )

        records = [
            {
                "_key": "2023:1",
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
                "status": "failed",
            },
        ]

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.datastore.save_state_atomic"
            ) as mock_save:
                with patch(
                    "books_we_love.cli.book.utils.state_as_list", return_value=records
                ):
                    with patch(
                        "books_we_love.cli.book.utils.find_books_by_jsonpath"
                    ) as mock_find:
                        mock_find.return_value = [("2023:1", sample_state["2023:1"])]
                        from books_we_love.cli import book

                        book.handle_book_reset(args)

                        mock_save.assert_called_once()
                        captured = capsys.readouterr()
                        import json

                        output_data = json.loads(captured.out)
                        assert output_data["count"] == 1
                        assert "2023:1" in output_data["keys"]

    def test_book_reset_with_jsonpath_multiple_matches(self, sample_state, capsys):
        """Test book reset with JSONPath expression (multiple matches)."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "reset", "--jsonpath", "$[?(@.status == 'failed')]"]
        )

        records = [
            {
                "_key": "2023:1",
                "source_year": 2023,
                "local_id": 1,
                "title": "Test Book",
                "status": "failed",
            },
            {
                "_key": "2024:1",
                "source_year": 2024,
                "local_id": 1,
                "title": "Other Book",
                "status": "failed",
            },
        ]

        extended_state = sample_state.copy()
        extended_state["2024:1"] = {
            "source_year": 2024,
            "local_id": 1,
            "title": "Other Book",
            "author": "Other Author",
            "status": "failed",
            "attempts": 2,
        }

        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=extended_state
        ):
            with patch(
                "books_we_love.cli.book.datastore.save_state_atomic"
            ) as mock_save:
                with patch(
                    "books_we_love.cli.book.utils.state_as_list", return_value=records
                ):
                    with patch(
                        "books_we_love.cli.book.utils.find_books_by_jsonpath"
                    ) as mock_find:
                        mock_find.return_value = [
                            ("2023:1", extended_state["2023:1"]),
                            ("2024:1", extended_state["2024:1"]),
                        ]
                        from books_we_love.cli import book

                        book.handle_book_reset(args)

                        mock_save.assert_called_once()
                        captured = capsys.readouterr()
                        import json

                        output_data = json.loads(captured.out)
                        assert output_data["count"] == 2
                        assert "2023:1" in output_data["keys"]
                        assert "2024:1" in output_data["keys"]

    def test_book_reset_with_jsonpath_no_matches(self, sample_state, capsys):
        """Test book reset with JSONPath expression (no matches)."""
        parser = build_parser()
        args = parser.parse_args(
            ["book", "reset", "--jsonpath", "$[?(@.local_id == 999)]"]
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
                    "books_we_love.cli.book.utils.find_books_by_jsonpath"
                ) as mock_find:
                    mock_find.return_value = []
                    from books_we_love.cli import book

                    book.handle_book_reset(args)

                    captured = capsys.readouterr()
                    assert "No matching records found" in captured.out

    def test_book_reset_main_entry_point(self, sample_state, capsys):
        """Test book reset through main entry point."""
        with patch(
            "books_we_love.cli.book.datastore.load_state", return_value=sample_state
        ):
            with patch(
                "books_we_love.cli.book.datastore.save_state_atomic"
            ) as mock_save:
                with patch(
                    "books_we_love.cli.book.utils.find_book_by_key"
                ) as mock_find:
                    mock_find.return_value = ("2023:1", sample_state["2023:1"])
                    with patch(
                        "sys.argv",
                        [
                            "books-we-love",
                            "book",
                            "reset",
                            "--year",
                            "2023",
                            "--id",
                            "1",
                        ],
                    ):
                        from books_we_love.cli import main
                        import sys

                        main()

                        mock_save.assert_called_once()
                        captured = capsys.readouterr()
                        import json

                        output_data = json.loads(captured.out)
                        assert output_data["count"] == 1
                        assert "2023:1" in output_data["keys"]
