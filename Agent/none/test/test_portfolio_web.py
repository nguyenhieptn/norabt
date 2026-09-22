"""Tầng web của báo cáo tổ hợp: một trang, cùng renderer, cùng 3 tab.

Điều được khoá ở đây không phải là "route trả 200". Là: trang tổ hợp đi qua
ĐÚNG `render_bot_report_html` mà trang một bot đi qua, nên nó không thể lệch
style; và không route nào ở đây được phép bịa ra một con số khi thiếu dữ liệu.
"""

from __future__ import annotations

import pytest

from Agent.backend.pipeline_portfolio import (
    PortfolioBotRequest,
    PortfolioSupervisionPipeline,
)
from Agent.backend.web.data import (
    InvalidCodeError,
    PORTFOLIO_MAX_CODES,
    _full_result,
    validate_portfolio_codes,
)
from Agent.backend.web.portfolio_section import (
    inject_portfolio_section,
    render_portfolio_section,
)
from Agent.none.test.conftest import FIXED_AS_OF_MS
from Agent.none.test.test_web_app import _client_for, _service_with, _StubBotSource

_MEMBERS = (
    PortfolioBotRequest(asset="BTC", bot_folder_name="bot_35F888C7BB441B2B"),
    PortfolioBotRequest(asset="ETH", bot_folder_name="bot_6F262ADB3B44266C"),
    PortfolioBotRequest(asset="WBTC", bot_folder_name="bot_58D7D205FB591484"),
)


@pytest.fixture(scope="module")
def portfolio_payload():
    """One real portfolio payload, built from committed fixtures.

    Module-scoped because it costs three ledger reads plus a merged
    simulation, and every test below asks a different question of the same
    payload.
    """
    outcome = PortfolioSupervisionPipeline(persist_history=False, max_workers=3).run(
        _MEMBERS,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=300,
        simulation_horizon=100,
        portfolio_iterations=400,
    )
    payload = _full_result(outcome.portfolio.portfolio_id, outcome.combined)
    payload["portfolio_id"] = outcome.portfolio.portfolio_id
    payload["portfolio"] = outcome.portfolio.model_dump(mode="json")
    return payload


# --------------------------------------------------------------------------- #
# Phân tách mã: cái ô nhập duy nhất
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "raw",
    ["AAA,BBB", "AAA BBB", "AAA, BBB", "AAA;BBB", "AAA\nBBB", ["AAA", "BBB"]],
)
def test_every_separator_a_person_actually_types_is_accepted(raw) -> None:
    assert validate_portfolio_codes(raw) == ["AAA", "BBB"]


def test_the_same_bot_twice_is_one_position() -> None:
    """Đếm hai lần vừa nhân đôi trọng số vừa tạo ra tương quan hoàn hảo giả."""
    assert validate_portfolio_codes("AAA, BBB, AAA") == ["AAA", "BBB"]


def test_one_code_is_not_a_portfolio() -> None:
    with pytest.raises(InvalidCodeError, match="at least 2"):
        validate_portfolio_codes("AAA")


def test_too_many_members_is_refused_before_any_fetch() -> None:
    codes = [f"CODE{index}" for index in range(PORTFOLIO_MAX_CODES + 1)]
    with pytest.raises(InvalidCodeError, match="At most"):
        validate_portfolio_codes(codes)


def test_a_path_traversal_attempt_is_rejected_like_any_other_code() -> None:
    with pytest.raises(InvalidCodeError):
        validate_portfolio_codes("AAA, ../../etc/passwd")


# --------------------------------------------------------------------------- #
# Trang: cùng renderer, cùng 3 tab
# --------------------------------------------------------------------------- #


