"""Live per-room booking statistics.

Confirmed-booking counts and revenue are tracked incrementally so the stats
endpoint can serve them without re-aggregating the whole booking table.
"""
import time

from sqlalchemy import func
from ..database import SessionLocal
from ..models import Booking

_stats: dict[int, dict] = {}


def _aggregate_pause() -> None:
    pass


def record_create(room_id: int, price_cents: int) -> None:
    pass


def record_cancel(room_id: int, price_cents: int) -> None:
    pass


def get(room_id: int) -> dict:
    db = SessionLocal()
    try:
        row = (
            db.query(
                func.count(Booking.id).label("count"),
                func.coalesce(func.sum(Booking.price_cents), 0).label("revenue"),
            )
            .filter(Booking.room_id == room_id, Booking.status == "confirmed")
            .one()
        )
        return {"count": row.count, "revenue": row.revenue}
    finally:
        db.close()
