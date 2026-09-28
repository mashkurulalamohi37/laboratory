"""Pure helpers behind search, the centre locator and CMS validation."""

from __future__ import annotations

from datetime import datetime, time

import pytest
from pydantic import ValidationError

from app.core.text import normalize_query, prefix_tsquery, query_tokens, slugify
from app.core.timeutil import DHAKA_TZ
from app.modules.catalog.schemas import Price, SynonymIn
from app.modules.centre.models import CentreHours
from app.modules.centre.schemas import CentreIn
from app.modules.centre.service import haversine_km, is_open
from app.modules.cms.schemas import BannerIn


class TestQueryText:
    def test_normalize_collapses_case_space_and_bangla_digits(self) -> None:
        assert normalize_query("  Vitamin   D ") == "vitamin d"
        assert normalize_query("মিরপুর ১০") == "মিরপুর 10"
        assert len(normalize_query("x" * 500)) == 80

    def test_tokens_keep_bangla_words_whole(self) -> None:
        # Vowel signs and virama are combining marks; they must not split words.
        assert query_tokens(normalize_query("রক্ত পরীক্ষা")) == ["রক্ত", "পরীক্ষা"]

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("sugar", "sugar:*"),
            ("blood sugar", "blood:* & sugar:*"),
            ("a & b | !c", "a:* & b:* & c:*"),
            ("x'):* | y", "x:* & y:*"),
            ("সুগার", None),  # Bangla goes through trigram/synonyms, not the tsquery
            ("!!!", None),
        ],
    )
    def test_prefix_tsquery_cannot_inject_operators(self, raw: str, expected: str | None) -> None:
        assert prefix_tsquery(normalize_query(raw)) == expected

    def test_slugify(self) -> None:
        assert slugify("Cox's Bazar") == "cox-s-bazar"
        assert slugify("  Uttara Sector 7 ") == "uttara-sector-7"


class TestOpeningHours:
    week = [
        CentreHours(weekday=d, opens_at=time(7), closes_at=time(21)) for d in (5, 6, 0, 1, 2, 3)
    ] + [CentreHours(weekday=4, opens_at=time(15), closes_at=time(21))]

    @pytest.mark.parametrize(
        ("local", "expected"),
        [
            (datetime(2026, 9, 27, 6, 59, tzinfo=DHAKA_TZ), False),  # Sunday before opening
            (datetime(2026, 9, 27, 7, 0, tzinfo=DHAKA_TZ), True),
            (datetime(2026, 9, 27, 20, 59, tzinfo=DHAKA_TZ), True),
            (datetime(2026, 9, 27, 21, 0, tzinfo=DHAKA_TZ), False),  # closing time is exclusive
            (datetime(2026, 10, 2, 10, 0, tzinfo=DHAKA_TZ), False),  # Friday morning
            (datetime(2026, 10, 2, 16, 0, tzinfo=DHAKA_TZ), True),  # Friday afternoon
        ],
    )
    def test_is_open(self, local: datetime, expected: bool) -> None:
        assert is_open(self.week, local, holiday=False) is expected

    def test_holiday_closes_everything(self) -> None:
        assert not is_open(self.week, datetime(2026, 9, 27, 10, tzinfo=DHAKA_TZ), holiday=True)

    def test_overlapping_hours_are_rejected(self) -> None:
        base = {
            "code": "C1",
            "slug": "c1",
            "name": "Centre",
            "branch_id": "01a0e389-0000-7000-8000-000000000000",
            "address": "Somewhere 1",
            "district_id": "01a0e389-0000-7000-8000-000000000000",
        }
        with pytest.raises(ValidationError, match="overlap"):
            CentreIn(
                **base,
                hours=[
                    {"weekday": 0, "opens_at": "08:00", "closes_at": "13:00"},
                    {"weekday": 0, "opens_at": "12:30", "closes_at": "18:00"},
                ],
            )
        split_shift = CentreIn(
            **base,
            hours=[
                {"weekday": 0, "opens_at": "08:00", "closes_at": "13:00"},
                {"weekday": 0, "opens_at": "13:00", "closes_at": "18:00"},
            ],
        )
        assert len(split_shift.hours) == 2


def test_haversine_dhaka_to_chattogram() -> None:
    assert 210 < haversine_km(23.8103, 90.4125, 22.3569, 91.7832) < 220
    assert haversine_km(23.8, 90.4, 23.8, 90.4) == 0


class TestMoneyAndContent:
    def test_discount_percent(self) -> None:
        assert Price(amount=15000, mrp=20000).discount_percent == 25
        assert Price(amount=20000, mrp=20000).discount_percent == 0
        assert Price(amount=0, mrp=0).discount_percent == 0

    @pytest.mark.parametrize("href", ["/packages", "/tests/cbc?x=1#top", "https://example.com/a"])
    def test_safe_banner_links(self, href: str) -> None:
        assert BannerIn(title="Offer", cta_label="Go", cta_href=href).cta_href == href

    @pytest.mark.parametrize(
        "href", ["javascript:alert(1)", "//evil.example", "http://x.example", "/a b", "data:x"]
    )
    def test_unsafe_banner_links(self, href: str) -> None:
        with pytest.raises(ValidationError):
            BannerIn(title="Offer", cta_label="Go", cta_href=href)

    def test_synonym_terms_are_normalised(self) -> None:
        body = SynonymIn(
            term="  Blood  Sugar ",
            target_type="TEST",
            target_id="01a0e389-0000-7000-8000-000000000000",  # type: ignore[arg-type]
        )
        assert body.term == "blood sugar"