def test_the_portfolio_page_is_the_single_bot_page_plus_one_block(
    portfolio_payload,
) -> None:
    """Điều kiện nghiệm thu của "cùng 1 style": cùng renderer, cùng 3 tab."""
    from Agent.backend.web.report_page import render_bot_report_html

    document = render_bot_report_html(portfolio_payload)
    full = inject_portfolio_section(document, portfolio_payload["portfolio"])

    for panel in ("panel-report", "panel-market", "panel-trades"):
        assert f'id="{panel}"' in full
    assert 'id="portfolio-correlation"' in full
    # Khối thêm vào KHÔNG được đụng tới phần biểu đồ của trang gốc.
    assert full.count("<svg") == document.count("<svg")
    # Và nó nằm trong tab đầu, nơi người dùng thường dừng lại.
    assert (
        full.index('id="panel-report"')
        < full.index('id="portfolio-correlation"')
        < full.index('id="panel-market"')
    )


def test_the_block_survives_a_renderer_that_moved_its_anchor(
    portfolio_payload,
) -> None:
    """Mất mốc chèn phải thành "khối nằm thấp hơn", không phải "khối biến mất".

    `report_page.py` đang được viết lại; một phát hiện đầu bài của báo cáo tổ
    hợp không được phép im lặng rơi mất vì đổi markup.
    """
    document = "<html><body><main>report</main></body></html>"
    full = inject_portfolio_section(document, portfolio_payload["portfolio"])
    assert 'id="portfolio-correlation"' in full
    assert full.index("portfolio-correlation") < full.index("</main>")


def test_bot_names_from_okx_are_escaped(portfolio_payload) -> None:
    hostile = dict(portfolio_payload["portfolio"])
    hostile["members"] = [
        {**hostile["members"][0], "label": '<img src=x onerror="alert(1)">'}
    ]
    html = render_portfolio_section(hostile)
    assert "<img src=x" not in html
    assert "&lt;img src=x" in html


def test_a_missing_measurement_reads_as_missing_not_as_zero(
    portfolio_payload,
) -> None:
    blank = dict(portfolio_payload["portfolio"])
    blank["joint_simulation"] = None
    blank["correlation"] = {
        **blank["correlation"],
        "average_pearson": None,
        "max_pearson": None,
    }
    html = render_portfolio_section(blank)
    assert "&mdash;" in html
    assert "0.00" not in html.split("Average pairwise correlation")[1][:200]


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


def _client(tmp_path):
    return _client_for(_service_with(_StubBotSource(), data_dir=tmp_path))


def test_portfolio_history_endpoint_returns_a_list_never_a_sample(tmp_path) -> None:
    """Rỗng là rỗng. Một hàng minh hoạ trong bảng rủi ro của quản trị viên
    trông y hệt một hàng đo thật."""
    response = _client(tmp_path).get("/api/portfolios")
    assert response.status_code == 200
    body = response.json()
    assert body["portfolios"] == []
    assert body["count"] == 0


def test_an_invalid_portfolio_id_never_reaches_a_lookup(tmp_path) -> None:
    for bad in ("../../etc/passwd", "NOTAPORT", "PORT_zzzz", "PORT_"):
        response = _client(tmp_path).get(f"/portfolio/{bad}")
        assert response.status_code in (400, 404), bad


def test_an_unknown_portfolio_is_a_404_not_a_fresh_okx_run(tmp_path) -> None:
    """Mở một link cũ không được phép biến thành N lượt gọi OKX."""
    response = _client(tmp_path).get("/portfolio/PORT_ABCDEF012345")
    assert response.status_code == 404
    assert "no longer held" in response.text


def test_a_cached_run_renders_the_full_page(tmp_path, portfolio_payload) -> None:
    service = _service_with(_StubBotSource(), data_dir=tmp_path)
    portfolio_id = portfolio_payload["portfolio_id"]
    service._portfolio_by_id.set(portfolio_id, portfolio_payload)
    response = _client_for(service).get(f"/portfolio/{portfolio_id}")
    assert response.status_code == 200
    for panel in ("panel-report", "panel-market", "panel-trades"):
        assert f'id="{panel}"' in response.text
    assert 'id="portfolio-correlation"' in response.text


def test_analyze_rejects_a_single_code_before_touching_okx(tmp_path) -> None:
    response = _client(tmp_path).post("/api/portfolio/analyze", json={"codes": ["AAA"]})
    assert response.status_code == 400
    assert "at least 2" in response.text


