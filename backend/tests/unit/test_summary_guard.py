from app.domain.services.summary_guard import find_ungrounded_amounts_and_dates


def test_grounded_amount_passes():
    original = "總價款為新臺幣一百萬元整，分三期支付，簽約後支付百分之三十。"
    summary = "總價款分三期支付，簽約後付款百分之三十。"
    assert find_ungrounded_amounts_and_dates(original, summary) == []


def test_ungrounded_amount_fails():
    original = "總價款分三期支付。"
    summary = "總價款為新臺幣兩百萬元，分三期支付。"
    ungrounded = find_ungrounded_amounts_and_dates(original, summary)
    assert ungrounded  # 原文沒有具體金額，摘要卻臆造了金額


def test_ungrounded_date_fails():
    original = "甲方應於乙方交付成果後完成驗收。"
    summary = "甲方應於民國114年5月1日前完成驗收。"
    ungrounded = find_ungrounded_amounts_and_dates(original, summary)
    assert ungrounded


def test_grounded_date_passes():
    original = "本合約應於民國114年5月1日簽署生效。"
    summary = "本合約於民國114年5月1日生效。"
    assert find_ungrounded_amounts_and_dates(original, summary) == []


def test_fullwidth_digits_are_normalized_before_comparison():
    original = "保固期間為交付後一年，逾期罰款為每日千分之一。"
    summary = "保固期間為一年，逾期罰款為每日千分之一。"
    assert find_ungrounded_amounts_and_dates(original, summary) == []


def test_summary_without_amounts_or_dates_always_passes():
    original = "乙方應依附件所載規格開發系統。"
    summary = "乙方須依附件規格完成系統開發。"
    assert find_ungrounded_amounts_and_dates(original, summary) == []


def test_dollar_prefix_amount_without_trailing_unit_is_detected():
    original = "簽約金為新臺幣一百萬元整。"
    summary = "簽約金為 NT$1,000 整。"
    assert find_ungrounded_amounts_and_dates(original, summary) != []


def test_dollar_prefix_amount_grounded_when_present_in_original():
    original = "簽約金為 NT$1,000。"
    summary = "簽約金為 NT$1,000。"
    assert find_ungrounded_amounts_and_dates(original, summary) == []


def test_arabic_percentage_is_detected():
    original = "逾期違約金為每日千分之一。"
    summary = "逾期違約金為百分之30。"
    assert find_ungrounded_amounts_and_dates(original, summary) != []


def test_arabic_percentage_grounded_when_present_in_original():
    original = "簽約後支付百分之30。"
    summary = "簽約後支付百分之30貨款。"
    assert find_ungrounded_amounts_and_dates(original, summary) == []


def test_western_calendar_date_marker_is_detected():
    original = "甲方應於乙方交付成果後完成驗收。"
    summary = "甲方應於西元2026年5月1日前完成驗收。"
    assert find_ungrounded_amounts_and_dates(original, summary) != []


def test_chinese_percentage_paraphrased_as_arabic_percent_sign_is_grounded():
    # Regression: observed live during spec.md AC2 manual review — the LLM
    # commonly rewrites 百分之三十 as 30%; same value, must not be flagged.
    original = (
        "第三條　付款方式\n總價款為新臺幣一百萬元整，分三期支付。\n"
        "1. 簽約後支付百分之三十。\n2. 期中驗收支付百分之四十。\n3. 驗收合格支付百分之三十。"
    )
    summary = "總價款為新臺幣一百萬元，分為簽約後支付30%、期中驗收支付40%及驗收合格支付30%三期支付。"
    assert find_ungrounded_amounts_and_dates(original, summary) == []


def test_different_percentage_value_is_still_flagged():
    original = "簽約後支付百分之三十。"
    summary = "簽約後支付35%。"
    assert find_ungrounded_amounts_and_dates(original, summary) != []
