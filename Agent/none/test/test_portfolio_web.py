"""Tầng web của báo cáo tổ hợp: một trang, cùng renderer, cùng 3 tab.

Điều được khoá ở đây không phải là "route trả 200". Là: trang tổ hợp đi qua
ĐÚNG `render_bot_report_html` mà trang một bot đi qua, nên nó không thể lệch
style; và không route nào ở đây được phép bịa ra một con số khi thiếu dữ liệu.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from Agent.backend.pipeline_portfolio import (
    PortfolioBotRequest,
    PortfolioSupervisionPipeline,
)
from Agent.backend.web.data import (
    InvalidCodeError,
    PORTFOLIO_MAX_CODES,
    _full_result,
    _portfolio_text_lines,
    validate_portfolio_codes,
)
from Agent.backend.web.portfolio_section import (
    inject_portfolio_section,
    render_portfolio_section,
)
from Agent.backend.web.report_page import render_bot_report_html
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
    # `analyze_portfolio` (data.py) always overwrites `text` this way before
    # a payload ever reaches a page -- built here too, so every test below
    # exercises the SAME shape a real report gets, not the pre-overwrite one.
    payload["text"] = _portfolio_text_lines(
        payload,
        outcome.portfolio,
        len(_MEMBERS),
        combined_action=outcome.combined.risk_assessment.recommended_action,
    )
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
    # Khối thêm vào mang biểu đồ CỦA RIÊNG NÓ (class `pf-svg`), và không được
    # làm mất hay đụng vào biểu đồ của trang gốc. Trước đây test này khoá
    # "tổng số SVG không đổi" -- đúng khi khối chỉ có bảng, nhưng nó khoá
    # nhầm thứ: điều cần giữ là biểu đồ GỐC còn nguyên, không phải là khối
    # này mãi mãi không được vẽ gì.
    own_charts = full.count('class="pf-svg"')
    assert own_charts >= 1 and 'class="pf-var"' in full  # VaR bars are HTML (formula stars)
    assert full.count("<svg") - own_charts == document.count("<svg")
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
    # Khoá Ý NGHĨA chứ không ghim nguyên văn: trang phải nói người đọc làm gì
    # tiếp, và nói rõ id sẽ quay lại y nguyên nếu chạy lại đúng tập mã.
    assert "Re-run" in response.text
    assert "member set" in response.text


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


# --------------------------------------------------------------------------- #
# Tái dùng: một bot đã đọc rồi thì không đọc lại
# --------------------------------------------------------------------------- #


class _CountingDiskSource:
    """Phục vụ bot theo uniqueCode từ fixture trên đĩa, và ĐẾM số lượt đọc.

    Cần đếm chứ không chỉ đo thời gian: "nhanh hơn" có thể do máy rảnh, còn
    "không gọi lần nào" thì không thể nhầm.
    """

    def __init__(self, codes) -> None:
        import json

        from Agent.backend.infra.config import config as _config

        root = Path(_config.DATA_DIR) / "trade"
        self._docs = {}
        for code in codes:
            folder = root / f"bot_{code}"
            self._docs[code] = (
                json.loads((folder / "overview.json").read_text(encoding="utf-8")),
                json.loads((folder / "trade_list.json").read_text(encoding="utf-8")),
            )
        self.overview_calls = 0
        self.ledger_calls = 0

    def get_overview(self, unique_code, bot_dir=None):
        self.overview_calls += 1
        return self._docs[unique_code][0]

    def get_ledger(self, unique_code, bot_dir=None):
        self.ledger_calls += 1
        return self._docs[unique_code][1]


_REUSE_CODES = ("35F888C7BB441B2B", "6F262ADB3B44266C")


def _reuse_service(tmp_path):
    from Agent.backend.infra.config import config as _config
    from Agent.backend.web.data import WebDataService

    source = _CountingDiskSource(_REUSE_CODES)
    service = WebDataService(
        data_dir=Path(_config.DATA_DIR),
        bot_source_factory=lambda client, bucket: source,
    )
    return service, source


def test_a_bot_already_analysed_alone_is_not_read_again_for_a_portfolio(
    tmp_path,
) -> None:
    """Đây là phần lớn thời gian của một lượt chạy tổ hợp (đo được: 76%)."""
    service, source = _reuse_service(tmp_path)
    for code in _REUSE_CODES:
        service.analyze(code)
    after_singles = source.overview_calls
    assert after_singles == 2

    payload = service.analyze_portfolio(list(_REUSE_CODES))
    assert payload["status"] == "FULL"
    # Không một lượt đọc nào nữa.
    assert source.overview_calls == after_singles
    assert payload["member_sources"] == {code: "reused" for code in _REUSE_CODES}


def test_a_bot_first_seen_in_a_portfolio_opens_free_on_its_own(tmp_path) -> None:
    """Chiều ngược lại của cùng một bộ nhớ đệm."""
    service, source = _reuse_service(tmp_path)
    service.analyze_portfolio(list(_REUSE_CODES))
    after_portfolio = source.overview_calls
    assert after_portfolio == 2

    single = service.analyze(_REUSE_CODES[0])
    assert single["status"] == "FULL"
    assert source.overview_calls == after_portfolio


def test_refresh_takes_the_long_road_past_every_cache(tmp_path) -> None:
    """`?refresh=1` tồn tại để đọc lại OKX. Một cache lặng lẽ chặn nó thì nút
    đó thành nút giả."""
    service, source = _reuse_service(tmp_path)
    service.analyze_portfolio(list(_REUSE_CODES))
    baseline = source.overview_calls

    forced = service.analyze_portfolio(list(_REUSE_CODES), force=True)
    assert forced["cached"] is False
    assert source.overview_calls == baseline + 2
    assert forced["member_sources"] == {code: "fetched" for code in _REUSE_CODES}


def test_a_replayed_payload_says_it_is_a_replay(tmp_path) -> None:
    """`member_sources` mô tả lượt chạy ĐÃ SINH RA payload, không phải lượt
    gọi này -- nên phải có cờ nói rõ đây là bản phát lại."""
    service, _ = _reuse_service(tmp_path)
    first = service.analyze_portfolio(list(_REUSE_CODES))
    second = service.analyze_portfolio(list(_REUSE_CODES))
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["portfolio_id"] == first["portfolio_id"]


def test_the_portfolio_payload_carries_the_same_report_fields(tmp_path) -> None:
    """Payload tổ hợp LÀ payload đơn lẻ; thiếu khoá nào thì mọi consumer phải
    viết một nhánh đặc biệt."""
    from Agent.backend.web.data import build_portfolio_report_url

    service, _ = _reuse_service(tmp_path)
    single = service.analyze(_REUSE_CODES[0])
    multi = service.analyze_portfolio(list(_REUSE_CODES))

    for field in ("status", "code", "name", "verdict", "risk", "quality",
                  "confidence", "evidence", "report_markdown"):
        assert field in multi, field
        assert field in single, field
    assert len(multi["report_markdown"]) > 0
    # Link phải trỏ tới trang tổ hợp: `/bot/<id>` sẽ tra id như một uniqueCode,
    # trượt, rồi đi hỏi OKX về một bot không tồn tại.
    if "report_url" in multi:
        assert multi["report_url"] == build_portfolio_report_url(
            multi["portfolio_id"]
        )
        assert "/portfolio/" in multi["report_url"]


# --------------------------------------------------------------------------- #
# Bền vững và không xung đột
# --------------------------------------------------------------------------- #


def test_the_page_outlives_this_process_memory(tmp_path) -> None:
    """`report_url` chỉ đáng phát ra nếu trang còn sống sau TTL / restart.

    Trước khi có bước lưu xuống đĩa, `/portfolio/<id>` chỉ phục vụ được lượt
    chạy còn nằm trong bộ nhớ tiến trình -- nghĩa là cái link trong payload
    sẽ 404 sau 10 phút, sau một lần restart, hoặc đơn giản khi rơi vào
    worker khác. Phát ra một URL phần lớn thời gian chết còn tệ hơn không
    phát ra gì.
    """
    from Agent.backend.web.data import portfolio_document_path

    service, _ = _reuse_service(tmp_path)
    service.data_dir = tmp_path  # đừng ghi vào dataset thật
    payload = service.analyze_portfolio(list(_REUSE_CODES))
    portfolio_id = payload["portfolio_id"]

    assert portfolio_document_path(tmp_path, portfolio_id).exists()

    # Quên sạch bộ nhớ, như một tiến trình vừa khởi động lại.
    service._portfolio_by_id = _TTLCache_for(service)
    restored = service.portfolio_report(portfolio_id)
    assert restored is not None
    assert restored["portfolio_id"] == portfolio_id
    assert restored["risk"] == payload["risk"]
    assert restored["portfolio"]["verdict"] == payload["portfolio"]["verdict"]


def _TTLCache_for(service):
    from Agent.backend.web.data import _TTLCache

    return _TTLCache(600.0)


def test_an_unknown_id_is_still_a_404_not_a_fresh_run(tmp_path) -> None:
    """Đọc từ đĩa không được biến thành 'phân tích lại khi trượt'."""
    service, source = _reuse_service(tmp_path)
    service.data_dir = tmp_path
    before = source.overview_calls
    assert service.portfolio_report("PORT_FFFFFFFFFFFF") is None
    assert source.overview_calls == before


def test_a_hostile_portfolio_id_cannot_escape_its_directory(tmp_path) -> None:
    from Agent.backend.web.data import portfolio_document_path

    path = portfolio_document_path(tmp_path, "../../../etc/passwd")
    assert tmp_path in path.parents
    assert ".." not in path.parts


def test_two_callers_asking_at_once_run_the_analysis_once(tmp_path) -> None:
    """Một lượt tổ hợp là N lần đọc sổ lệnh OKX. Hai request trùng nhau chạy
    song song là trả giá hai lần cho đúng một câu trả lời."""
    import threading

    service, source = _reuse_service(tmp_path)
    service.data_dir = tmp_path
    results = []
    barrier = threading.Barrier(2)

    def _call() -> None:
        barrier.wait()
        results.append(service.analyze_portfolio(list(_REUSE_CODES)))

    threads = [threading.Thread(target=_call) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=300)

    assert len(results) == 2
    # Đúng một lượt đọc cho mỗi thành viên, không phải hai.
    assert source.overview_calls == 2
    assert results[0]["portfolio_id"] == results[1]["portfolio_id"]
    # Người thứ hai thấy bản phát lại, và payload nói rõ điều đó.
    assert sorted(item["cached"] for item in results) == [False, True]


def test_the_whole_round_trip_works_over_http(tmp_path) -> None:
    """POST phân tích -> lấy id -> GET trang, qua đúng các route thật.

    Mọi test trên đây gọi thẳng tầng dữ liệu hoặc dựng HTML từ payload có
    sẵn. Đây là đường một người dùng thật đi, và nó là đường duy nhất đồng
    thời chạm cả validate đầu vào, khoá chống chạy trùng, lưu xuống đĩa,
    renderer dùng chung và khối correlation chèn thêm.
    """
    service, source = _reuse_service(tmp_path)
    service.data_dir = tmp_path
    client = _client_for(service)

    posted = client.post(
        "/api/portfolio/analyze", json={"codes": list(_REUSE_CODES)}
    )
    assert posted.status_code == 200
    body = posted.json()
    assert body["status"] == "FULL"
    assert body["cached"] is False
    portfolio_id = body["portfolio_id"]
    assert portfolio_id.startswith("PORT_")
    assert body["report_markdown"]
    assert body["portfolio"]["correlation"]["is_valid"] is True

    page = client.get(f"/portfolio/{portfolio_id}")
    assert page.status_code == 200
    for panel in ("panel-report", "panel-market", "panel-trades"):
        assert f'id="{panel}"' in page.text
    assert 'id="portfolio-correlation"' in page.text

    # Lần POST thứ hai không được đọc lại sổ lệnh của ai.
    before = source.overview_calls
    again = client.post(
        "/api/portfolio/analyze", json={"codes": list(reversed(_REUSE_CODES))}
    )
    assert again.status_code == 200
    assert again.json()["cached"] is True
    assert again.json()["portfolio_id"] == portfolio_id
    assert source.overview_calls == before

    # Và danh sách lịch sử thấy lượt chạy này.
    listed = client.get("/api/portfolios").json()
    assert any(row["portfolio_id"] == portfolio_id for row in listed["portfolios"])


# --------------------------------------------------------------------------- #
# Hợp đồng trường giữa API và giao diện
# --------------------------------------------------------------------------- #


def test_the_admin_table_reads_no_field_the_api_does_not_send(tmp_path) -> None:
    """Mọi `run.<field>` trong bảng Admin phải có thật trong hàng API trả về.

    Đây là lỗi đã xảy ra thật, không phải giả định: bảng được viết theo một
    bộ dữ liệu mẫu cũ và đọc `portfolio_risk_score` / `joint_max_drawdown` /
    `members`, ba trường mà API không hề trả. Hậu quả không phải một lỗi ném
    ra — mà là những ô lặng lẽ trống, trông y như "chưa đo được".

    Đọc thẳng file JSX thay vì kiểm bằng mắt, vì một trường bị đổi tên ở một
    bên sẽ không bao giờ tự báo cho bên kia.
    """
    import re

    from Agent.backend.infra.config import config as _config

    admin = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "pages"
        / "AdminHome.jsx"
    )
    if not admin.exists():  # pragma: no cover - chỉ khi cây nguồn bị cắt
        pytest.skip("frontend source is not present in this checkout")
    source = admin.read_text(encoding="utf-8")
    # Bỏ phần chú thích: một trường được NHẮC TỚI trong lời giải thích vì sao
    # nó bị loại bỏ thì không phải là một trường đang được đọc.
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    source = re.sub(r"^\s*//.*$", "", source, flags=re.M)
    read_fields = set(re.findall(r"\brun\.([a-z_0-9]+)", source))
    assert read_fields, "không tìm thấy trường nào -- biểu thức đã lỗi thời"

    service, _ = _reuse_service(tmp_path)
    service.data_dir = tmp_path
    service.analyze_portfolio(list(_REUSE_CODES))
    rows = service.list_portfolio_runs()
    assert rows, "phải có ít nhất một hàng để đối chiếu"

    missing = sorted(field for field in read_fields if field not in rows[0])
    assert not missing, (
        "bảng Admin đọc những trường API không gửi: "
        + ", ".join(missing)
        + " -- thêm chúng vào list_portfolio_runs hoặc sửa bảng"
    )


def test_a_listed_run_can_always_be_opened_or_says_it_cannot(tmp_path) -> None:
    """Cờ `report_available` phải khớp thực tế, không được đoán.

    Nó tồn tại để giao diện không mời người đọc bấm vào một trang 404 -- nên
    một cờ sai còn tệ hơn không có cờ.
    """
    service, _ = _reuse_service(tmp_path)
    service.data_dir = tmp_path
    payload = service.analyze_portfolio(list(_REUSE_CODES))
    client = _client_for(service)

    for row in service.list_portfolio_runs():
        page = client.get(f"/portfolio/{row['portfolio_id']}")
        expected = 200 if row["report_available"] else 404
        assert page.status_code == expected, row["portfolio_id"]
    assert any(
        row["portfolio_id"] == payload["portfolio_id"] and row["report_available"]
        for row in service.list_portfolio_runs()
    )


def test_short_labels_shorten_real_okx_nicknames_not_only_spaced_ones() -> None:
    """Tên mẫu trong mockup có dấu cách ("Aquila Grid" -> "Aquila"); tên OKX
    thật thì không. Quy tắc cũ chỉ tách theo khoảng trắng, nên ma trận thật
    hiện "Elegant-Layer…", "E9BB0FE3B8797…" -- lệch hẳn thiết kế (2026-09-24)."""
    from Agent.backend.web.portfolio_section import _short_labels

    assert _short_labels(
        [
            "Elegant-Layer-Violet",
            "Alvin_Cryptodancers",
            "E9BB0FE3B8797B72",
            "828556126433358780",
            "Delta Mean Rev",
        ]
    ) == {
        "Elegant-Layer-Violet": "Elegant",
        "Alvin_Cryptodancers": "Alvin",
        "E9BB0FE3B8797B72": "E9BB0F",
        "828556126433358780": "828556",
        "Delta Mean Rev": "Delta",
    }


def test_short_labels_fall_back_to_the_full_name_when_first_words_collide() -> None:
    from Agent.backend.web.portfolio_section import _short_labels

    assert _short_labels(["Crypto-Zeus", "Crypto-King"]) == {
        "Crypto-Zeus": "Crypto-Zeus",
        "Crypto-King": "Crypto-King",
    }


def test_short_labels_keep_a_one_or_two_letter_first_word_whole() -> None:
    from Agent.backend.web.portfolio_section import _short_labels

    short = _short_labels(["IS.K", "Trader KS"])
    assert short["IS.K"] == "IS.K"
    assert short["Trader KS"] == "Trader"


def test_the_matrix_table_is_not_capped_by_an_inline_pixel_width(portfolio_payload) -> None:
    """Bảng từng bị giới hạn `max-width:(n+1)*130px` nằm trong một thẻ rộng
    hơn -- khoảng trống chết bên cạnh, ký hiệu r/d bị đẩy ra mép. Giờ bảng
    lấp đầy thẻ, và hai thẻ (matrix / statistics) cân nhau theo đúng tỉ lệ
    mockup `1fr : 1.08fr` -- yêu cầu của chủ dự án (2026-09-24)."""
    html = render_portfolio_section(portfolio_payload["portfolio"])
    tag = html.split('<table class="pf-matrix"')[1].split(">", 1)[0]
    assert "max-width" not in tag
    assert (
        ".pf-pane-corr .pf-cols{grid-template-columns:minmax(0,1fr) minmax(0,1.08fr)}"
        in html
    )


def test_the_portfolio_title_counts_the_bots_that_were_booked(tmp_path, monkeypatch) -> None:
    """Phát hiện thật (2026-09-24): book 4 mã, 1 mã giấu sổ -- report hiện
    "Portfolio of 3 bots", và câu hỏi đầu tiên của người đọc là bot thứ tư
    đâu. Tiêu đề phải là số bot đã BOOK; bao nhiêu được đo nằm ở từng mục.

    `fetch_members`/`assemble` được thay bằng bản ghi lại tham số, nên test
    không đụng OKX, không đụng đĩa -- chỉ kiểm đúng nhãn được truyền đi.
    """
    from Agent.backend.pipeline_portfolio import (
        PortfolioMemberFailure,
        PortfolioSupervisionResult,
    )
    from Agent.none.test.portfolio_factory import make_bot, make_trades

    series = [1.0, -2.0, 3.0, -1.0, 0.5, -0.5, 2.0, -3.0, 1.5, -1.5] * 6
    measured = [
        make_bot("AAAA1111", make_trades(series)),
        make_bot("BBBB2222", make_trades([-v for v in series])),
        make_bot("CCCC3333", make_trades(series)),
    ]
    concealed = PortfolioMemberFailure(
        asset="BTC", bot_folder_name="bot_DDDD4444", error="60004", kind="concealed"
    )
    captured = {}

    def fake_fetch(self, requests, **kwargs):
        return list(measured), [concealed]

    def fake_assemble(self, members, **kwargs):
        captured.update(kwargs)
        return PortfolioSupervisionResult(
            failures=list(kwargs.get("failures") or []),
            unavailable_reason="captured for the test",
        )

    monkeypatch.setattr(PortfolioSupervisionPipeline, "fetch_members", fake_fetch)
    monkeypatch.setattr(PortfolioSupervisionPipeline, "assemble", fake_assemble)

    service = _service_with(_StubBotSource(), data_dir=tmp_path)
    service.analyze_portfolio(["AAAA1111", "BBBB2222", "CCCC3333", "DDDD4444"])

    assert captured.get("nick_name") == "Portfolio of 4 bots"


def test_a_concealed_member_is_still_counted_in_the_history_listing(tmp_path) -> None:
    """Phát hiện thật, trực tiếp trên container đang chạy (2026-09-24): gửi
    4 mã, một mã giấu sổ lệnh -- `/api/portfolios` lưu lại thành "3 bot",
    không còn dấu vết nào là mã thứ tư từng được gửi lên.

    Đi thẳng qua lớp `list_portfolio_runs` đọc -- lớp máy quét đúng chỗ hổng
    (nó chỉ có `PortfolioRiskAssessment` đã lưu, không có `failures` gốc),
    thay vì kéo theo toàn bộ đường live-lookup/scratch-dir của
    `analyze_portfolio`, vốn đã có test riêng ở nơi khác.

    CỐ Ý dùng `_service_with` (buộc `data_dir=tmp_path` NGAY LÚC khởi tạo),
    không phải `_reuse_service` (khoá cứng `Agent/data` thật rồi đổi
    `.data_dir` SAU) -- `WebDataService.portfolio_history` được gắn vào
    thư mục thật ngay trong `__init__`, nên đổi `.data_dir` sau đó không dời
    nó đi đâu cả. Bài học từ chính lần chạy đầu của test này (2026-09-24):
    nó đã ghi thật một `PORT_…json` với hai bot "AAA"/"BBB" giả vào đúng
    `Agent/data/report/multi/state/portfolios/` -- thư mục container thật
    (`norabt-agent-web`) đang đọc -- và phải dọn tay.
    """
    from Agent.backend.report.qc.portfolio.service import (
        PortfolioCandidate,
        PortfolioQCService,
    )
    from Agent.none.test.portfolio_factory import make_bot, make_trades

    service = _service_with(_StubBotSource(), data_dir=tmp_path)

    series = [1.0, -2.0, 3.0, -1.0, 0.5, -0.5, 2.0, -3.0, 1.5, -1.5] * 6
    assessment = PortfolioQCService.assess_portfolio(
        [
            PortfolioCandidate(bot=make_bot("AAA", make_trades(series))),
            PortfolioCandidate(bot=make_bot("BBB", make_trades([-v for v in series]))),
        ],
        iterations=500,
        concealed_members=["ZZZ"],
        error_members=["YYY"],
    )
    service.portfolio_history.append(assessment)

    row = next(
        r for r in service.list_portfolio_runs()
        if r["portfolio_id"] == assessment.portfolio_id
    )
    # Do duoc chi 2 -- nhung phai con nguyen dau vet la 4 ma da gui len
    # (2 do duoc + 1 giau so + 1 loi doc).
    assert row["member_count"] == 2
    assert row["submitted_member_count"] == 4
    assert row["concealed_member_codes"] == ["ZZZ"]
    assert row["measurement_coverage_pct"] == assessment.measurement_coverage_pct


def test_each_member_links_to_its_own_bot_report(portfolio_payload) -> None:
    """Thấy bot nào kéo danh mục xuống mà không mở được nó thì vô dụng.

    Link mang href thật (`/bot/<code>`) nên vẫn đi được khi trang được mở
    trực tiếp, và mang `class`/`data-code` để SPA chặn lại, ở trong router
    của chính nó thay vì điều hướng cả trang.
    """
    import re

    html = render_portfolio_section(portfolio_payload["portfolio"])
    links = re.findall(
        r'<a class="pf-member-link" data-code="([^"]+)" href="/bot/([^"]+)"', html
    )
    assert links, "bảng thành viên phải có link sang từng bot"
    codes = {member["unique_code"] for member in portfolio_payload["portfolio"]["members"]}
    assert {code for code, _ in links} == codes
    # data-code và href phải nói cùng một bot; lệch nhau là gửi người đọc đi
    # xem một bot khác với bot họ vừa bấm.
    assert all(code == href for code, href in links)


def test_the_section_is_parameters_and_charts_not_prose(portfolio_payload) -> None:
    """Khối này phải đọc như một bảng điều khiển, không như một tài liệu.

    Bản đầu đổ nguyên `evidence`, `warnings`, `limitations` và
    `recommended_action` ra thành các danh sách câu đầy đủ, cộng một câu
    verdict dài trên mỗi badge và một câu ghi chú cho mỗi cặp bot. Trên tám
    bot đó là hơn hai mươi dòng văn xuôi nằm phía trên con số đầu tiên.
    Không có thông tin nào bị vứt đi: các cảnh báo trở thành chip mang đủ
    nội dung trong `title`, còn mọi câu ghi chú vốn chỉ diễn đạt lại đúng r,
    p và khoảng cách phong cách -- đều đang hiển thị dưới dạng số.
    """
    import re

    portfolio = portfolio_payload["portfolio"]
    html = render_portfolio_section(portfolio)
    body = html.split("</style>", 1)[1]

    # Không đổ nguyên văn các trường văn xuôi ra thân trang.
    for sentence in (portfolio.get("evidence") or [])[:5]:
        assert sentence not in body
    action = portfolio.get("recommended_action") or ""
    if action:
        assert action not in body
    reason = portfolio.get("verdict_reason") or ""
    if reason:
        assert reason not in body

    # Cảnh báo vẫn còn NGUYÊN NỘI DUNG, chỉ là trong `title` của chip.
    warnings = portfolio.get("warnings") or []
    if warnings:
        assert 'class="pf-chip' in body
        assert _esc_for_test(warnings[0]) in body

    # Và những thứ PHẢI có: biểu đồ, ô số liệu, hàng dữ liệu, ma trận.
    assert body.count('class="pf-svg"') >= 1 and 'class="pf-var"' in body
    assert body.count('class="pf-kpi"') >= 6
    assert body.count('class="pf-row"') >= 3
    assert body.count('<table class="pf-matrix"') == 1

    # Câu "khối này trả lời câu hỏi gì" giờ nằm trong `title` của tiêu đề --
    # một chỗ hover, không phải một dòng văn xuôi trên trang -- và vẫn phải
    # ngắn.
    hint = re.search(r'<h3 class="pf-title" title="([^"]*)"', body)
    assert hint is not None
    assert len(hint.group(1)) < 160, f"dòng dẫn nhập dài {len(hint.group(1))}"

    # Và phần đầu không được chứa một thẻ đoạn văn nào -- `<p>` ở đây nghĩa
    # là ai đó vừa thêm lại một khối văn xuôi.
    header = body[: body.index('class="pf-kpis"')]
    # Ranh giới thẻ, không phải tiền tố: `<li` khớp cả `<line>` trong SVG.
    assert not re.search(r"<p[ >]", header)
    assert not re.search(r"<li[ >]", body), "gạch đầu dòng là hình dạng tài liệu"


def _esc_for_test(value: str) -> str:
    import html as _html

    return _html.escape(value, quote=True)


# --------------------------------------------------------------------------- #
# Market và position trên cùng một hàng
# --------------------------------------------------------------------------- #


def test_exposure_and_notional_do_not_contradict_each_other(
    portfolio_payload,
) -> None:
    """Hai cột nói về cùng một sự thật thì phải nói giống nhau.

    Bản đầu lấy `open_notional` từ `exposure_by_symbol` còn `exposure_share`
    từ `concentration`, mà `concentration` có bước dự phòng khi bot không
    tách notional theo mã. Kết quả: cột này đọc 55% trong khi cột ngay cạnh
    đọc 0 -- không phải thiếu dữ liệu, mà là hai cột mâu thuẫn về một con số.
    """
    breakdown = portfolio_payload["portfolio"].get("symbol_breakdown") or []
    assert breakdown, "phải có ít nhất một mã"
    for row in breakdown:
        share = row.get("exposure_share")
        notional = row.get("open_notional")
        if share:
            assert notional, f"{row['symbol']}: exp {share} nhưng notional {notional}"


def test_the_joint_table_shows_book_and_market_on_one_row(
    portfolio_payload,
) -> None:
    """Đây là thứ hai tab tách rời không nói được."""
    portfolio = portfolio_payload["portfolio"]
    markets = [
        {
            "symbol": (portfolio["symbol_breakdown"][0]["symbol"]),
            "share_pct": 50.0,
            "venue_type": "CEX",
            "trend": "BULLISH",
            "volatility": "NORMAL",
            "liquidity_tier": "ADEQUATE",
            "flow_bias": "NEUTRAL",
            "last_price": 1234.5,
        }
    ]
    html = render_portfolio_section(portfolio, markets, [])
    assert "Book and market, per instrument" in html
    assert ">BOOK<" in html and ">MARKET<" in html
    assert "BULLISH" in html
    assert "1234.50" in html


def test_a_symbol_without_market_data_keeps_its_row_and_says_why(
    portfolio_payload,
) -> None:
    """Bỏ hàng đó đi là âm thầm thu nhỏ cuốn sổ mà người đọc tưởng mình đang xem."""
    portfolio = portfolio_payload["portfolio"]
    symbol = portfolio["symbol_breakdown"][0]["symbol"]
    html = render_portfolio_section(
        portfolio,
        [],
        [{"symbol": symbol, "share_pct": 50.0, "reason": "NO_MARKET_DATA"}],
    )
    assert f"<b>{symbol}</b>" in html
    assert "no market data" in html


def test_a_long_tail_of_instruments_is_rolled_up_not_dropped(
    portfolio_payload,
) -> None:
    """Một danh mục thật chạm 71 mã. 71 hàng là bãi dữ liệu, không phải phân
    tích -- nhưng phần đuôi vẫn phải được cộng vào đâu đó."""
    from Agent.backend.web.portfolio_section import _MAX_SYMBOL_ROWS

    base = portfolio_payload["portfolio"]["symbol_breakdown"][0]
    many = [
        {**base, "symbol": f"SYM{index}", "realized_pnl": 100.0,
         "closed_trades": 3, "exposure_share": None, "open_notional": None}
        for index in range(_MAX_SYMBOL_ROWS + 9)
    ]
    portfolio = {**portfolio_payload["portfolio"], "symbol_breakdown": many}
    html = render_portfolio_section(portfolio, [], [])
    assert "9 more" in html
    # Tổng của phần đuôi phải có mặt, không bị vứt.
    assert "900" in html
    assert "rolled up" in html


def test_no_html_entity_is_escaped_twice(portfolio_payload) -> None:
    """`&le;` viết trong một nhãn rồi đi qua `_esc()` sẽ ra `&amp;le;`.

    Trên màn hình nó hiện nguyên chuỗi `&le;` chứ không thành ký tự. Lỗi này
    đã xảy ra hai lần trong khối này -- một lần với dấu gạch ngang trên `r`,
    một lần với dấu nhỏ-hơn-hoặc-bằng trong chú giải -- vì các hàm dựng nhãn
    escape đầu vào của chúng, đúng như chúng phải làm. Cách sửa là dùng ký
    tự Unicode thật, không phải entity; test này bắt lần thứ ba.
    """
    import re

    html_out = render_portfolio_section(portfolio_payload["portfolio"], [], [])
    doubled = set(re.findall(r"&amp;[a-zA-Z]{2,8};", html_out))
    assert not doubled, f"entity bị escape hai lần: {sorted(doubled)}"
    assert not re.findall(r"&amp;#\d+;", html_out)


def test_results_and_behaviour_share_one_matrix(portfolio_payload) -> None:
    """Kết quả (r) và hành vi (khoảng cách thoát lệnh d) phải đọc được như
    MỘT hình: cùng một cặp, cùng một toạ độ.

    Hai ma trận đặt cạnh nhau bắt người đọc tự dò hai ô cùng toạ độ bằng
    mắt. Giờ là một ma trận: nửa trên là r, nửa dưới là d, và cặp "bẫy"
    (r thấp nhưng cùng cách chơi) được khoanh ở CẢ hai nửa.
    """
    import re

    portfolio = portfolio_payload["portfolio"]
    html_out = render_portfolio_section(portfolio, [], [])
    labels = portfolio["correlation"]["labels"]
    body = html_out.split('<table class="pf-matrix"')[1].split("</table>")[0]
    rows = re.findall(r'<tr><th class="pf-row-head".*?</tr>', body, re.S)
    assert len(rows) == len(labels)
    upper = body.count('class="pf-up')
    lower = body.count('class="pf-lo')
    pair_count = len(labels) * (len(labels) - 1) // 2
    assert upper == pair_count and lower == pair_count
    traps = sum(
        1 for p in portfolio["correlation"].get("pairs") or []
        if (p.get("style") or {}).get("style_vs_pnl_conflict")
    )
    assert body.count("pf-trapcell") == 2 * traps
    # Chú giải dính đáy khung để hai khung cạnh nhau kết thúc cùng một đường.
    assert ".pf-legend{margin-top:auto" in html_out
    # Thống kê cặp KHÔNG in lại r và d -- chúng đã ở trong ma trận.
    stats = html_out.split('class="pf-box pf-pairs"')[1]
    header = re.search(r'<div class="pf-row pf-row-h">(.*?)</div>', stats, re.S).group(1)
    assert ">r<" not in header and ">d<" not in header


def test_the_conclusion_is_one_fact_per_line_not_a_paragraph(tmp_path) -> None:
    """`report_page.py` gộp mọi dòng KHÔNG có bullet thành một đoạn duy nhất.

    Bản giải thích mặc định phát ra bốn dòng dài không bullet, nên phần kết
    luận của một danh mục hiện ra như một khối văn xuôi liền mạch với cả
    danh sách ghi chú dữ liệu nhét vào giữa. Mỗi phép đo phải là một dòng
    riêng, đủ ngắn để đọc lướt.
    """
    service, _ = _reuse_service(tmp_path)
    service.data_dir = tmp_path
    payload = service.analyze_portfolio(list(_REUSE_CODES))
    lines = payload.get("text") or []
    assert lines, "phải có dòng kết luận"

    bulleted = [line for line in lines if line.startswith("• ")]
    assert len(bulleted) >= 4, f"chỉ có {len(bulleted)} dòng thành hàng riêng"
    # Mỗi dòng là MỘT phép đo, không phải một đoạn.
    for line in bulleted:
        assert len(line) < 140, f"dòng dài {len(line)}: {line}"
    # Phần không bullet -- thứ sẽ bị gộp thành đoạn -- phải ngắn.
    plain = " ".join(line for line in lines if not line.startswith("• "))
    assert len(plain) < 160, f"đoạn văn còn lại dài {len(plain)}: {plain}"

    # Và ghi chú của từng thành viên chỉ còn là số đếm ở đây.
    joined = " ".join(lines)
    assert "Data notes per member" in joined
    for limitation in (payload["portfolio"].get("limitations") or [])[:3]:
        assert limitation not in joined


# --------------------------------------------------------------------------- #
# Thành viên KHÔNG nạp được phải hiện trên trang.
#
# `_member_table` chỉ liệt kê bot đã đọc xong. Bot hỏng ngay từ khâu nạp không
# bao giờ tới được danh sách đó, nên trước đây nó không để lại dấu vết nào: tổ
# hợp 6 bot mà bot thứ sáu giấu sổ lệnh sẽ hiện ra như một báo cáo 5 bot gọn
# gàng, và mọi con số trong đó mô tả một rổ khác với rổ người đọc hỏi.
#
# Hướng sai lệch mới là điều phải nói rõ: các bot còn lại đều là bot CÔNG KHAI
# sổ lệnh, nên tương quan đo được thấp hơn và mức phân tán tốt hơn rổ thật.
# --------------------------------------------------------------------------- #


def _failure(kind: str, code: str = "ZZZ") -> dict:
    return {
        "asset": "BTC",
        "bot_folder_name": f"bot_{code}",
        "error": "boom",
        "kind": kind,
    }


def test_a_member_that_never_loaded_is_still_on_the_page(portfolio_payload) -> None:
    html = render_portfolio_section(
        portfolio_payload["portfolio"], [], [], [_failure("concealed")]
    )
    assert "Submitted but not measured" in html
    assert "ZZZ" in html
    assert "CONCEALED" in html


def test_a_concealed_member_says_the_numbers_are_optimistic(
    portfolio_payload,
) -> None:
    """"Thiếu một thành viên" và "số bạn đang đọc là lạc quan" là hai cảnh báo
    khác nhau; cái thứ hai mới là cái người đọc cần."""
    html = render_portfolio_section(
        portfolio_payload["portfolio"], [], [], [_failure("concealed")]
    )
    assert "RISK UNDERSTATED" in html


def test_a_failed_read_is_not_reported_as_concealment(portfolio_payload) -> None:
    """Đọc hỏng là lỗi của LƯỢT CHẠY, không phải phát hiện về bot.

    Gộp hai thứ này sẽ ghi một mạng chập vào hồ sơ rủi ro của bot, nên
    `kind="error"` không được kéo theo cảnh báo của `kind="concealed"`.
    """
    html = render_portfolio_section(
        portfolio_payload["portfolio"], [], [], [_failure("error")]
    )
    assert "UNREADABLE" in html
    assert "RISK UNDERSTATED" not in html
    assert "CONCEALED" not in html


def test_no_absent_block_when_every_member_loaded(portfolio_payload) -> None:
    html = render_portfolio_section(portfolio_payload["portfolio"], [], [], [])
    assert "Submitted but not measured" not in html


def test_absent_member_codes_from_okx_are_escaped(portfolio_payload) -> None:
    html = render_portfolio_section(
        portfolio_payload["portfolio"],
        [],
        [],
        [_failure("concealed", '<img src=x onerror="alert(1)">')],
    )
    assert "<img src=x" not in html
    assert "&lt;img" in html


# --------------------------------------------------------------------------- #
# Banner EMERGENCY/CAUTION/STANDARD phải xuất hiện cho báo cáo tổ hợp, y hệt
# báo cáo đơn -- `_render_conclusion` (report_page.py) chỉ dựng banner này
# nếu tìm được một dòng bắt đầu "CONCLUSION:" trong `result["text"]"`. Trước
# fix, generator của tổ hợp không bao giờ phát ra dòng đó, nên trang tổ hợp
# luôn thiếu hẳn khối này dù scorecard vẫn hiện số trần trụi.
# --------------------------------------------------------------------------- #


def test_the_conclusion_line_is_present_for_a_portfolio(portfolio_payload) -> None:
    assert any(line.startswith("CONCLUSION:") for line in portfolio_payload["text"])


def test_the_risk_banner_renders_for_a_portfolio_report(portfolio_payload) -> None:
    """Đúng bằng chứng người dùng đã thấy thiếu: 'chỉ thấy con số trần trụi,
    không có banner nào'. Sau fix, trang tổ hợp phải có class callout đó."""
    html = render_bot_report_html(portfolio_payload)
    # 2026-09-24 redesign: the EMERGENCY/CAUTION/STANDARD callout box was
    # removed at the project owner's request; the same zone now drives the
    # verdict chip in the header and the "Action: ..." pill on the WHY row.
    assert "report-verdict-chip tone-" in html
    assert any(
        f'class="action-pill tone-{zone}"' in html
        for zone in ("danger", "warning", "success")
    )