# --------------------------------------------------------------------------- #
# Không tràn, và đúng form của trang
# --------------------------------------------------------------------------- #


def test_every_wide_block_carries_its_own_horizontal_scroller(
    portfolio_payload,
) -> None:
    """`.main` đặt `overflow-x:hidden`, nên tràn ngang bị CẮT chứ không cuộn.

    Một ma trận 8 bot mà không có scroller riêng thì mất hẳn các cột bên phải
    và người đọc không có cách nào biết là đang thiếu.
    """
    html = render_portfolio_section(portfolio_payload["portfolio"])
    assert html.count('class="data-table"') == html.count('class="table-scroll"')
    assert html.count('class="pf-matrix"') == html.count('class="pf-scroll"')
    # Con của grid phải có min-width:0, nếu không nội dung dài sẽ đẩy rộng ô
    # thay vì bị ràng buộc trong nó -- lỗi tràn kinh điển của flex/grid.
    assert "min-width:0" in html


def test_no_hard_coded_colour_survives_a_theme_switch(portfolio_payload) -> None:
    """Bảng màu mặc định của `report_page.py` là SÁNG, có biến thể tối.

    Một `#94a3b8` hay `rgba(255,255,255,...)` viết cứng sẽ đúng ở đúng một
    trong hai chế độ và không đọc được ở chế độ còn lại.
    """
    import re

    html = render_portfolio_section(portfolio_payload["portfolio"])
    literals = re.findall(
        r"(?:color|background)\s*:\s*(#[0-9a-fA-F]{3,6}|rgba\(255,\s*255,\s*255)", html
    )
    assert literals == []
    for token in ("var(--ink)", "var(--ink-2)", "var(--down)", "var(--panel-2)"):
        assert token in html


def test_a_pathological_bot_name_cannot_stretch_the_layout(
    portfolio_payload,
) -> None:
    """Nickname OKX là văn bản tự do: có thể rất dài và không có chỗ ngắt."""
    import re

    hostile = dict(portfolio_payload["portfolio"])
    hostile["members"] = [
        {**hostile["members"][0], "label": "A" * 300 + "<script>alert(1)</script>"}
    ]
    html = render_portfolio_section(hostile)
    visible = re.findall(r'<span class="pf-name"[^>]*>(.*?)</span>', html, re.S)
    assert visible, "the name should be rendered through the clipping helper"
    assert all(len(chunk) <= 80 for chunk in visible)
    # Tên đầy đủ vẫn còn, nhưng trong `title` -- nơi không ảnh hưởng layout.
    assert 'title="' in html
    assert "<script>" not in html


def test_the_widest_supported_portfolio_still_fits_the_contract(
    portfolio_payload,
) -> None:
    """8 thành viên là trần (`PORTFOLIO_MAX_CODES`); ma trận 8x8 vẫn phải nằm
    trong scroller và không sinh ô nào ngoài lưới."""
    import re

    base = portfolio_payload["portfolio"]
    labels = [f"Member {index}" for index in range(PORTFOLIO_MAX_CODES)]
    wide = dict(base)
    wide["correlation"] = {
        **base["correlation"],
        "labels": labels,
        "codes": [f"CODE{index}" for index in range(PORTFOLIO_MAX_CODES)],
        "pearson": [
            [1.0 if row == col else 0.3 for col in range(PORTFOLIO_MAX_CODES)]
            for row in range(PORTFOLIO_MAX_CODES)
        ],
        "pairs": [],
    }
    html = render_portfolio_section(wide)
    assert html.count('class="pf-scroll"') == html.count('class="pf-matrix"')
    body = html.split('<table class="pf-matrix"')[1]
    first_row = re.search(r"<tr><th class=\"pf-row-head\".*?</tr>", body, re.S)
    assert first_row is not None
    # 8 ô dữ liệu, không hơn không kém, cho mỗi hàng.
    assert first_row.group(0).count("<td") == PORTFOLIO_MAX_CODES
