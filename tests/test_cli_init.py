from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from books_we_love.cli import build_parser, main


class TestInitCommand:
    """Tests for the init command."""

    @pytest.fixture
    def sample_book_data(self):
        """Sample book data from JSON file."""
        return [
            {
                "id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "cover": "1234567890",
            },
            {
                "id": 2,
                "title": "Another Book",
                "author": "Another Author",
                "cover": "0987654321",
            },
        ]

    def test_init_with_year(self, sample_book_data, capsys):
        """Test init command with a specific year."""
        parser = build_parser()
        args = parser.parse_args(["init", "--year", "2023"])

        mock_state = {}
        with patch("books_we_love.cli.init.seed_books") as mock_seed:
            with patch(
                "books_we_love.cli.init.datastore.load_state", return_value=mock_state
            ):
                with patch(
                    "books_we_love.cli.init.datastore.save_state_atomic"
                ) as mock_save:
                    with patch(
                        "books_we_love.cli.init.datastore.ensure_book_entry"
                    ) as mock_ensure:
                        with patch("pathlib.Path.exists", return_value=True):
                            with patch("pathlib.Path.open", create=True) as mock_open:
                                import io

                                mock_file = MagicMock()
                                mock_file.__enter__ = MagicMock(
                                    return_value=io.StringIO("[]")
                                )
                                mock_file.__exit__ = MagicMock(return_value=None)
                                mock_open.return_value = mock_file

                                # Mock json.load to return sample data
                                with patch(
                                    "books_we_love.cli.init.json.load",
                                    return_value=sample_book_data,
                                ):
                                    from books_we_love.cli import init

                                    init.handle_init(args)

                                    mock_seed.assert_called_once_with(year=2023)
                                    assert mock_ensure.call_count == 2
                                    mock_save.assert_called_once()

                                    captured = capsys.readouterr()
                                    import json

                                    output_data = json.loads(captured.out)
                                    assert output_data["total_books"] == 2
                                    assert 2023 in output_data["years_processed"]

    def test_init_without_year(self, sample_book_data, capsys):
        """Test init command without year (downloads all years)."""
        parser = build_parser()
        args = parser.parse_args(["init"])

        mock_state = {}
        with patch("books_we_love.cli.init.seed_books") as mock_seed:
            with patch(
                "books_we_love.cli.init.datastore.load_state", return_value=mock_state
            ):
                with patch(
                    "books_we_love.cli.init.datastore.save_state_atomic"
                ) as mock_save:
                    with patch(
                        "books_we_love.cli.init.datastore.ensure_book_entry"
                    ) as mock_ensure:
                        with patch(
                            "books_we_love.cli.init._target_years",
                            return_value=[2023, 2024],
                        ):
                            with patch("pathlib.Path.exists", return_value=True):
                                with patch(
                                    "pathlib.Path.open", create=True
                                ) as mock_open:
                                    import io

                                    mock_file = MagicMock()
                                    mock_file.__enter__ = MagicMock(
                                        return_value=io.StringIO("[]")
                                    )
                                    mock_file.__exit__ = MagicMock(return_value=None)
                                    mock_open.return_value = mock_file

                                    with patch(
                                        "books_we_love.cli.init.json.load",
                                        return_value=sample_book_data,
                                    ):
                                        from books_we_love.cli import init

                                        init.handle_init(args)

                                        mock_seed.assert_called_once_with(year=None)
                                        # Should be called for each book in each year
                                        assert mock_ensure.call_count == 4
                                        mock_save.assert_called_once()

    def test_init_main_entry_point(self, sample_book_data, capsys):
        """Test init command through main entry point."""
        mock_state = {}
        with patch("books_we_love.cli.init.seed_books") as mock_seed:
            with patch(
                "books_we_love.cli.init.datastore.load_state", return_value=mock_state
            ):
                with patch(
                    "books_we_love.cli.init.datastore.save_state_atomic"
                ) as mock_save:
                    with patch(
                        "books_we_love.cli.init.datastore.ensure_book_entry"
                    ) as mock_ensure:
                        with patch("pathlib.Path.exists", return_value=True):
                            with patch("pathlib.Path.open", create=True) as mock_open:
                                import io

                                mock_file = MagicMock()
                                mock_file.__enter__ = MagicMock(
                                    return_value=io.StringIO("[]")
                                )
                                mock_file.__exit__ = MagicMock(return_value=None)
                                mock_open.return_value = mock_file

                                with patch(
                                    "books_we_love.cli.init.json.load",
                                    return_value=sample_book_data,
                                ):
                                    with patch(
                                        "sys.argv",
                                        ["books-we-love", "init", "--year", "2024"],
                                    ):
                                        from books_we_love.cli import main
                                        import sys

                                        main()

                                        mock_seed.assert_called_once_with(year=2024)
                                        assert mock_ensure.call_count == 2
                                        mock_save.assert_called_once()

    def test_init_no_books_found(self, capsys):
        """Test init when no books are found in JSON files."""
        parser = build_parser()
        args = parser.parse_args(["init", "--year", "2023"])

        mock_state = {}
        with patch("books_we_love.cli.init.seed_books") as mock_seed:
            with patch(
                "books_we_love.cli.init.datastore.load_state", return_value=mock_state
            ):
                with patch(
                    "books_we_love.cli.init.datastore.save_state_atomic"
                ) as mock_save:
                    with patch("pathlib.Path.exists", return_value=False):
                        from books_we_love.cli import init

                        init.handle_init(args)

                        mock_seed.assert_called_once_with(year=2023)
                        mock_save.assert_not_called()

                        captured = capsys.readouterr()
                        assert "Populated datastore" not in captured.out
