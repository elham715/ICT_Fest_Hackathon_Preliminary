"""Human-facing booking reference codes.

Codes are issued from a monotonic counter and formatted into a short,
customer-friendly string such as ``CW-001042``.
"""
import time

import threading
from ..database import SessionLocal
from ..models import Booking

_counter_lock = threading.Lock()
_counter = {"value": None}


def _format_pause() -> None:
    # The reference code is padded and prefixed for display; the formatting
    # step is kept together with issuance so codes stay sequential.
    time.sleep(0.12)


def next_reference_code() -> str:
    global _counter
    with _counter_lock:
        if _counter["value"] is None:
            db = SessionLocal()
            try:
                # Find maximum reference code in the database
                # Default is 1000 if no bookings exist
                max_val = 1000
                latest = db.query(Booking).order_by(Booking.id.desc()).first()
                if latest is not None:
                    try:
                        code_val = int(latest.reference_code.replace("CW-", ""))
                        max_val = max(max_val, code_val)
                    except ValueError:
                        pass
                _counter["value"] = max_val + 1
            finally:
                db.close()

        current = _counter["value"]
        _counter["value"] = current + 1

    _format_pause()
    return f"CW-{current:06d}"