def test_the_conclusion_line_carries_the_combined_books_own_verdict(
    portfolio_payload,
) -> None:
    """Không phải verdict bịa riêng cho tổ hợp -- đúng verdict của MỘT
    BotRiskAssessment gộp mà toàn bộ report còn lại (kể cả scorecard) đọc."""
    conclusion = next(
        line for line in portfolio_payload["text"] if line.startswith("CONCLUSION:")
    )
    assert portfolio_payload["verdict"] in conclusion


def test_the_conclusion_line_also_carries_the_portfolio_verdict(
    portfolio_payload,
) -> None:
    """Sếp (2026-09-23, M3): '<verdict DRAWDOWN/QUALITY của bot gộp> —
    <PortfolioVerdict>' -- hai trục, một dòng."""
    conclusion = next(
        line for line in portfolio_payload["text"] if line.startswith("CONCLUSION:")
    )
    assert portfolio_payload["portfolio"]["verdict"] in conclusion
    # Đúng thứ tự: verdict sổ gộp trước, PortfolioVerdict sau dấu " — ".
    combined_idx = conclusion.index(portfolio_payload["verdict"])
    portfolio_idx = conclusion.index(portfolio_payload["portfolio"]["verdict"])
    assert combined_idx < portfolio_idx


def test_high_correlation_cluster_escalates_the_banner_to_at_least_warning() -> None:
    """Sếp (2026-09-23, M3): PortfolioVerdict = HIGH_CORRELATION_CLUSTER phải
    ép banner tối thiểu ở mức cảnh báo, kể cả khi sổ gộp tự nó đọc DRAWDOWN
    thấp -- dựng payload tổng hợp trực tiếp, không phụ thuộc việc fixture
    thật có ra đúng HIGH_CORRELATION_CLUSTER hay không."""
    payload = {
        "status": "FULL",
        "code": "PORT_TEST",
        "name": "Test Portfolio",
        "verdict": "DRAWDOWN: LOW · QUALITY: GOOD",
        "risk": 20.0,
        "quality": 90.0,
        "portfolio": {"verdict": "HIGH_CORRELATION_CLUSTER"},
        "text": [
            "CONCLUSION: DRAWDOWN: LOW · QUALITY: GOOD — HIGH_CORRELATION_CLUSTER. "
            "quality 90/100, risk 20/100."
        ],
        "evidence": {},
        "unavailable": [],
    }
    html = render_bot_report_html(payload)
    # Zone now shown by the header chip + action pill (see the test above).
    assert 'class="action-pill tone-warning"' in html
    assert "report-verdict-chip tone-warning" in html
    assert "report-verdict-chip tone-success" not in html


