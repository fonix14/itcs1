from __future__ import annotations

from datetime import datetime, timedelta


_BACKOFF = [
    60,
    5 * 60,
    15 * 60,
    60 * 60,
    3 * 60 * 60,
    6 * 60 * 60,
    12 * 60 * 60,
    24 * 60 * 60,
    48 * 60 * 60,
    72 * 60 * 60,
]


def next_retry(attempts: int, now: datetime) -> datetime:
    """Compute next retry time.

    attempts: already incremented attempts value (1..)
    """
    idx = max(0, min(attempts - 1, len(_BACKOFF) - 1))
    return now + timedelta(seconds=_BACKOFF[idx])
