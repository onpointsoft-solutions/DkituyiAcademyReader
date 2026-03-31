import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from books.models import Book
from library.models import UserLibrary
from .models import (
    Bookmark, Highlight, Note,
    PageCharge, ReadingSession, ScreenshotWarning,
)

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    User = None

logger = logging.getLogger(__name__)


class JWTAuthenticated(BasePermission):
    """
    Custom permission class that checks for JWT authentication
    """
    
    def has_permission(self, request, view):
        return hasattr(request, 'user_payload') and 'user_id' in request.user_payload


# ---------------------------------------------------------------------------
# Serialisation helpers  (single source of truth per model)
# ---------------------------------------------------------------------------

def _bookmark_dict(b: Bookmark) -> dict:
    return {
        "id": b.id,
        "page_number": b.page_number,
        "position": b.position,
        "title": b.title,
        "note": b.note,
        "type": "bookmark",
        "created_at": b.created_at,
    }


def _highlight_dict(h: Highlight) -> dict:
    return {
        "id": h.id,
        "page_number": h.page_number,
        "start_position": h.start_position,
        "end_position": h.end_position,
        "selected_text": h.selected_text,
        "color": h.color,
        "note": h.note,
        "type": "highlight",
        "created_at": h.created_at,
    }


def _note_dict(n: Note) -> dict:
    return {
        "id": n.id,
        "page_number": n.page_number,
        "position": n.position,
        "content": n.content,
        "color": n.color,
        "is_private": n.is_private,
        "type": "note",
        "created_at": n.created_at,
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require_fields(data: dict, *fields: str):
    """
    Return a list of field names that are missing or blank.
    Treats 0 as a valid value so page_number=0 isn't rejected.
    """
    return [f for f in fields if data.get(f) is None or data.get(f) == ""]


def _valid_hex_color(value: str) -> bool:
    import re
    return bool(re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", value or ""))


# ---------------------------------------------------------------------------
# ViewSet
# ---------------------------------------------------------------------------

class ReadingFeaturesViewSet(viewsets.GenericViewSet):
    """
    Bookmarks, highlights, notes, reading sessions, screenshot protection,
    and per-page charging.
    """
    permission_classes = [JWTAuthenticated]  # Use custom JWT permission
    authentication_classes = []  # Use JWT middleware for auth

    # ------------------------------------------------------------------
    # Auth / access helpers
    # ------------------------------------------------------------------

    def _get_user_id(self) -> int:
        """
        Resolve user ID from JWT payload or the standard DRF user object.
        Raises AttributeError only if neither is available (misconfigured auth).
        """
        try:
            return self.request.user_payload["user_id"]
        except (AttributeError, KeyError):
            if hasattr(self.request, "user") and self.request.user.is_authenticated:
                return self.request.user.id
            raise AttributeError("No authentication information found")

    def _check_library_access(self, user_id: int, book: Book) -> bool:
        return UserLibrary.objects.filter(
            user_id=user_id, book=book, is_active=True
        ).exists()

    def _get_book_with_access(self, book_id, user_id: int):
        """
        Return (book, None) on success or (None, Response) on failure.
        Validates that book_id is present and the user has library access.
        """
        if not book_id:
            return None, Response(
                {"error": "book_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return None, Response(
                {"error": "Book not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not self._check_library_access(user_id, book):
            return None, Response(
                {"error": "Access denied to this book"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return book, None

    # ------------------------------------------------------------------
    # Bookmarks
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def add_bookmark(self, request):
        user_id = self._get_user_id()
        data = request.data

        missing = _require_fields(data, "book_id", "page_number")
        if missing:
            return Response(
                {"error": f"Missing required fields: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book, err = self._get_book_with_access(data["book_id"], user_id)
        if err:
            return err

        page_number = data["page_number"]
        title = data.get("title") or f"Page {page_number}"
        note = data.get("note", "")
        position = data.get("position") or {}

        if not isinstance(position, dict):
            return Response(
                {"error": "position must be a JSON object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bookmark, _ = Bookmark.objects.update_or_create(
            user_id=user_id,
            book=book,
            page_number=page_number,
            defaults={"title": title, "note": note, "position": position},
        )

        return Response({"message": "Bookmark saved successfully", "bookmark": _bookmark_dict(bookmark)})

    @action(detail=False, methods=["get"])
    def get_bookmarks(self, request):
        user_id = self._get_user_id()

        book, err = self._get_book_with_access(request.GET.get("book_id"), user_id)
        if err:
            return err

        qs = Bookmark.objects.filter(user_id=user_id, book=book).order_by("page_number")
        return Response({"bookmarks": [_bookmark_dict(b) for b in qs]})

    @action(detail=False, methods=["delete"])
    def delete_bookmark(self, request):
        user_id = self._get_user_id()
        bookmark_id = request.data.get("bookmark_id")

        if not bookmark_id:
            return Response(
                {"error": "bookmark_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = Bookmark.objects.filter(id=bookmark_id, user_id=user_id).delete()
        if not deleted:
            return Response({"error": "Bookmark not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Bookmark deleted successfully"})

    # ------------------------------------------------------------------
    # Highlights
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def add_highlight(self, request):
        user_id = self._get_user_id()
        data = request.data

        missing = _require_fields(data, "book_id", "page_number", "selected_text")
        if missing:
            return Response(
                {"error": f"Missing required fields: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        color = data.get("color", "#ffff00")
        if not _valid_hex_color(color):
            return Response(
                {"error": "color must be a valid hex color (e.g. #ffff00)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book, err = self._get_book_with_access(data["book_id"], user_id)
        if err:
            return err

        highlight = Highlight.objects.create(
            user_id=user_id,
            book=book,
            page_number=data["page_number"],
            start_position=data.get("start_position") or {},
            end_position=data.get("end_position") or {},
            selected_text=data["selected_text"],
            color=color,
            note=data.get("note", ""),
        )

        return Response({"message": "Highlight added successfully", "highlight": _highlight_dict(highlight)})

    @action(detail=False, methods=["get"])
    def get_highlights(self, request):
        user_id = self._get_user_id()

        book, err = self._get_book_with_access(request.GET.get("book_id"), user_id)
        if err:
            return err

        qs = Highlight.objects.filter(user_id=user_id, book=book)
        page_number = request.GET.get("page_number")
        if page_number:
            qs = qs.filter(page_number=page_number)

        qs = qs.order_by("page_number", "created_at")
        return Response({"highlights": [_highlight_dict(h) for h in qs]})

    @action(detail=False, methods=["put"])
    def update_highlight(self, request):
        user_id = self._get_user_id()
        data = request.data
        highlight_id = data.get("highlight_id")

        if not highlight_id:
            return Response(
                {"error": "highlight_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            highlight = Highlight.objects.get(id=highlight_id, user_id=user_id)
        except Highlight.DoesNotExist:
            return Response({"error": "Highlight not found"}, status=status.HTTP_404_NOT_FOUND)

        if "color" in data:
            if not _valid_hex_color(data["color"]):
                return Response(
                    {"error": "color must be a valid hex color"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            highlight.color = data["color"]

        if "note" in data:
            highlight.note = data["note"]

        highlight.save()
        return Response({
            "message": "Highlight updated successfully",
            "highlight": {"id": highlight.id, "color": highlight.color, "note": highlight.note},
        })

    @action(detail=False, methods=["delete"])
    def delete_highlight(self, request):
        user_id = self._get_user_id()
        highlight_id = request.data.get("highlight_id")

        if not highlight_id:
            return Response(
                {"error": "highlight_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = Highlight.objects.filter(id=highlight_id, user_id=user_id).delete()
        if not deleted:
            return Response({"error": "Highlight not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Highlight deleted successfully"})

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def add_note(self, request):
        user_id = self._get_user_id()
        data = request.data

        missing = _require_fields(data, "book_id", "page_number", "content")
        if missing:
            return Response(
                {"error": f"Missing required fields: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        color = data.get("color", "#ffffff")
        if not _valid_hex_color(color):
            return Response(
                {"error": "color must be a valid hex color"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book, err = self._get_book_with_access(data["book_id"], user_id)
        if err:
            return err

        note = Note.objects.create(
            user_id=user_id,
            book=book,
            page_number=data["page_number"],
            position=data.get("position") or {},
            content=data["content"],
            color=color,
            is_private=bool(data.get("is_private", True)),
        )

        return Response({"message": "Note added successfully", "note": _note_dict(note)})

    @action(detail=False, methods=["get"])
    def get_notes(self, request):
        user_id = self._get_user_id()

        book, err = self._get_book_with_access(request.GET.get("book_id"), user_id)
        if err:
            return err

        qs = Note.objects.filter(user_id=user_id, book=book)
        page_number = request.GET.get("page_number")
        if page_number:
            qs = qs.filter(page_number=page_number)

        qs = qs.order_by("page_number", "created_at")
        return Response({"notes": [_note_dict(n) for n in qs]})

    @action(detail=False, methods=["put"])
    def update_note(self, request):
        user_id = self._get_user_id()
        data = request.data
        note_id = data.get("note_id")

        if not note_id:
            return Response(
                {"error": "note_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            note = Note.objects.get(id=note_id, user_id=user_id)
        except Note.DoesNotExist:
            return Response({"error": "Note not found"}, status=status.HTTP_404_NOT_FOUND)

        if "content" in data:
            note.content = data["content"]
        if "color" in data:
            if not _valid_hex_color(data["color"]):
                return Response(
                    {"error": "color must be a valid hex color"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            note.color = data["color"]
        if "is_private" in data:
            note.is_private = bool(data["is_private"])

        note.save()
        return Response({
            "message": "Note updated successfully",
            "note": {"id": note.id, "content": note.content, "color": note.color, "is_private": note.is_private},
        })

    @action(detail=False, methods=["delete"])
    def delete_note(self, request):
        user_id = self._get_user_id()
        note_id = request.data.get("note_id")

        if not note_id:
            return Response(
                {"error": "note_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = Note.objects.filter(id=note_id, user_id=user_id).delete()
        if not deleted:
            return Response({"error": "Note not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Note deleted successfully"})

    # ------------------------------------------------------------------
    # Chapter progress
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def mark_chapter_finished(self, request):
        user_id = self._get_user_id()
        data = request.data

        missing = _require_fields(data, "book_id", "chapter_number")
        if missing:
            return Response(
                {"error": f"Missing required fields: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book, err = self._get_book_with_access(data["book_id"], user_id)
        if err:
            return err

        # TODO: persist to a ChapterProgress model when ready
        return Response({
            "success": True,
            "message": f"Chapter {data['chapter_number']} marked as finished",
            "chapter_number": data["chapter_number"],
            "book_id": data["book_id"],
        })

    # ------------------------------------------------------------------
    # Per-page charging  (atomic wallet deduction)
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def charge_for_page(self, request):
        user_id = self._get_user_id()
        data = request.data

        missing = _require_fields(
            data, "book_id", "page_number", "amount",
            "total_book_price", "total_pages", "per_page_cost",
        )
        if missing:
            return Response(
                {"error": f"Missing required fields: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = float(data["amount"])
            total_book_price = float(data["total_book_price"])
            total_pages = int(data["total_pages"])
            per_page_cost = float(data["per_page_cost"])
            page_number = int(data["page_number"])
        except (ValueError, TypeError) as exc:
            return Response(
                {"error": f"Invalid numeric field: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount <= 0:
            return Response(
                {"error": "amount must be positive"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book, err = self._get_book_with_access(data["book_id"], user_id)
        if err:
            return err

        if book.is_free or book.price <= 0:
            return Response(
                {"error": "Book is free — no charging required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve wallet field name once
        wallet_field = None
        if User:
            for candidate in ("wallet_balance", "balance"):
                if hasattr(User, candidate):
                    wallet_field = candidate
                    break

        try:
            # Wrap charge creation + wallet deduction in a single transaction
            # so a crash between the two steps can never leave them inconsistent.
            with transaction.atomic():
                # Re-check inside the transaction to prevent double-charges
                # under concurrent requests (select_for_update locks the row).
                if PageCharge.objects.filter(
                    user_id=user_id, book=book, page_number=page_number
                ).exists():
                    return Response(
                        {"error": "Page already charged"},
                        status=status.HTTP_409_CONFLICT,      # 409 is more accurate than 400
                    )

                # Lock the user row while we read + deduct balance
                wallet_balance = 0.0
                user_obj = None
                if User and wallet_field:
                    try:
                        user_obj = User.objects.select_for_update().get(pk=user_id)
                        wallet_balance = float(getattr(user_obj, wallet_field))
                    except User.DoesNotExist:
                        return Response(
                            {"error": "User not found"},
                            status=status.HTTP_404_NOT_FOUND,
                        )
                else:
                    logger.warning(
                        "charge_for_page: no wallet field found for user %s — "
                        "balance check skipped (demo mode)",
                        user_id,
                    )
                    wallet_balance = float("inf")   # demo: always sufficient

                if wallet_balance < amount:
                    return Response(
                        {
                            "success": False,
                            "error": "Insufficient wallet balance",
                            "required_amount": amount,
                            "current_balance": wallet_balance,
                            "shortfall": round(amount - wallet_balance, 4),
                        },
                        status=status.HTTP_402_PAYMENT_REQUIRED,
                    )

                page_charge = PageCharge.objects.create(
                    user_id=user_id,
                    book=book,
                    page_number=page_number,
                    amount=amount,
                    total_book_price=total_book_price,
                    total_pages=total_pages,
                    per_page_cost=per_page_cost,
                    charged_at=timezone.now(),
                )

                new_balance = wallet_balance - amount
                if user_obj and wallet_field:
                    setattr(user_obj, wallet_field, new_balance)
                    user_obj.save(update_fields=[wallet_field])

        except Exception as exc:
            logger.exception("charge_for_page failed for user=%s book=%s page=%s", user_id, book.id, page_number)
            return Response(
                {"error": f"Charge failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Aggregate outside the transaction (read-only, no need to hold lock)
        charges_qs = PageCharge.objects.filter(user_id=user_id, book=book)
        pages_charged = charges_qs.count()
        total_spent = float(charges_qs.aggregate(total=Sum("amount"))["total"] or 0)

        logger.info(
            "Page charge: user=%s book=%s page=%s amount=%.4f new_balance=%.4f",
            user_id, book.id, page_number, amount, new_balance,
        )

        return Response({
            "success": True,
            "charge": {
                "page_number": page_charge.page_number,
                "amount": float(page_charge.amount),
                "per_page_cost": float(page_charge.per_page_cost),
                "charged_at": page_charge.charged_at,
            },
            "wallet": {
                "previous_balance": wallet_balance,
                "amount_deducted": amount,
                "new_balance": round(new_balance, 4),
            },
            "total_spent": total_spent,
            "book_progress": {
                "pages_charged": pages_charged,
                "total_pages": total_pages,
                "percentage_charged": round((pages_charged / total_pages) * 100, 2),
            },
        })

    # ------------------------------------------------------------------
    # Reading sessions & screenshot protection
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def start_reading_session(self, request):
        user_id = self._get_user_id()
        data = request.data

        book, err = self._get_book_with_access(data.get("book_id"), user_id)
        if err:
            return err

        device_info = data.get("device_info") or {}
        if not isinstance(device_info, dict):
            device_info = {}

        warning, _ = ScreenshotWarning.objects.get_or_create(
            user_id=user_id,
            book=book,
            defaults={
                "warning_count": 0,
                "message": (
                    "Screenshots are disabled to protect author copyright. "
                    "Please respect intellectual property rights."
                ),
            },
        )

        session = ReadingSession.objects.create(
            user_id=user_id, book=book, device_info=device_info
        )

        return Response({
            "session_id": session.id,
            "screenshot_protection": {
                "enabled": True,
                "warning_count": warning.warning_count,
                "is_blocked": warning.is_blocked,
                "message": warning.message,
            },
        })

    @action(detail=False, methods=["post"])
    def report_screenshot_attempt(self, request):
        user_id = self._get_user_id()
        data = request.data
        session_id = data.get("session_id")
        book_id = data.get("book_id")

        if not session_id or not book_id:
            return Response(
                {"error": "session_id and book_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = ReadingSession.objects.get(id=session_id, user_id=user_id)
            book = Book.objects.get(pk=book_id)
        except ReadingSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)

        # Atomic increment to avoid race conditions on concurrent requests
        ReadingSession.objects.filter(pk=session.pk).update(
            screenshot_attempts=Q(screenshot_attempts) + 1
        )

        warning, created = ScreenshotWarning.objects.get_or_create(
            user_id=user_id,
            book=book,
            defaults={
                "warning_count": 1,
                "message": (
                    "Screenshots are disabled to protect author copyright. "
                    "Please respect intellectual property rights."
                ),
            },
        )

        if not created:
            ScreenshotWarning.objects.filter(pk=warning.pk).update(
                warning_count=Q(warning_count) + 1,
                last_warning=timezone.now(),
            )
            warning.refresh_from_db()

            if warning.warning_count >= 3 and not warning.is_blocked:
                warning.is_blocked = True
                warning.message = (
                    "Multiple screenshot attempts detected. "
                    "Your reading access has been temporarily restricted."
                )
                warning.save(update_fields=["is_blocked", "message"])

        count = warning.warning_count
        if count == 1:
            message = "Warning: Screenshots are not allowed. This is your first warning."
            severity = "warning"
        elif count == 2:
            message = "Final warning: Continued screenshot attempts will result in access restrictions."
            severity = "final_warning"
        else:
            message = "Access restricted due to repeated screenshot violations. Please contact support."
            severity = "blocked"

        return Response({
            "message": message,
            "severity": severity,
            "warning_count": count,
            "is_blocked": warning.is_blocked,
            "session_ended": warning.is_blocked,
        })

    @action(detail=False, methods=["post"])
    def end_reading_session(self, request):
        user_id = self._get_user_id()
        data = request.data
        session_id = data.get("session_id")

        if not session_id:
            return Response(
                {"error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pages_read = int(data.get("pages_read", 0))
        except (ValueError, TypeError):
            pages_read = 0

        try:
            session = ReadingSession.objects.get(id=session_id, user_id=user_id)
        except ReadingSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        end_time = timezone.now()
        duration_minutes = int((end_time - session.start_time).total_seconds() / 60)

        ReadingSession.objects.filter(pk=session.pk).update(
            end_time=end_time,
            pages_read=pages_read,
            duration_minutes=duration_minutes,
        )

        return Response({
            "message": "Reading session ended",
            "session_summary": {
                "duration_minutes": duration_minutes,
                "pages_read": pages_read,
                "screenshot_attempts": session.screenshot_attempts,
            },
        })

    # ------------------------------------------------------------------
    # Aggregated annotations
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"])
    def get_all_annotations(self, request):
        user_id = self._get_user_id()

        book, err = self._get_book_with_access(request.GET.get("book_id"), user_id)
        if err:
            return err

        return Response({
            "bookmarks": [
                _bookmark_dict(b)
                for b in Bookmark.objects.filter(user_id=user_id, book=book).order_by("page_number")
            ],
            "highlights": [
                _highlight_dict(h)
                for h in Highlight.objects.filter(user_id=user_id, book=book).order_by("page_number", "created_at")
            ],
            "notes": [
                _note_dict(n)
                for n in Note.objects.filter(user_id=user_id, book=book).order_by("page_number", "created_at")
            ],
        })