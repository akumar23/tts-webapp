"""Project Gutenberg client using Gutendex API."""

import re
from typing import Optional

import httpx
import structlog

from src.api.schemas.books import GutenbergSearchResult

logger = structlog.get_logger(__name__)

# Gutendex API - free JSON API for Project Gutenberg
GUTENDEX_API = "https://gutendex.com"


class GutenbergClient:
    """Client for fetching books from Project Gutenberg."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, language: str = "en", page: int = 1) -> list[GutenbergSearchResult]:
        """
        Search for books on Project Gutenberg.

        Args:
            query: Search query (title or author)
            language: Filter by language code
            page: Page number for pagination

        Returns:
            List of search results
        """
        try:
            params = {
                "search": query,
                "languages": language,
                "page": page,
            }
            response = await self._client.get(f"{GUTENDEX_API}/books", params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for book in data.get("results", []):
                # Get first author
                authors = book.get("authors", [])
                author = authors[0].get("name", "Unknown") if authors else "Unknown"

                # Get language
                languages = book.get("languages", ["en"])
                lang = languages[0] if languages else "en"

                results.append(
                    GutenbergSearchResult(
                        id=str(book["id"]),
                        title=book.get("title", "Unknown Title"),
                        author=author,
                        language=lang,
                        subjects=book.get("subjects", []),
                        download_count=book.get("download_count"),
                    )
                )

            logger.info("Gutenberg search completed", query=query, results=len(results))
            return results

        except httpx.HTTPError as e:
            logger.error("Gutenberg search failed", query=query, error=str(e))
            raise RuntimeError(f"Failed to search Gutenberg: {e}")

    async def fetch_book_text(self, book_id: str) -> tuple[dict, str]:
        """
        Fetch the full text of a book from Project Gutenberg.

        Args:
            book_id: Gutenberg book ID

        Returns:
            Tuple of (metadata dict, full text string)
        """
        try:
            # First get book metadata
            response = await self._client.get(f"{GUTENDEX_API}/books/{book_id}")
            response.raise_for_status()
            metadata = response.json()

            # Find the plain text URL
            formats = metadata.get("formats", {})
            text_url = None

            # Prefer UTF-8 plain text
            for fmt, url in formats.items():
                if "text/plain" in fmt and "utf-8" in fmt.lower():
                    text_url = url
                    break

            # Fall back to any plain text
            if not text_url:
                for fmt, url in formats.items():
                    if "text/plain" in fmt:
                        text_url = url
                        break

            if not text_url:
                raise RuntimeError(f"No plain text format available for book {book_id}")

            # Fetch the text
            text_response = await self._client.get(text_url, follow_redirects=True)
            text_response.raise_for_status()

            # Handle encoding
            text = text_response.text

            # Clean up Gutenberg header/footer
            text = self._clean_gutenberg_text(text)

            logger.info(
                "Fetched Gutenberg book",
                book_id=book_id,
                title=metadata.get("title"),
                text_length=len(text),
            )

            return metadata, text

        except httpx.HTTPError as e:
            logger.error("Failed to fetch Gutenberg book", book_id=book_id, error=str(e))
            raise RuntimeError(f"Failed to fetch book {book_id}: {e}")

    def _clean_gutenberg_text(self, text: str) -> str:
        """Remove Project Gutenberg header and footer boilerplate."""
        # Common start markers
        start_markers = [
            r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK",
            r"\*\*\* START OF THIS PROJECT GUTENBERG EBOOK",
            r"\*\*\*START OF THE PROJECT GUTENBERG EBOOK",
        ]

        # Common end markers
        end_markers = [
            r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK",
            r"\*\*\* END OF THIS PROJECT GUTENBERG EBOOK",
            r"\*\*\*END OF THE PROJECT GUTENBERG EBOOK",
            r"End of the Project Gutenberg EBook",
            r"End of Project Gutenberg",
        ]

        # Find and remove header
        for marker in start_markers:
            match = re.search(marker, text, re.IGNORECASE)
            if match:
                # Find the end of this line and start from there
                end_of_line = text.find("\n", match.end())
                if end_of_line != -1:
                    text = text[end_of_line + 1 :]
                break

        # Find and remove footer
        for marker in end_markers:
            match = re.search(marker, text, re.IGNORECASE)
            if match:
                text = text[: match.start()]
                break

        return text.strip()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
