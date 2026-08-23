import pytest

from app.domain.services.conservative_language_guard import find_banned_phrase


@pytest.mark.parametrize(
    "text",
    [
        "本條無效，建議刪除。",
        "乙方一定會賠償甲方損失。",
        "此條款可保證勝訴。",
        "違約方絕對須負全責。",
        "逾期必然構成違約。",
        "毫無疑問此條款對乙方不利。",
    ],
)
def test_detects_banned_phrases(text: str):
    assert find_banned_phrase(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "可能有疑慮，建議確認賠償責任上限是否合理。",
        "可考慮協商修改逾期罰則的計算方式。",
        "建議確認保固範圍是否明確。",
    ],
)
def test_passes_conservative_language(text: str):
    assert find_banned_phrase(text) is None
