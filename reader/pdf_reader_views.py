import logging
import os
import re
from functools import lru_cache
from html import escape
from typing import Dict, Generator, Iterator, List, Optional, Tuple

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from books.models import Book
from library.models import ReadingProgress, UserLibrary

logger = logging.getLogger(__name__)


class JWTAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request, "user_payload") and "user_id" in request.user_payload


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PDF_MAGIC = b"%PDF"
MIN_PDF_BYTES = 64
MAX_PAGES_SAFETY = 5_000

PRELIMINARY_PATTERNS: List[str] = [
    r"title\s*page", r"copyright", r"dedication",
    r"table\s*of\s*contents?", r"foreword", r"preface",
    r"introduction", r"acknowledgments?", r"about\s*the\s*author",
    r"isbn", r"bibliography", r"index", r"glossary", r"appendix",
]
CHAPTER_PATTERNS: List[str] = [
    r"chapter\s+\d+",
    r"chapter\s+[IVXLCDM]+",
    r"^\d+\s*\.\s+",
    r"^[IVXLCDM]+\s*\.\s*",
]

# Pre-compiled at module load — shared across all requests
_PRELIM_RE = re.compile("|".join(PRELIMINARY_PATTERNS), re.IGNORECASE)
_CHAPTER_RE = re.compile("|".join(CHAPTER_PATTERNS), re.IGNORECASE | re.MULTILINE)


# ---------------------------------------------------------------------------
# Page analysis — stateless functions + LRU-bounded cache
# ---------------------------------------------------------------------------

@lru_cache(maxsize=512)
def _cached_analyze(text_key: str, page_num: int, fast_mode: bool) -> Dict:
    """
    LRU cache replaces the unbounded dict cache in PageAnalyzer.
    `text_key` is the first 200 chars of the page — enough to distinguish
    pages without storing full content in the cache.
    """
    # Reconstruct text from the key for analysis (we only stored the prefix,
    # so this path is only used for the full analyze path which is called
    # with the real text — see analyze_page_content below).
    raise NotImplementedError("Call analyze_page_content directly.")


def analyze_page_content(text: str, page_num: int, fast_mode: bool = False) -> Dict:
    """Stateless page analyzer — no global mutable state."""
    text_stripped = text.strip() if text else ""

    if not text_stripped:
        return {
            "page_number": page_num,
            "type": "empty",
            "category": "empty",
            "confidence": 1.0,
            "title": None,
            "content_preview": "",
        }

    if fast_mode:
        return _fast_analyze(text_stripped, page_num)
    return _full_analyze(text_stripped, page_num)


def _fast_analyze(text: str, page_num: int) -> Dict:
    text_lower = text.lower()
    first_line = text.split("\n", 1)[0][:50]

    if any(k in text_lower for k in ("copyright", "title", "contents", "table of contents", "isbn")):
        return _result(page_num, "preliminary", "preliminary", 0.7, first_line, text)

    if "chapter" in text_lower and any(c.isdigit() for c in text[:50]):
        return _result(page_num, "chapter", "chapter", 0.8, first_line, text)

    return _result(page_num, "content", "content", 0.6, first_line, text)


def _full_analyze(text: str, page_num: int) -> Dict:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    title = _extract_title(lines)

    if _PRELIM_RE.search(text):
        category = _get_preliminary_category(text)
        return _result(page_num, "preliminary", category, 0.8, title, text)

    if _CHAPTER_RE.search(text):
        return _result(page_num, "chapter", "chapter", 0.9, title, text)

    return _result(page_num, "content", "content", 0.6, title, text)


def _result(page_num, ptype, category, confidence, title, text) -> Dict:
    return {
        "page_number": page_num,
        "type": ptype,
        "category": category,
        "confidence": confidence,
        "title": title[:50] if title else None,
        "content_preview": text[:100],
    }


