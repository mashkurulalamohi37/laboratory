"""Bangladesh mobile number normalisation to E.164 (+8801XXXXXXXXX)."""

from __future__ import annotations

import re

_BD_MOBILE = re.compile(r"^(?:\+?880|0)?(1[3-9]\d{8})$")


class InvalidPhone(ValueError):
    pass


def normalize_bd_phone(raw: str) -> str:
    """Accepts 01XXXXXXXXX, 8801XXXXXXXXX, +8801XXXXXXXXX, with spaces/dashes.

    Bangla digits are converted to ASCII first.
    """
    translated = raw.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    compact = re.sub(r"[\s\-().]", "", translated)
    match = _BD_MOBILE.match(compact)
    if not match:
        raise InvalidPhone("Enter a valid Bangladesh mobile number (e.g. 01712345678).")
    return f"+880{match.group(1)}"


def mask_phone(phone: str) -> str:
    """+8801712345678 → +88017•••••678 (safe for display and logs)."""
    if len(phone) < 8:
        return "•••"
    return f"{phone[:6]}{'•' * (len(phone) - 9)}{phone[-3:]}"
