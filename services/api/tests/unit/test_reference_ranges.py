"""Reference-range selection is clinical-safety critical (risk R3): exhaustive cases."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.modules.catalog.ranges import (
    Flag,
    RangeRule,
    Subject,
    evaluate,
    find_conflict,
    matches,
    select_range,
)

YEAR = 365
TODAY = date(2026, 9, 27)
SERUM, PLASMA = uuid.uuid4(), uuid.uuid4()
LAB_A, LAB_B = uuid.uuid4(), uuid.uuid4()


def rule(**kw: object) -> RangeRule:
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "sex": None,
        "age_min_days": 0,
        "age_max_days": None,
        "sample_type_id": None,
        "lab_id": None,
        "method": None,
        "effective_from": date(2020, 1, 1),
        "effective_to": None,
        "low": Decimal("3.5"),
        "high": Decimal("5.1"),
    }
    base.update(kw)
    return RangeRule(**base)  # type: ignore[arg-type]


def adult(sex: str = "F", **kw: object) -> Subject:
    base: dict[str, object] = {"sex": sex, "age_days": 40 * YEAR, "on": TODAY}
    base.update(kw)
    return Subject(**base)  # type: ignore[arg-type]


class TestMatches:
    def test_generic_rule_matches_anyone(self) -> None:
        assert matches(rule(), adult("M"))
        assert matches(rule(), adult("O"))
        assert matches(rule(), Subject(sex=None, age_days=0, on=TODAY))

    def test_sex_specific_rule_excludes_other_sexes(self) -> None:
        male = rule(sex="M")
        assert matches(male, adult("M"))
        assert not matches(male, adult("F"))
        assert not matches(male, adult("O"))
        assert not matches(male, Subject(sex=None, age_days=40 * YEAR, on=TODAY))

    @pytest.mark.parametrize(
        ("age", "expected"),
        [(18 * YEAR - 1, False), (18 * YEAR, True), (65 * YEAR - 1, True), (65 * YEAR, False)],
    )
    def test_age_band_is_half_open(self, age: int, expected: bool) -> None:
        band = rule(age_min_days=18 * YEAR, age_max_days=65 * YEAR)
        assert matches(band, adult(age_days=age)) is expected

    def test_sample_lab_and_method_must_match_when_set(self) -> None:
        assert not matches(rule(sample_type_id=SERUM), adult(sample_type_id=PLASMA))
        assert matches(rule(sample_type_id=SERUM), adult(sample_type_id=SERUM))
        assert not matches(rule(lab_id=LAB_A), adult(lab_id=LAB_B))
        assert not matches(rule(lab_id=LAB_A), adult())
        assert matches(rule(method=" ISE "), adult(method="ise"))
        assert not matches(rule(method="ISE"), adult(method="Flame"))

    @pytest.mark.parametrize(
        ("on", "expected"),
        [
            (date(2025, 12, 31), False),
            (date(2026, 1, 1), True),
            (date(2026, 6, 30), True),
            (date(2026, 7, 1), False),
        ],
    )
    def test_validity_window_is_half_open(self, on: date, expected: bool) -> None:
        window = rule(effective_from=date(2026, 1, 1), effective_to=date(2026, 7, 1))
        assert matches(window, adult(on=on)) is expected


class TestSelection:
    def test_no_candidates(self) -> None:
        assert select_range([rule(sex="M")], adult("F")) is None
        assert select_range([], adult()) is None

    def test_sex_specific_beats_generic(self) -> None:
        generic, female = rule(), rule(sex="F")
        assert select_range([generic, female], adult("F")) is female
        assert select_range([generic, female], adult("M")) is generic

    def test_precedence_lab_over_method_over_sample_over_sex(self) -> None:
        by_sex = rule(sex="F")
        by_sample = rule(sample_type_id=SERUM)
        by_method = rule(method="ISE")
        by_lab = rule(lab_id=LAB_A)
        subject = adult("F", sample_type_id=SERUM, method="ISE", lab_id=LAB_A)
        pool = [by_sex, by_sample, by_method, by_lab]
        assert select_range(pool, subject) is by_lab
        assert select_range(pool[:3], subject) is by_method
        assert select_range(pool[:2], subject) is by_sample
        assert select_range(pool[:1], subject) is by_sex

    def test_narrower_age_band_wins_at_equal_criteria(self) -> None:
        # The database rejects this overlap; the matcher must still resolve it predictably.
        open_ended = rule(sex="M", age_min_days=0)
        child = rule(sex="M", age_min_days=0, age_max_days=12 * YEAR)
        assert select_range([open_ended, child], adult("M", age_days=5 * YEAR)) is child
        assert select_range([open_ended, child], adult("M", age_days=30 * YEAR)) is open_ended

    def test_paediatric_and_adult_bands(self) -> None:
        neonate = rule(age_min_days=0, age_max_days=28)
        infant = rule(age_min_days=28, age_max_days=YEAR)
        child = rule(age_min_days=YEAR, age_max_days=18 * YEAR)
        grown = rule(age_min_days=18 * YEAR)
        pool = [grown, child, infant, neonate]
        assert select_range(pool, adult(age_days=3)) is neonate
        assert select_range(pool, adult(age_days=28)) is infant
        assert select_range(pool, adult(age_days=10 * YEAR)) is child
        assert select_range(pool, adult(age_days=70 * YEAR)) is grown

    def test_superseded_range_is_ignored(self) -> None:
        old = rule(effective_from=date(2020, 1, 1), effective_to=date(2026, 1, 1))
        new = rule(effective_from=date(2026, 1, 1), low=Decimal("3.6"))
        assert select_range([old, new], adult(on=date(2025, 6, 1))) is old
        assert select_range([old, new], adult(on=TODAY)) is new


class TestEvaluate:
    potassium = rule(
        low=Decimal("3.5"),
        high=Decimal("5.1"),
        critical_low=Decimal("2.5"),
        critical_high=Decimal("6.5"),
    )

    @pytest.mark.parametrize(
        ("value", "flag"),
        [
            ("2.4", Flag.CRITICAL_LOW),
            ("2.5", Flag.CRITICAL_LOW),
            ("3.0", Flag.LOW),
            ("3.5", Flag.NORMAL),
            ("5.1", Flag.NORMAL),
            ("5.8", Flag.HIGH),
            ("6.5", Flag.CRITICAL_HIGH),
            ("6.8", Flag.CRITICAL_HIGH),  # user story US-3
        ],
    )
    def test_potassium(self, value: str, flag: Flag) -> None:
        assert evaluate(Decimal(value), self.potassium) is flag

    def test_one_sided_range(self) -> None:
        upper_only = rule(low=None, high=Decimal("200"))
        assert evaluate(Decimal("1"), upper_only) is Flag.NORMAL
        assert evaluate(Decimal("201"), upper_only) is Flag.HIGH


class TestConflicts:
    def test_overlapping_band_with_same_criteria_conflicts(self) -> None:
        existing = [rule(sex="M", age_min_days=0, age_max_days=18 * YEAR)]
        clash = rule(sex="M", age_min_days=10 * YEAR, age_max_days=None)
        assert find_conflict(clash, existing) is existing[0]

    def test_adjacent_bands_do_not_conflict(self) -> None:
        existing = [rule(sex="M", age_min_days=0, age_max_days=18 * YEAR)]
        assert find_conflict(rule(sex="M", age_min_days=18 * YEAR), existing) is None

    def test_different_criteria_do_not_conflict(self) -> None:
        existing = [rule(sex="M")]
        assert find_conflict(rule(sex="F"), existing) is None
        assert find_conflict(rule(sex="M", method="ISE"), existing) is None
        assert find_conflict(rule(), existing) is None

    def test_sequential_validity_does_not_conflict(self) -> None:
        existing = [rule(effective_to=date(2026, 1, 1))]
        assert find_conflict(rule(effective_from=date(2026, 1, 1)), existing) is None
        assert find_conflict(rule(effective_from=date(2025, 12, 31)), existing) is existing[0]

    def test_updating_a_rule_does_not_conflict_with_itself(self) -> None:
        current = rule()
        edited = replace(current, low=None)
        assert find_conflict(edited, [current]) is None
