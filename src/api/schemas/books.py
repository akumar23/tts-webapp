"""Book and chapter schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class BookSource(str, Enum):
    """Source of the book."""
    GUTENBERG = "gutenberg"
    UPLOAD = "upload"


class ChapterStatus(str, Enum):
    """Audio generation status for a chapter."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Chapter(BaseModel):
    """A chapter within a book."""
    id: str = Field(description="Unique chapter identifier")
    number: int = Field(description="Chapter number (1-indexed)")
    title: str = Field(description="Chapter title")
    text: str = Field(description="Full chapter text")
    word_count: int = Field(description="Number of words in chapter")
    audio_status: ChapterStatus = Field(default=ChapterStatus.PENDING)
    audio_url: Optional[str] = Field(default=None, description="URL to generated audio")


class ChapterSummary(BaseModel):
    """Chapter summary without full text."""
    id: str
    number: int
    title: str
    word_count: int
    audio_status: ChapterStatus
    audio_url: Optional[str] = None


class Book(BaseModel):
    """A book with chapters."""
    id: str = Field(description="Unique book identifier")
    title: str = Field(description="Book title")
    author: str = Field(description="Book author")
    source: BookSource = Field(description="Where the book came from")
    source_id: Optional[str] = Field(default=None, description="ID from source (e.g., Gutenberg ID)")
    language: str = Field(default="en", description="Book language code")
    chapters: list[Chapter] = Field(default_factory=list)
    total_words: int = Field(default=0, description="Total word count")


class BookSummary(BaseModel):
    """Book summary without chapter text."""
    id: str
    title: str
    author: str
    source: BookSource
    language: str
    chapter_count: int
    total_words: int


class GutenbergSearchResult(BaseModel):
    """Search result from Project Gutenberg."""
    id: str = Field(description="Gutenberg book ID")
    title: str
    author: str
    language: str
    subjects: list[str] = Field(default_factory=list)
    download_count: Optional[int] = None


class UploadBookRequest(BaseModel):
    """Request to upload custom book text."""
    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(default="Unknown")
    text: str = Field(..., min_length=1, description="Full book text to parse into chapters")
    language: str = Field(default="en")


class SynthesizeChapterRequest(BaseModel):
    """Request to synthesize a chapter to audio."""
    voice: Optional[str] = Field(default=None, description="Voice ID to use")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    provider: str = Field(default="edge")


class WordTimingResponse(BaseModel):
    """Word timing for karaoke-style highlighting."""
    word: str
    start_ms: float = Field(description="Start time in milliseconds")
    end_ms: float = Field(description="End time in milliseconds")
    char_start: int = Field(description="Character start position in text")
    char_end: int = Field(description="Character end position in text")


class ChapterAudioResponse(BaseModel):
    """Response with audio URL and timing data for a chapter."""
    chapter_id: str
    audio_url: str
    duration_ms: float
    word_count: int
    timings: list[WordTimingResponse] = Field(description="Word-level timing for highlighting")
