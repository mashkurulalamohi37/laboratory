"""Reference-range selection and flagging (pure functions, no I/O).

Selection rule (docs/database.md): among the ranges whose criteria all match the subject,
the most specific wins, compared in this order:

    lab > method > sample type > sex > narrower age band

A criterion left empty on a range means "any". Two ranges with identical criteria cannot
overlap in age band and validity (database exclusion constraint), so the winner is unique
for real data; the final tie-breakers only make the result deterministic.

Flags (used from Phase 5): L/H outside [low, high]; CL/CH at or beyond the critical limits.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Flag(StrEnum):
    NORMAL = "N"
    LOW = "L"
    HIGH = "H"
    CRITICAL_LOW = "CL"
    CRITICAL_HIGH = "CH"


@dataclass(frozen=True, slots=True)
class RangeRule:
    id: uuid.UUID
    sex: str | None
    age_min_days: int
    age_max_days: int | None
    sample_type_id: uuid.UUID | None
    lab_id: uuid.UUID | None
    method: str | None
    effective_from: date
    effective_to: date | None
    low: Decimal | None = None
    high: Decimal | None = None
    critical_low: Decimal | None = None
    critical_high: Decimal | None = None
    text_normal: str | None = None


@dataclass(frozen=True, slots=True)
class Subject:
    """Who/what is being evaluated. `sex` is the patient's recorded sex (M, F or O)."""

    sex: str | None
    age_days: int
    on: date
    sample_type_id: uuid.UUID | None = None
    lab_id: uuid.UUID | None = None
    method: str | None = None


def _norm(method: str | None) -> str | None:
    return method.strip().lower() if method and method.strip() else None


def matches(rule: RangeRule, subject: Subject) -> bool:  # noqa: PLR0911 (one exit per criterion)
    if rule.sex is not None and rule.sex != subject.sex:
        return False
    if subject.age_days < rule.age_min_days:
        return False
    if rule.age_max_days is not None and subject.age_days >= rule.age_max_days:
        return False
    if rule.sample_type_id is not None and rule.sample_type_id != subject.sample_type_id:
        return False
    if rule.lab_id is not None and rule.lab_id != subject.lab_id:
        return False
    if _norm(rule.method) is not None and _norm(rule.method) != _norm(subject.method):
        return False
    if subject.on < rule.effective_from:
        return False
    return rule.effective_to is None or subject.on < rule.effective_to


def specificity(rule: RangeRule) -> tuple[int, int, int, int, int]:
    """Larger is more specific. The age component prefers narrower bands (open-ended
    bands count as the widest)."""
    span = (rule.age_max_days - rule.age_min_days) if rule.age_max_days is not None else None
    return (
        int(rule.lab_id is not None),
        int(_norm(rule.method) is not None),
        int(rule.sample_type_id is not None),
        int(rule.sex is not None),
        -(span if span is not None else 10**9),
    )


def select_range(rules: Iterable[RangeRule], subject: Subject) -> RangeRule | None:
    candidates = [r for r in rules if matches(r, subject)]
    if not candidates:
        return None
    # Deterministic tie-break: the most recently effective rule, then the id.
    return max(candidates, key=lambda r: (specificity(r), r.effective_from, r.id.int))


def evaluate(value: Decimal, rule: RangeRule) -> Flag:
    """Flag a numeric result against its matched range."""
    if rule.critical_low is not None and value <= rule.critical_low:
        return Flag.CRITICAL_LOW
    if rule.critical_high is not None and value >= rule.critical_high:
        return Flag.CRITICAL_HIGH
    if rule.low is not None and value < rule.low:
        return Flag.LOW
    if rule.high is not None and value > rule.high:
        return Flag.HIGH
    return Flag.NORMAL


def _same_criteria(a: RangeRule, b: RangeRule) -> bool:
    return (
        a.sex == b.sex
        and a.sample_type_id == b.sample_type_id
        and a.lab_id == b.lab_id
        and _norm(a.method) == _norm(b.method)
    )


def _overlap(a_lo: int, a_hi: int | None, b_lo: int, b_hi: int | None) -> bool:
    """Half-open intervals [lo, hi) with hi=None meaning unbounded."""
    return (a_hi is None or b_lo < a_hi) and (b_hi is None or a_lo < b_hi)


def find_conflict(candidate: RangeRule, existing: Sequence[RangeRule]) -> RangeRule | None:
    """The first existing rule that would make `candidate` ambiguous (same criteria,
    overlapping age band and validity). Mirrors the database exclusion constraint so the
    API can answer with a clear message before hitting it."""
    for other in existing:
        if other.id == candidate.id or not _same_criteria(candidate, other):
            continue
        age = _overlap(
            candidate.age_min_days, candidate.age_max_days, other.age_min_days, other.age_max_days
        )
        days = _overlap(
            candidate.effective_from.toordinal(),
            candidate.effective_to.toordinal() if candidate.effective_to else None,
            other.effective_from.toordinal(),
            other.effective_to.toordinal() if other.effective_to else None,
        )
        if age and days:
            return other
    return None