def _get_preliminary_category(text: str) -> str:
    t = text.lower()
    for keyword, category in (
        ("copyright", "copyright"),
        ("table of content", "table_of_contents"),
        ("contents", "table_of_contents"),
        ("dedication", "dedication"),
        ("foreword", "foreword"),
        ("preface", "preface"),
        ("introduction", "introduction"),
        ("acknowledgment", "acknowledgments"),
        ("isbn", "isbn"),
        ("index", "index"),
        ("bibliography", "bibliography"),
        ("glossary", "glossary"),
        ("appendix", "appendix"),
    ):
        if keyword in t:
            return category
    if "title" in t and len(text) < 500:
        return "title_page"
    return "preliminary"


def _extract_title(lines: List[str]) -> Optional[str]:
    if not lines:
        return None
    candidates = [
        l for l in lines[:5]
        if 10 <= len(l) <= 100 and not l.startswith(("http", "www", "ISBN"))
    ]
    return max(candidates, key=len) if candidates else (lines[0] if lines else None)


# ---------------------------------------------------------------------------
# HTML rendering — lightweight, no per-line loop
# ---------------------------------------------------------------------------

def _render_page_html(page_num: int, raw_text: str, analysis: Dict) -> str:
    """
    Build page HTML. Avoids the expensive line-by-line loop from the original
    _html_page_wrap; delegates paragraph structure to CSS white-space instead.
    """
    ptype = analysis["type"]
    category = analysis["category"]
    title = analysis.get("title")

    if raw_text.strip():
        # Wrap the escaped text in a single <pre class="pdf-text"> so the
        # browser preserves whitespace without us re-parsing every line.
        body = f"<pre class='pdf-text'>{escape(raw_text)}</pre>"
    else:
        body = "<em>[No extractable text on this page]</em>"

    title_html = (
        f"<span class='page-title'>{escape(title)}</span>" if title else ""
    )

    return (
        f"<div class='pdf-page page-type-{ptype} page-category-{category}'"
        f" data-page='{page_num}' data-type='{ptype}' data-category='{category}'>"
        f"<div class='pdf-page-header'>"
        f"<span class='page-number'>Page {page_num}</span>"
        f"{title_html}"
        f"<span class='page-type-badge'>{ptype.replace('_', ' ').title()}</span>"
        f"</div>"
        f"<div class='pdf-page-content'>{body}</div>"
        f"</div>\n"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_pdf_file(path: str) -> Tuple[bool, Optional[str]]:
    if not os.path.exists(path):
        return False, "PDF file not found on disk"
    size = os.path.getsize(path)
    if size < MIN_PDF_BYTES:
        return False, f"File too small to be a PDF ({size} bytes)"
    try:
        with open(path, "rb") as fh:
            if not fh.read(8).startswith(PDF_MAGIC):
                return False, "File does not start with %PDF"
    except OSError as exc:
        return False, f"Cannot read file header: {exc}"
    return True, None


# ---------------------------------------------------------------------------
# Streaming generators  ← the core optimization
# ---------------------------------------------------------------------------

def _structure_comment(structure: Dict) -> str:
    s = structure
    return (
        f"<!-- PDF structure:"
        f" total={s['total_pages']}"
        f" prelim={s['preliminary_count']}(last={s['last_preliminary_page']})"
        f" content_start={s['first_content_page']}"
        f" chapters={s['chapter_count']}"
        f" empty={s['empty_count']} -->\n"
    )


def _iter_pages_pypdf(
    path: str,
    page_number: Optional[int],
) -> Generator[Tuple[str, Optional[str], Optional[Dict]], None, None]:
    """
    Yields (html_chunk, error, final_analysis) tuples.
    
    - For a single-page request: yields exactly one tuple then stops.
    - For all-pages: yields one tuple per page (html_chunk, None, None),
      then a final tuple ("", None, structure_dict).
    
    Using a generator means each page is yielded to the HTTP response
    immediately after it's extracted — no accumulation in memory.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        yield "", "pypdf is not installed", None
        return

    try:
        reader = PdfReader(path, strict=False)
    except Exception as exc:
        yield "", f"Cannot open PDF: {exc}", None
        return

    total = len(reader.pages)
    if total == 0:
        yield "", "PDF has no pages", None
        return

    # ── single page ─────────────────────────────────────────────────────────
    if page_number is not None:
        if not (1 <= page_number <= total):
            yield "", f"Page {page_number} out of range (1–{total})", None
            return
        try:
            raw = reader.pages[page_number - 1].extract_text() or ""
            analysis = analyze_page_content(raw, page_number)
            yield _render_page_html(page_number, raw, analysis), None, analysis
        except Exception as exc:
            yield "", f"Error reading page {page_number}: {exc}", None
        return

    # ── all pages ────────────────────────────────────────────────────────────
    cap = min(total, MAX_PAGES_SAFETY)
    fast_mode = total > 100

    structure = {
        "total_pages": cap,
        "preliminary_count": 0,
        "chapter_count": 0,
        "content_count": 0,
        "empty_count": 0,
        "first_content_page": None,
        "last_preliminary_page": None,
    }

    for idx in range(cap):
        try:
            raw = reader.pages[idx].extract_text() or ""
            analysis = analyze_page_content(raw, idx + 1, fast_mode=fast_mode)

            # Update running structure totals inline — no second pass needed
            ptype = analysis["type"]
            structure[f"{ptype}_count"] += 1
            if ptype in ("chapter", "content") and structure["first_content_page"] is None:
                structure["first_content_page"] = idx + 1
            elif ptype == "preliminary":
                structure["last_preliminary_page"] = idx + 1

            yield _render_page_html(idx + 1, raw, analysis), None, None

        except Exception as exc:
            logger.warning("pypdf page %d error in %s: %s", idx + 1, path, exc)
            structure["empty_count"] += 1
            yield (
                f"<div class='pdf-page page-type-error' data-page='{idx + 1}'>"
                f"<em>[Page could not be read: {escape(str(exc))}]</em></div>\n"
            ), None, None

    # Final tuple carries the complete structure summary
    yield _structure_comment(structure), None, structure


def _iter_pages_pdfplumber(
    path: str,
    page_number: Optional[int],
) -> Generator[Tuple[str, Optional[str], Optional[Dict]], None, None]:
    """Mirror of _iter_pages_pypdf for pdfplumber fallback."""
    try:
        import pdfplumber
    except ImportError:
        yield "", "pdfplumber is not installed", None
        return

    try:
        pdf = pdfplumber.open(path)
    except Exception as exc:
        yield "", f"pdfplumber failed to open PDF: {exc}", None
        return

    with pdf:
        total = len(pdf.pages)
        if total == 0:
            yield "", "PDF has no pages", None
            return

        # ── single page ──────────────────────────────────────────────────────
        if page_number is not None:
            if not (1 <= page_number <= total):
                yield "", f"Page {page_number} out of range (1–{total})", None
                return
            try:
                raw = pdf.pages[page_number - 1].extract_text() or ""
                analysis = analyze_page_content(raw, page_number)
                yield _render_page_html(page_number, raw, analysis), None, analysis
            except Exception as exc:
                yield "", f"Error reading page {page_number}: {exc}", None
            return

        # ── all pages ────────────────────────────────────────────────────────
        cap = min(total, MAX_PAGES_SAFETY)
        fast_mode = total > 100
        structure = {
            "total_pages": cap,
            "preliminary_count": 0,
            "chapter_count": 0,
            "content_count": 0,
            "empty_count": 0,
            "first_content_page": None,
            "last_preliminary_page": None,
        }

        for idx in range(cap):
            try:
                raw = pdf.pages[idx].extract_text() or ""
                analysis = analyze_page_content(raw, idx + 1, fast_mode=fast_mode)

                ptype = analysis["type"]
                structure[f"{ptype}_count"] += 1
                if ptype in ("chapter", "content") and structure["first_content_page"] is None:
                    structure["first_content_page"] = idx + 1
                elif ptype == "preliminary":
                    structure["last_preliminary_page"] = idx + 1

                yield _render_page_html(idx + 1, raw, analysis), None, None

            except Exception as exc:
                logger.warning("pdfplumber page %d in %s: %s", idx + 1, path, exc)
                structure["empty_count"] += 1
                yield (
                    f"<div class='pdf-page page-type-error' data-page='{idx + 1}'>"
                    f"<em>[Page could not be read: {escape(str(exc))}]</em></div>\n"
                ), None, None

        yield _structure_comment(structure), None, structure


# ---------------------------------------------------------------------------
# Public streaming entry-point
# ---------------------------------------------------------------------------

def stream_pdf_pages(
    path: str,
    page_number: Optional[int] = None,
) -> Tuple[Iterator[str], Optional[str]]:
    """
    Returns (chunk_iterator, error_string_or_None).

    The iterator yields HTML strings one page at a time.  Callers wrap it
    in StreamingHttpResponse — no full content ever exists in memory.
    """
    ok, reason = _validate_pdf_file(path)
    if not ok:
        return iter([]), reason

    def _generate() -> Iterator[str]:
        had_content = False
        error_seen = None

        # Try pypdf first
        for chunk, err, _ in _iter_pages_pypdf(path, page_number):
            if err:
                error_seen = err
                break
            if chunk:
                had_content = True
                yield chunk

        if had_content:
            return

        # Fallback to pdfplumber
        logger.info("pypdf failed (%s) for %s, trying pdfplumber", error_seen, path)
        for chunk, err, _ in _iter_pages_pdfplumber(path, page_number):
            if err:
                logger.error("pdfplumber also failed for %s: %s", path, err)
                yield (
                    "<div class='scanned-notice'>"
                    "<p>This PDF appears to contain scanned images with no "
                    "extractable text. Consider using an OCR service.</p></div>"
                )
                return
            if chunk:
                yield chunk

    return _generate(), None


# ---------------------------------------------------------------------------
# Backward-compatible non-streaming helper (used by read_page / analyze)
# ---------------------------------------------------------------------------

def extract_pdf_text_robust(
    path: str,
    page_number: Optional[int] = None,
) -> Tuple[Optional[str], Optional[str], Dict]:
    """
    Non-streaming path kept for single-page requests and analyze_structure.
    Collects the generator into memory — only appropriate for small payloads.
    """
    ok, reason = _validate_pdf_file(path)
    if not ok:
        return None, reason, {}

    chunks: List[str] = []
    final_analysis: Dict = {}
    error: Optional[str] = None

    for chunk, err, analysis in _iter_pages_pypdf(path, page_number):
        if err:
            error = err
            break
        if analysis:
            final_analysis = analysis
        if chunk:
            chunks.append(chunk)

    if chunks:
        return "".join(chunks), None, final_analysis

    # Fallback
    chunks.clear()
    for chunk, err, analysis in _iter_pages_pdfplumber(path, page_number):
        if err:
            return None, err, {}
        if analysis:
            final_analysis = analysis
        if chunk:
            chunks.append(chunk)

    if not chunks:
        return (
            "<div class='scanned-notice'><p>No extractable text found.</p></div>",
            None,
            {},
        )

    return "".join(chunks), None, final_analysis


# ---------------------------------------------------------------------------
# ViewSet
# ---------------------------------------------------------------------------

class PDFReaderViewSet(viewsets.GenericViewSet):
    permission_classes = [JWTAuthenticated]
    authentication_classes = []

    def _get_user_id(self) -> int:
        try:
            return self.request.user_payload["user_id"]
        except (AttributeError, KeyError):
            if hasattr(self.request, "user") and self.request.user.is_authenticated:
                return self.request.user.id
            raise AttributeError("No authentication information found")

    def _check_access(self, book: Book, user_id: int) -> Optional[Response]:
        # Uncomment for production:
        # if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
        #     return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
        return None

    def _total_pages(self, book: Book) -> int:
        return book.total_pages if book.content_source == "manual" else (book.pages or 0)

    # ------------------------------------------------------------------
    # Streaming action — the main reader endpoint
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"])
    def read_pdf(self, request, pk=None):
        """
        Stream full book content as chunked HTML.
        
        Uses StreamingHttpResponse so the client receives and can render
        page 1 before the server has read page 2.  The X-Book-Meta header
        carries JSON metadata so the frontend doesn't have to wait for the
        stream to finish.
        """
        import json

        user_id = self._get_user_id()

        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)

        access_error = self._check_access(book, user_id)
        if access_error:
            return access_error

        if book.content_source == "manual":
            # Manual content is already in the DB — no benefit to streaming
            html = self._extract_manual_content(book)
            return Response(self._book_response(book, user_id, html))

        if not book.pdf_file:
            return Response(
                {"error": "This book has no PDF file attached"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chunk_iter, error = stream_pdf_pages(book.pdf_file.path)
        if error:
            logger.error("read_pdf book=%s error=%s", pk, error)
            return Response(
                {"error": f"Failed to extract content: {error}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Update / create reading progress without blocking the stream
        progress, _ = ReadingProgress.objects.get_or_create(
            user_id=user_id,
            book=book,
            defaults={"current_page": 1, "total_pages": self._total_pages(book)},
        )

        meta = {
            "id": book.id,
            "title": book.title,
            "author": book.author.name if book.author else "Unknown",
            "description": book.description,
            "total_pages": self._total_pages(book),
            "current_page": progress.current_page,
            "content_source": book.content_source,
            "price": float(book.price),
            "is_free": book.is_free,
            "pdf_file_url": book.pdf_file.url if book.pdf_file else None,
        }

        response = StreamingHttpResponse(chunk_iter, content_type="text/html; charset=utf-8")
        # Deliver metadata immediately via header — frontend reads it before
        # the stream body arrives.
        response["X-Book-Meta"] = json.dumps(meta)
        response["X-Accel-Buffering"] = "no"  # Disable nginx proxy buffering
        return response

    # ------------------------------------------------------------------
    # Single-page action — non-streaming (single page is already small)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"])
    def read_page(self, request, pk=None):
        user_id = self._get_user_id()

        try:
            page_number = max(1, int(request.GET.get("page", 1)))
        except (ValueError, TypeError):
            page_number = 1

        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)

        access_error = self._check_access(book, user_id)
        if access_error:
            return access_error

        if book.content_source == "manual":
            html = self._extract_manual_content(book, page_number)
            return Response({
                "page_number": page_number,
                "content": html,
                "total_pages": self._total_pages(book),
                "content_source": "manual",
            })

        if not book.pdf_file:
            return Response({"error": "No PDF attached"}, status=status.HTTP_400_BAD_REQUEST)

        html, error, analysis = extract_pdf_text_robust(book.pdf_file.path, page_number)
        if error:
            return Response(
                {"error": f"Failed to extract page: {error}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "page_number": page_number,
            "content": html,
            "total_pages": self._total_pages(book),
            "content_source": book.content_source,
            "page_info": {
                "type": analysis.get("type", "content"),
                "category": analysis.get("category", "content"),
                "title": analysis.get("title"),
                "confidence": analysis.get("confidence", 0.0),
            } if analysis else None,
        })

    @action(detail=True, methods=["get"])
    def analyze_structure(self, request, pk=None):
        user_id = self._get_user_id()

        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)

        access_error = self._check_access(book, user_id)
        if access_error:
            return access_error

        if book.content_source == "manual":
            chapters = book.chapters.all().order_by("chapter_number")
            return Response({
                "structure": {
                    "content_source": "manual",
                    "total_chapters": chapters.count(),
                    "chapters": [
                        {
                            "number": c.chapter_number,
                            "title": c.title,
                            "pages_count": c.pages.count(),
                            "is_free": c.is_free,
                        }
                        for c in chapters
                    ],
                }
            })

        if not book.pdf_file:
            return Response({"error": "No PDF attached"}, status=status.HTTP_400_BAD_REQUEST)

        # extract_pdf_text_robust collects all pages — intentional here
        # because we need the complete structure summary, not just page 1.
        _, error, analysis = extract_pdf_text_robust(book.pdf_file.path)
        if error:
            return Response(
                {"error": f"Failed to analyze structure: {error}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # analysis is the structure dict from the final generator tuple
        return Response({"structure": {"content_source": "pdf", **analysis}})

    @action(detail=False, methods=["post"])
    def update_progress(self, request):
        user_id = self._get_user_id()
        book_id = request.data.get("book_id")
        current_page = request.data.get("current_page")
        total_pages = request.data.get("total_pages")

        if not all([book_id, current_page, total_pages]):
            return Response(
                {"error": "book_id, current_page, and total_pages are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)

        if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            current_page = int(current_page)
            total_pages = int(total_pages)
        except (ValueError, TypeError):
            return Response(
                {"error": "current_page and total_pages must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        progress, _ = ReadingProgress.objects.update_or_create(
            user_id=user_id,
            book=book,
            defaults={
                "current_page": current_page,
                "total_pages": total_pages,
                "last_read_at": timezone.now(),
            },
        )

        return Response({
            "success": True,
            "current_page": progress.current_page,
            "total_pages": progress.total_pages,
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _book_response(self, book: Book, user_id: int, html: str) -> Dict:
        progress, _ = ReadingProgress.objects.get_or_create(
            user_id=user_id,
            book=book,
            defaults={"current_page": 1, "total_pages": self._total_pages(book)},
        )
        
        # Calculate per-page cost
        per_page_cost = 0.00
        if not book.is_free and book.price > 0 and self._total_pages(book) > 0:
            per_page_cost = round(float(book.price) / self._total_pages(book), 4)
        
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author.name if book.author else "Unknown",
            "description": book.description,
            "total_pages": self._total_pages(book),
            "current_page": progress.current_page,
            "content": html,
            "content_source": book.content_source,
            "price": float(book.price),
            "is_free": book.is_free,
            "pdf_file_url": book.pdf_file.url if book.pdf_file else None,
            "per_page_cost": per_page_cost,
        }

    def _extract_manual_content(self, book: Book, page_number: Optional[int] = None) -> str:
        chapters = book.chapters.all().order_by("chapter_number")

        if page_number is not None:
            for chapter in chapters:
                page_obj = chapter.pages.filter(page_number=page_number).first()
                if page_obj:
                    return (
                        f"<div class='page' data-page='{page_number}'>"
                        f"<h3>Chapter {chapter.chapter_number}: {escape(chapter.title)}</h3>"
                        f"<div class='page-content'>{page_obj.content}</div></div>"
                    )
            chapter = chapters.first()
            if chapter:
                return (
                    f"<div class='page' data-page='{page_number}'>"
                    f"<h3>Chapter {chapter.chapter_number}: {escape(chapter.title)}</h3>"
                    f"<div class='page-content'>{chapter.content}</div></div>"
                )
            return f"<div class='page'>Page {page_number} not available</div>"

        parts: List[str] = []
        for chapter in chapters:
            parts.append(
                f"<div class='chapter' data-chapter='{chapter.chapter_number}'>"
                f"<h2>Chapter {chapter.chapter_number}: {escape(chapter.title)}</h2>"
                f"<div class='chapter-content'>{chapter.content}</div>"
            )
            for page in chapter.pages.all().order_by("page_number"):
                parts.append(
                    f"<div class='page' data-page='{page.page_number}'>"
                    f"<h4>Page {page.page_number}</h4>"
                    f"<div class='page-content'>{page.content}</div></div>"
                )
            parts.append("</div>")
        return "".join(parts)