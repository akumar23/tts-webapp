"""Chapter parsing and text splitting."""

import re
import uuid
from typing import Optional

import structlog

from src.api.schemas.books import Chapter, ChapterStatus

logger = structlog.get_logger(__name__)

# Chapter detection patterns
CHAPTER_PATTERNS = [
    # "CHAPTER I", "CHAPTER 1", "CHAPTER ONE"
    r"^(CHAPTER\s+[IVXLCDM]+\.?)\s*$",
    r"^(CHAPTER\s+\d+\.?)\s*$",
    r"^(CHAPTER\s+(?:ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY)[A-Z\-]*\.?)\s*$",
    # "Chapter I", "Chapter 1"
    r"^(Chapter\s+[IVXLCDM]+\.?)\s*$",
    r"^(Chapter\s+\d+\.?)\s*$",
    r"^(Chapter\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty)[A-Za-z\-]*\.?)\s*$",
    # "I.", "II.", "III." at start of line (Roman numerals)
    r"^([IVXLCDM]+\.)\s*$",
    # "1.", "2." at start of line
    r"^(\d+\.)\s*$",
    # "BOOK I", "BOOK ONE", "Part I"
    r"^(BOOK\s+[IVXLCDM]+\.?)\s*$",
    r"^(BOOK\s+\d+\.?)\s*$",
    r"^(PART\s+[IVXLCDM]+\.?)\s*$",
    r"^(PART\s+\d+\.?)\s*$",
    r"^(Part\s+[IVXLCDM]+\.?)\s*$",
    r"^(Part\s+\d+\.?)\s*$",
]


class ChapterParser:
    """Parses book text into chapters."""

    def __init__(self, min_chapter_words: int = 100, max_chunk_words: int = 5000) -> None:
        """
        Initialize the parser.

        Args:
            min_chapter_words: Minimum words for a valid chapter
            max_chunk_words: Max words per chunk when splitting long chapters
        """
        self.min_chapter_words = min_chapter_words
        self.max_chunk_words = max_chunk_words

    def parse(self, text: str, force_split: bool = False) -> list[Chapter]:
        """
        Parse text into chapters.

        Args:
            text: Full book text
            force_split: If True, split by word count if no chapters found

        Returns:
            List of Chapter objects
        """
        # Try to detect chapters
        chapters = self._detect_chapters(text)

        if not chapters and force_split:
            # No chapters found, split by word count
            chapters = self._split_by_words(text)

        if not chapters:
            # Single chapter for entire text
            chapters = [self._create_chapter(1, "Full Text", text)]

        logger.info("Parsed chapters", count=len(chapters), total_words=sum(c.word_count for c in chapters))
        return chapters

    def _detect_chapters(self, text: str) -> list[Chapter]:
        """Detect and split chapters based on patterns."""
        lines = text.split("\n")
        chapter_starts: list[tuple[int, str]] = []

        # Find all chapter markers
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            for pattern in CHAPTER_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    # Check if next line might be the title
                    title = stripped
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        # If next line is short and not empty, might be title
                        if next_line and len(next_line) < 100 and not re.match(r"^[A-Z]", next_line[:1] if next_line else ""):
                            pass  # Keep current title
                        elif next_line and len(next_line) < 100:
                            title = f"{stripped}: {next_line}"
                    chapter_starts.append((i, title))
                    break

        if not chapter_starts:
            return []

        # Split text into chapters
        chapters: list[Chapter] = []
        for idx, (start_line, title) in enumerate(chapter_starts):
            # Get end line (start of next chapter or end of text)
            if idx + 1 < len(chapter_starts):
                end_line = chapter_starts[idx + 1][0]
            else:
                end_line = len(lines)

            # Extract chapter text
            chapter_text = "\n".join(lines[start_line:end_line]).strip()

            # Skip if too short
            word_count = len(chapter_text.split())
            if word_count < self.min_chapter_words:
                continue

            chapters.append(self._create_chapter(len(chapters) + 1, title, chapter_text))

        return chapters

    def _split_by_words(self, text: str, chunk_size: Optional[int] = None) -> list[Chapter]:
        """Split text into chunks by word count."""
        chunk_size = chunk_size or self.max_chunk_words
        words = text.split()
        chapters: list[Chapter] = []

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chapter_num = len(chapters) + 1
            chapters.append(self._create_chapter(chapter_num, f"Part {chapter_num}", chunk_text))

        return chapters

    def _create_chapter(self, number: int, title: str, text: str) -> Chapter:
        """Create a Chapter object."""
        # Clean up title
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) > 100:
            title = title[:97] + "..."

        return Chapter(
            id=str(uuid.uuid4())[:8],
            number=number,
            title=title,
            text=text,
            word_count=len(text.split()),
            audio_status=ChapterStatus.PENDING,
        )

    def split_long_chapter(self, chapter: Chapter) -> list[Chapter]:
        """Split a long chapter into smaller parts for TTS."""
        if chapter.word_count <= self.max_chunk_words:
            return [chapter]

        parts = self._split_by_words(chapter.text, self.max_chunk_words)

        # Update titles to show they're parts
        for i, part in enumerate(parts):
            part.title = f"{chapter.title} (Part {i + 1}/{len(parts)})"
            part.number = chapter.number

        return parts
