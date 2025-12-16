from __future__ import annotations

import json
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table


class OutputFormat(str, Enum):
    """Output format options."""

    JSON = "json"
    TABLE = "table"
    LIST = "list"


def format_output(data: Any, output_format: str = "json") -> None:
    """Format and print data according to the specified output format."""
    format_enum = OutputFormat(output_format.lower())

    if format_enum == OutputFormat.JSON:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif format_enum == OutputFormat.TABLE:
        _format_table(data)
    elif format_enum == OutputFormat.LIST:
        _format_list(data)


def _format_table(data: Any) -> None:
    """Format data as a rich table."""
    console = Console()

    if isinstance(data, list):
        if not data:
            print("[]")
            return

        # Determine columns from first item
        if isinstance(data[0], dict):
            columns = list(data[0].keys())
            table = Table(show_header=True, header_style="bold magenta")
            for col in columns:
                table.add_column(col)

            for item in data:
                row = [str(item.get(col, "")) for col in columns]
                table.add_row(*row)
            console.print(table)
        else:
            # Simple list of primitives
            table = Table(show_header=False)
            table.add_column("Value")
            for item in data:
                table.add_row(str(item))
            console.print(table)
    elif isinstance(data, dict):
        # Single object - show as key-value table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Property")
        table.add_column("Value")
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                value_str = str(value)
            table.add_row(key, value_str)
        console.print(table)
    else:
        # Primitive value
        print(str(data))


def _format_list(data: Any) -> None:
    """Format data as a rich list."""
    console = Console()

    if isinstance(data, list):
        if not data:
            print("[]")
            return

        for item in data:
            if isinstance(item, dict):
                # Format dict as key: value pairs
                parts = []
                for key, value in item.items():
                    if isinstance(value, (dict, list)):
                        value_str = json.dumps(value, ensure_ascii=False)
                    else:
                        value_str = str(value)
                    parts.append(f"[bold]{key}[/bold]: {value_str}")
                console.print(" • " + " | ".join(parts))
            else:
                console.print(f" • {item}")
    elif isinstance(data, dict):
        # Single object - show as list of properties
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            console.print(f" • [bold]{key}[/bold]: {value_str}")
    else:
        # Primitive value
        print(str(data))

