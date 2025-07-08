"""Parsers for different issue body formats."""

from .json_parser import JsonParser
from .table_parser import TableParser

__all__ = ["JsonParser", "TableParser"] 