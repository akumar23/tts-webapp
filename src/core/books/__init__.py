"""Book management module."""

from src.core.books.store import BookStore, get_book_store
from src.core.books.gutenberg import GutenbergClient
from src.core.books.parser import ChapterParser

__all__ = ["BookStore", "get_book_store", "GutenbergClient", "ChapterParser"]
