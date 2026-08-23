import pytest

from app.domain.services.chinese_numeral import parse_chinese_numeral


@pytest.mark.parametrize(
    "text,expected",
    [
        ("三十", 30),
        ("十", 10),
        ("二十", 20),
        ("五", 5),
        ("一百", 100),
        ("一百二十三", 123),
        ("一百萬", 1_000_000),
        ("三十萬", 300_000),
        ("兩百", 200),
        ("零", 0),
    ],
)
def test_parses_common_amounts(text: str, expected: float):
    assert parse_chinese_numeral(text) == expected


def test_returns_none_for_non_numeral_text():
    assert parse_chinese_numeral("abc") is None
    assert parse_chinese_numeral("元") is None


def test_returns_none_for_empty_string():
    assert parse_chinese_numeral("") is None