def test_diversified_portfolio_does_not_escalate_the_banner() -> None:
    """Đối chứng: PortfolioVerdict tốt (DIVERSIFIED) không được tự ý nâng
    banner lên -- sàn chỉ áp cho đúng HIGH_CORRELATION_CLUSTER."""
    payload = {
        "status": "FULL",
        "code": "PORT_TEST2",
        "name": "Test Portfolio 2",
        "verdict": "DRAWDOWN: LOW · QUALITY: GOOD",
        "risk": 20.0,
        "quality": 90.0,
        "portfolio": {"verdict": "DIVERSIFIED"},
        "text": [
            "CONCLUSION: DRAWDOWN: LOW · QUALITY: GOOD — DIVERSIFIED. "
            "quality 90/100, risk 20/100."
        ],
        "evidence": {},
        "unavailable": [],
    }
    html = render_bot_report_html(payload)
    assert 'class="action-pill tone-success"' in html
    assert "report-verdict-chip tone-success" in html
    assert 'class="action-pill tone-warning"' not in html


# --------------------------------------------------------------------------- #
# /api/analyze with several codes -- the OnchainOS entry point (SID 40700)
# --------------------------------------------------------------------------- #
#
# The Marketplace service has ONE parameter, `code`. "A,B" used to be a 400
# (run-nora.sh then crashed on a missing confirmationId) and "A B" through
# the script scored only A (2026-09-25).


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AAA,BBB", ["AAA", "BBB"]),
        ("AAA BBB", ["AAA", "BBB"]),
        (" AAA ; BBB\nCCC ", ["AAA", "BBB", "CCC"]),
        (["AAA", "BBB"], ["AAA", "BBB"]),
        ("AAA,", ["AAA"]),
        ("AAA AAA", ["AAA"]),
        (["AAA"], ["AAA"]),
        ("   ", []),
        (7, None),
    ],
)
def test_code_lists_split_the_way_people_type_them(raw, expected) -> None:
    from Agent.backend.web.app import _split_code_list

    assert _split_code_list(raw) == expected


