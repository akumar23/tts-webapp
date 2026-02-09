"""Book and chapter API endpoints."""

import uuid
from io import BytesIO
from typing import Annotated

import soundfile as sf
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from src.api.schemas.books import (
    Book,
    BookSource,
    BookSummary,
    Chapter,
    ChapterAudioResponse,
    ChapterStatus,
    ChapterSummary,
    GutenbergSearchResult,
    SynthesizeChapterRequest,
    UploadBookRequest,
    WordTimingResponse,
)
from src.config import Settings, get_settings
from src.core.books.gutenberg import GutenbergClient
from src.core.books.parser import ChapterParser, normalize_text_for_tts
from src.core.books.store import BookStore, get_book_store
from src.core.provider_manager import ProviderManager, get_provider_manager
from src.core.providers.edge import EdgeTTSProvider

router = APIRouter(prefix="/v1/books", tags=["Books"])

# Shared instances
_gutenberg_client: GutenbergClient | None = None
_parser = ChapterParser()


def get_gutenberg_client() -> GutenbergClient:
    """Get or create the Gutenberg client."""
    global _gutenberg_client
    if _gutenberg_client is None:
        _gutenberg_client = GutenbergClient()
    return _gutenberg_client


# --- Search & Import ---


@router.get("/search", response_model=list[GutenbergSearchResult])
async def search_gutenberg(
    q: str = Query(..., min_length=1, description="Search query"),
    language: str = Query(default="en", description="Language filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
) -> list[GutenbergSearchResult]:
    """Search for books on Project Gutenberg."""
    client = get_gutenberg_client()
    return await client.search(q, language=language, page=page)


@router.post("/import/{gutenberg_id}", response_model=BookSummary)
async def import_gutenberg_book(
    gutenberg_id: str,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> BookSummary:
    """
    Import a book from Project Gutenberg by ID.

    Fetches the book text and parses it into chapters.
    """
    client = get_gutenberg_client()

    try:
        metadata, text = await client.fetch_book_text(gutenberg_id)
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get author
    authors = metadata.get("authors", [])
    author = authors[0].get("name", "Unknown") if authors else "Unknown"

    # Parse into chapters
    chapters = _parser.parse(text, force_split=True)

    # Create book
    book = Book(
        id=str(uuid.uuid4())[:8],
        title=metadata.get("title", "Unknown Title"),
        author=author,
        source=BookSource.GUTENBERG,
        source_id=gutenberg_id,
        language=metadata.get("languages", ["en"])[0] if metadata.get("languages") else "en",
        chapters=chapters,
        total_words=sum(c.word_count for c in chapters),
    )

    store.add_book(book)

    return BookSummary(
        id=book.id,
        title=book.title,
        author=book.author,
        source=book.source,
        language=book.language,
        chapter_count=len(book.chapters),
        total_words=book.total_words,
    )


@router.post("/upload", response_model=BookSummary)
async def upload_book(
    request: UploadBookRequest,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> BookSummary:
    """
    Upload custom book text.

    The text will be parsed into chapters automatically.
    """
    chapters = _parser.parse(request.text, force_split=True)

    book = Book(
        id=str(uuid.uuid4())[:8],
        title=request.title,
        author=request.author,
        source=BookSource.UPLOAD,
        language=request.language,
        chapters=chapters,
        total_words=sum(c.word_count for c in chapters),
    )

    store.add_book(book)

    return BookSummary(
        id=book.id,
        title=book.title,
        author=book.author,
        source=book.source,
        language=book.language,
        chapter_count=len(book.chapters),
        total_words=book.total_words,
    )


# --- Book Management ---


@router.get("", response_model=list[BookSummary])
async def list_books(
    store: Annotated[BookStore, Depends(get_book_store)],
) -> list[BookSummary]:
    """List all imported books."""
    books = store.list_books()
    return [
        BookSummary(
            id=b.id,
            title=b.title,
            author=b.author,
            source=b.source,
            language=b.language,
            chapter_count=len(b.chapters),
            total_words=b.total_words,
        )
        for b in books
    ]


@router.get("/{book_id}", response_model=BookSummary)
async def get_book(
    book_id: str,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> BookSummary:
    """Get book details."""
    book = store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookSummary(
        id=book.id,
        title=book.title,
        author=book.author,
        source=book.source,
        language=book.language,
        chapter_count=len(book.chapters),
        total_words=book.total_words,
    )


@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> dict:
    """Delete a book and all its audio."""
    if not store.delete_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found")
    return {"status": "deleted", "book_id": book_id}


# --- Chapters ---


@router.get("/{book_id}/chapters", response_model=list[ChapterSummary])
async def list_chapters(
    book_id: str,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> list[ChapterSummary]:
    """List all chapters in a book."""
    book = store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return [
        ChapterSummary(
            id=c.id,
            number=c.number,
            title=c.title,
            word_count=c.word_count,
            audio_status=c.audio_status,
            audio_url=c.audio_url,
        )
        for c in book.chapters
    ]


@router.get("/{book_id}/chapters/{chapter_id}", response_model=Chapter)
async def get_chapter(
    book_id: str,
    chapter_id: str,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> Chapter:
    """Get full chapter details including text."""
    chapter = store.get_chapter(book_id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


# --- Audio Synthesis ---


@router.post("/{book_id}/chapters/{chapter_id}/synthesize", response_model=ChapterAudioResponse)
async def synthesize_chapter(
    book_id: str,
    chapter_id: str,
    request: SynthesizeChapterRequest,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> ChapterAudioResponse:
    """
    Synthesize a chapter to audio with word-level timing.

    Returns audio URL and timing data for karaoke-style text highlighting.
    """
    chapter = store.get_chapter(book_id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Update status to processing
    store.update_chapter_status(book_id, chapter_id, ChapterStatus.PROCESSING)

    try:
        # Use Edge TTS with timing extraction
        edge_provider = EdgeTTSProvider()
        voice = request.voice or "en-US-JennyNeural"

        # Normalize text for natural TTS reading flow
        normalized_text = normalize_text_for_tts(chapter.text)

        result = await edge_provider.synthesize_with_timing(
            text=normalized_text,
            voice=voice,
            speed=request.speed,
        )

        # Convert timing to dict format for storage
        timings = [
            {
                "word": t.word,
                "start_ms": t.start_ms,
                "end_ms": t.end_ms,
                "char_start": t.char_start,
                "char_end": t.char_end,
            }
            for t in result.word_timings
        ]

        # Store the audio with timing
        store.store_audio(
            chapter_id=chapter_id,
            audio_bytes=result.audio_data,
            duration_ms=result.duration_ms,
            timings=timings,
        )

        # Update status
        audio_url = f"/v1/books/{book_id}/chapters/{chapter_id}/audio"
        store.update_chapter_status(book_id, chapter_id, ChapterStatus.COMPLETED, audio_url)

        return ChapterAudioResponse(
            chapter_id=chapter_id,
            audio_url=audio_url,
            duration_ms=result.duration_ms,
            word_count=len(result.word_timings),
            timings=[
                WordTimingResponse(**t) for t in timings
            ],
        )

    except Exception as e:
        store.update_chapter_status(book_id, chapter_id, ChapterStatus.FAILED)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e}")


@router.get("/{book_id}/chapters/{chapter_id}/audio")
async def get_chapter_audio(
    book_id: str,
    chapter_id: str,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> Response:
    """Get the synthesized audio file for a chapter."""
    chapter = store.get_chapter(book_id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if chapter.audio_status != ChapterStatus.COMPLETED:
        raise HTTPException(
            status_code=404,
            detail=f"Audio not ready. Status: {chapter.audio_status.value}",
        )

    audio = store.get_audio(chapter_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio data not found")

    return Response(
        content=audio.audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'attachment; filename="chapter_{chapter.number}.mp3"',
        },
    )


@router.get("/{book_id}/chapters/{chapter_id}/playback", response_model=ChapterAudioResponse)
async def get_chapter_playback(
    book_id: str,
    chapter_id: str,
    store: Annotated[BookStore, Depends(get_book_store)],
) -> ChapterAudioResponse:
    """
    Get playback data for a chapter (audio URL + timing).

    Use this endpoint for the karaoke-style reader UI.
    """
    chapter = store.get_chapter(book_id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if chapter.audio_status != ChapterStatus.COMPLETED:
        raise HTTPException(
            status_code=404,
            detail=f"Audio not ready. Status: {chapter.audio_status.value}",
        )

    audio = store.get_audio(chapter_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio data not found")

    return ChapterAudioResponse(
        chapter_id=chapter_id,
        audio_url=f"/v1/books/{book_id}/chapters/{chapter_id}/audio",
        duration_ms=audio.duration_ms,
        word_count=len(audio.timings),
        timings=[WordTimingResponse(**t) for t in audio.timings],
    )
