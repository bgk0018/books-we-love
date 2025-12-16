"""
CLI tools for downloading NPR 'Books We Love' JSON data and tracking external book/author lookups.
"""

__version__ = "0.1.0"

from .cli import book, init

__all__ = ["book", "init"]