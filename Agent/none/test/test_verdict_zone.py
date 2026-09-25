"""`Agent/backend/report/qc/reporting/verdict_zone.py` -- MỘT nguồn sự thật
cho phân loại "zone" (EMERGENCY/CAUTION/STANDARD) dùng chung bởi
`web/report_page.py` (badge trên report tĩnh) và `llm/chat.py` (trích lại
nguyên văn badge khi trả lời câu hỏi rủi ro tổng quát).

Mỗi test dưới đây khoá một CA THẬT lấy đúng từ logic gốc trong
`report_page.py`'s `_render_conclusion` trước khi được dời sang đây (23/09)
-- không suy đoán lại quy tắc.
"""

from __future__ import annotations

from Agent.backend.report.qc.reporting import verdict_zone


def test_veto_headline_is_always_danger_even_without_the_other_keywords() -> None:
    assert (
        verdict_zone.classify_verdict_zone("VETO FLOOR TRIGGERED")
        == verdict_zone.ZONE_DANGER
    )


def test_drawdown_high_headline_is_danger() -> None:
    assert (
        verdict_zone.classify_verdict_zone("DRAWDOWN: HIGH · QUALITY: WEAK")
        == verdict_zone.ZONE_DANGER
    )


def test_hidden_risk_headline_is_danger() -> None:
    assert verdict_zone.classify_verdict_zone("HIDDEN RISK") == verdict_zone.ZONE_DANGER


def test_canh_bao_headline_is_warning_not_danger() -> None:
    assert (
        verdict_zone.classify_verdict_zone("CẢNH BÁO: THIN SAMPLE")
        == verdict_zone.ZONE_WARNING
    )


def test_ordinary_headline_is_normal() -> None:
    assert (
        verdict_zone.classify_verdict_zone("DRAWDOWN: LOW · QUALITY: GOOD")
        == verdict_zone.ZONE_NORMAL
    )


def test_classification_is_case_insensitive() -> None:
    assert (
        verdict_zone.classify_verdict_zone("hidden risk")
        == verdict_zone.ZONE_DANGER
    )


def test_blank_headline_never_raises_and_reads_as_normal() -> None:
    assert verdict_zone.classify_verdict_zone("") == verdict_zone.ZONE_NORMAL
    assert verdict_zone.classify_verdict_zone(None) == verdict_zone.ZONE_NORMAL  # type: ignore[arg-type]


def test_badge_text_matches_report_pages_own_wording_exactly() -> None:
    """Câu chữ ở đây PHẢI khớp nguyên văn `report_page.py`'s
    `action_directive` HTML -- lệch một chữ là chat trích sai câu report
    tĩnh đang hiện cho người dùng."""
    assert (
        verdict_zone.zone_badge_text("HIDDEN RISK")
        == "EMERGENCY ZONE -- SEVERE RISK"
    )
    assert (
        verdict_zone.zone_badge_text("CẢNH BÁO: X")
        == "ELEVATED CAUTION ZONE"
    )
    assert (
        verdict_zone.zone_badge_text("DRAWDOWN: LOW · QUALITY: GOOD")
        == "STANDARD RISK ZONE"
    )


# --------------------------------------------------------------------------- #
# `min_zone`: sàn cho báo cáo tổ hợp -- sếp (2026-09-23, M3): một
# PortfolioVerdict HIGH_CORRELATION_CLUSTER phải ép banner tối thiểu ở mức
# cảnh báo, kể cả khi sổ GỘP tự nó đọc DRAWDOWN thấp.
# --------------------------------------------------------------------------- #


def test_min_zone_raises_a_normal_headline_to_warning() -> None:
    assert (
        verdict_zone.classify_verdict_zone(
            "DRAWDOWN: LOW · QUALITY: GOOD", min_zone=verdict_zone.ZONE_WARNING
        )
        == verdict_zone.ZONE_WARNING
    )


def test_min_zone_never_lowers_a_headline_that_is_already_worse() -> None:
    """Sàn, không phải ghi đè -- một headline đã DANGER không được hạ."""
    assert (
        verdict_zone.classify_verdict_zone(
            "HIDDEN RISK", min_zone=verdict_zone.ZONE_WARNING
        )
        == verdict_zone.ZONE_DANGER
    )


def test_omitting_min_zone_keeps_the_old_behaviour_exactly() -> None:
    """Mặc định không đổi hành vi cũ -- mọi report đơn (không có
    PortfolioVerdict) phải khớp nguyên văn kết quả trước khi tham số này
    tồn tại."""
    for headline in (
        "VETO FLOOR TRIGGERED",
        "DRAWDOWN: HIGH · QUALITY: WEAK",
        "HIDDEN RISK",
        "CẢNH BÁO: X",
        "DRAWDOWN: LOW · QUALITY: GOOD",
        "",
    ):
        assert verdict_zone.classify_verdict_zone(
            headline
        ) == verdict_zone.classify_verdict_zone(headline, min_zone=verdict_zone.ZONE_NORMAL)


def test_badge_text_respects_min_zone_too() -> None:
    assert (
        verdict_zone.zone_badge_text(
            "DRAWDOWN: LOW · QUALITY: GOOD", min_zone=verdict_zone.ZONE_WARNING
        )
        == "ELEVATED CAUTION ZONE"
    )