def test_several_codes_in_code_run_one_portfolio(tmp_path, portfolio_payload) -> None:
    service = _service_with(_StubBotSource(), data_dir=tmp_path)
    calls = []

    def fake(codes, *, force=False, progress=None):
        calls.append(list(codes))
        return portfolio_payload

    service.analyze_portfolio = fake
    response = _client_for(service).post("/api/analyze", json={"code": "AAA, BBB CCC"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert calls == [["AAA", "BBB", "CCC"]]
    assert body["status"] == "FULL"
    block = body["portfolio"]
    assert block["portfolio_id"] == portfolio_payload["portfolio_id"]
    assert len(block["members"]) == len(portfolio_payload["portfolio"]["members"])
    assert set(block["correlation"]) >= {"average_r_all_pairs", "average_r_significant_pairs", "significant_pairs"}
    assert "var_95_pct" in block["joint_simulation"] and "max_drawdown_pct" in block["book"]
    assert "merged order book" in block["scores_cover"]
    # The page-only internals stay off the wire.
    assert "formula_overrides" not in body and "evidence" not in body
    assert len(response.text) < 60_000


def test_a_slow_portfolio_answers_pending_with_a_link_that_says_so(
    tmp_path, monkeypatch, portfolio_payload
) -> None:
    import threading

    from Agent.backend.bot.mcp.aggregate import PortfolioAggregator
    from Agent.backend.web import app as app_module

    monkeypatch.setattr(app_module, "ANALYZE_SYNC_DEADLINE_SECONDS", 0.2)
    monkeypatch.setenv("NORABT_REPORT_BASE_URL", "https://agent.example.io")
    release = threading.Event()
    service = _service_with(_StubBotSource(), data_dir=tmp_path)
    calls = []

    def slow(codes, *, force=False, progress=None):
        calls.append(list(codes))
        release.wait(10)
        return portfolio_payload

    service.analyze_portfolio = slow
    # One event loop for every request (as under uvicorn): without the
    # context manager each TestClient call runs on a fresh loop that is torn
    # down afterwards, taking the background run with it.
    client = _client_for(service).__enter__()
    try:
        body = client.post("/api/analyze", json={"code": "AAA,BBB"}).json()
        requested = PortfolioAggregator.portfolio_id(["AAA", "BBB"])
        assert body["status"] == "PENDING"
        assert body["risk"] is None and body["verdict"] is None
        assert body["member_codes"] == ["AAA", "BBB"]
        if "report_url" in body:
            assert body["report_url"].endswith(f"/portfolio/{requested}")
        # The link handed out says "running", not 404.
        page = client.get(f"/portfolio/{requested}")
        assert page.status_code == 202 and "being analysed" in page.text
        # Asking again joins the run instead of starting another.
        client.post("/api/analyze", json={"code": "BBB AAA"})
        assert len(calls) == 1
    finally:
        release.set()
        client.__exit__(None, None, None)


def test_a_bad_code_in_the_list_is_a_400_before_any_run(tmp_path) -> None:
    service = _service_with(_StubBotSource(), data_dir=tmp_path)
    service.analyze_portfolio = lambda *a, **k: pytest.fail("must not run")
    response = _client_for(service).post("/api/analyze", json={"code": "AAA,bad-code!"})
    assert response.status_code == 400
    too_many = ",".join(f"CODE{i}" for i in range(9))
    assert _client_for(service).post("/api/analyze", json={"code": too_many}).status_code == 400


def test_a_run_whose_id_changed_keeps_the_pending_link_alive(tmp_path, portfolio_payload) -> None:
    from Agent.backend.web.data import write_portfolio_alias, write_portfolio_document

    service = _service_with(_StubBotSource(), data_dir=tmp_path)
    write_portfolio_document(tmp_path, portfolio_payload)
    write_portfolio_alias(tmp_path, "PORT_AAAAAAAAAAAA", portfolio_payload["portfolio_id"])
    assert service.portfolio_report("PORT_AAAAAAAAAAAA")["portfolio_id"] == portfolio_payload["portfolio_id"]
