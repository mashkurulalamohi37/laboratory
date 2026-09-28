import pytest

from app.core.phone import InvalidPhone, mask_phone, normalize_bd_phone


@pytest.mark.parametrize(
    "raw",
    ["01712345678", "8801712345678", "+8801712345678", "017-1234 5678", "০১৭১২৩৪৫৬৭৮"],
)
def test_normalizes_valid_bd_mobile_numbers(raw: str) -> None:
    assert normalize_bd_phone(raw) == "+8801712345678"


@pytest.mark.parametrize(
    "raw",
    ["", "0171234567", "017123456789", "01212345678", "+9101712345678", "abc", "+880 2 9123456"],
)
def test_rejects_invalid_numbers(raw: str) -> None:
    with pytest.raises(InvalidPhone):
        normalize_bd_phone(raw)


def test_mask_phone_hides_middle_digits() -> None:
    masked = mask_phone("+8801712345678")
    assert masked.startswith("+88017") and masked.endswith("678")
    assert "12345" not in masked


def test_escape_like_treats_wildcards_literally() -> None:
    from app.core.sql import escape_like

    assert escape_like("50%_off\\") == r"50\%\_off\\"
