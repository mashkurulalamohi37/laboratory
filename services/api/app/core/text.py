"""Text normalisation for slugs and search input (English and Bangla)."""

from __future__ import annotations

import re
import unicodedata

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
CODE_PATTERN = r"^[A-Z0-9][A-Z0-9_-]*$"

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_SPACE = re.compile(r"\s+")
# Keep letters/digits of any script (incl. Bangla vowel signs, which are combining marks)
# and split on everything else.
_TOKEN_SPLIT = re.compile(r"[^\wঀ-৿]+|_+")
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

MAX_QUERY_LENGTH = 80


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return _SLUG_STRIP.sub("-", ascii_value.lower()).strip("-")


def normalize_query(raw: str) -> str:
    """Lower-cased, NFC-normalised, single-spaced, Bangla digits mapped, length-capped."""
    value = unicodedata.normalize("NFC", raw).translate(_BN_DIGITS).lower()
    return _SPACE.sub(" ", value).strip()[:MAX_QUERY_LENGTH]


def query_tokens(normalized: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(normalized) if t and t != "_"]


_TS_TOKEN = re.compile(r"[a-z0-9]+")


def prefix_tsquery(normalized: str) -> str | None:
    """Build a safe `to_tsquery` string where every token is a prefix match (`tok:*`).

    Only Latin letters and digits are used: tokens therefore cannot carry tsquery operators,
    and Bangla (which PostgreSQL's parser splits at vowel signs) is matched by trigram/LIKE
    and the synonym table instead."""
    tokens = [t for t in query_tokens(normalized) if _TS_TOKEN.fullmatch(t)]
    if not tokens:
        return None
    return " & ".join(f"{t}:*" for t in tokens[:8])
