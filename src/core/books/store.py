"""In-memory book storage."""

import uuid
from dataclasses import dataclass
from typing import Optional

from src.api.schemas.books import Book, Chapter, ChapterStatus


@dataclass
class ChapterAudio:
    """Stored audio data with timing information."""
    audio_bytes: bytes
    duration_ms: float
    timings: list[dict]  # List of {word, start_ms, end_ms, char_start, char_end}


class BookStore:
    """Simple in-memory store for books and chapters."""

    def __init__(self) -> None:
        self._books: dict[str, Book] = {}
        self._audio_data: dict[str, ChapterAudio] = {}  # chapter_id -> audio with timing

    def add_book(self, book: Book) -> Book:
        """Add a book to the store."""
        if not book.id:
            book.id = str(uuid.uuid4())[:8]
        self._books[book.id] = book
        return book

    def get_book(self, book_id: str) -> Optional[Book]:
        """Get a book by ID."""
        return self._books.get(book_id)

    def list_books(self) -> list[Book]:
        """List all books."""
        return list(self._books.values())

    def delete_book(self, book_id: str) -> bool:
        """Delete a book and its audio data."""
        if book_id not in self._books:
            return False
        book = self._books[book_id]
        # Clean up audio data
        for chapter in book.chapters:
            self._audio_data.pop(chapter.id, None)
        del self._books[book_id]
        return True

    def get_chapter(self, book_id: str, chapter_id: str) -> Optional[Chapter]:
        """Get a specific chapter."""
        book = self.get_book(book_id)
        if not book:
            return None
        for chapter in book.chapters:
            if chapter.id == chapter_id:
                return chapter
        return None

    def update_chapter_status(
        self, book_id: str, chapter_id: str, status: ChapterStatus, audio_url: str | None = None
    ) -> bool:
        """Update a chapter's audio status."""
        book = self.get_book(book_id)
        if not book:
            return False
        for chapter in book.chapters:
            if chapter.id == chapter_id:
                chapter.audio_status = status
                if audio_url:
                    chapter.audio_url = audio_url
                return True
        return False

    def store_audio(
        self,
        chapter_id: str,
        audio_bytes: bytes,
        duration_ms: float,
        timings: list[dict],
    ) -> None:
        """Store audio data with timing for a chapter."""
        self._audio_data[chapter_id] = ChapterAudio(
            audio_bytes=audio_bytes,
            duration_ms=duration_ms,
            timings=timings,
        )

    def get_audio(self, chapter_id: str) -> Optional[ChapterAudio]:
        """Get audio data with timing for a chapter."""
        return self._audio_data.get(chapter_id)


# Singleton instance
_store: BookStore | None = None


def get_book_store() -> BookStore:
    """Get or create the book store singleton."""
    global _store
    if _store is None:
        _store = BookStore()
    return _store
