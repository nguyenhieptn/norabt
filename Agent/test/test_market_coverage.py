"""Tests for `Agent/backend/market/coverage.py` -- chọn và giải NHIỀU thị
trường theo mục tiêu phủ sóng (thay "luôn đúng 2 thị trường: chính + phụ").

`plan_market_coverage` là hàm thuần (không I/O): test bằng dict thường.
`resolve_planned_markets` gọi mạng qua một `resolve_fn` do caller cung cấp
-- ở đây luôn là một hàm giả lập (không network thật), một số test dùng
`time.sleep` NGẮN (<=0.3s) để mô phỏng một symbol chậm/timeout, vì
`concurrent.futures.wait(timeout=...)` cần thời gian THẬT trôi qua để kích
hoạt (không có đồng hồ giả tương đương cho API này).
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import pytest

from Agent.backend.market.coverage import (
    MARKET_COVERAGE_TARGET,
    plan_market_coverage,
    resolve_planned_markets,
)


# --------------------------------------------------------------------------- #
# plan_market_coverage
# --------------------------------------------------------------------------- #


def test_plan_stops_once_cumulative_share_reaches_target():
    exposure = {"AAA": 0.50, "BBB": 0.20, "CCC": 0.15, "DDD": 0.10, "EEE": 0.05}
    planned = plan_market_coverage("AAA", exposure, target=0.80, max_markets=8)
    # AAA (0.50) + BBB (0.20) = 0.70 < 0.80 -> thêm CCC (0.15) -> 0.85 >= 0.80 -> dừng.
    assert planned == ["AAA", "BBB", "CCC"]


def test_plan_includes_primary_even_with_zero_exposure_reported():
    """Thị trường CHÍNH luôn đứng đầu và luôn có mặt, kể cả khi
    `exposure_share` hoàn toàn không đo được gì cho nó (ví dụ bot không có
    lệnh đã chốt nào)."""
    planned = plan_market_coverage("AAA", {})
    assert planned == ["AAA"]


def test_plan_respects_hard_cap_even_if_target_not_reached():
    """Có bot chạm 69 mã (Ail.Wang) trải đều -- trần cứng `max_markets`
    phải thắng mục tiêu phủ sóng, không được để MỘT bot kéo sập ngân sách.
    """
    exposure = {f"SYM{i}": 0.02 for i in range(50)}
    exposure["AAA"] = 0.0
    planned = plan_market_coverage("AAA", exposure, target=0.80, max_markets=8)
    assert len(planned) == 8
    assert planned[0] == "AAA"
    # Tổng share của 8 mã được chọn (AAA=0 + 7 mã 0.02) = 0.14, còn xa 0.80 --
    # đúng ý "không đạt mục tiêu thì báo cáo thật, không được vượt trần".
    assert sum(exposure[sym] for sym in planned) == pytest.approx(0.14)


def test_plan_picks_candidates_by_exposure_descending():
    exposure = {"AAA": 0.40, "SMALL": 0.05, "BIG": 0.30, "MED": 0.25}
    planned = plan_market_coverage("AAA", exposure, target=0.80, max_markets=8)
    # AAA(0.40) rồi BIG(0.30) rồi MED(0.25): 0.40+0.30=0.70<0.80, +0.25=0.95>=0.80 dừng.
    assert planned == ["AAA", "BIG", "MED"]


def test_plan_default_target_matches_module_constant():
    exposure = {"AAA": 1.0}
    # Mặc định target=MARKET_COVERAGE_TARGET (0.80) -- một bot chỉ giao
    # dịch một mã đã phủ 100% ngay từ thị trường CHÍNH, không cần thêm gì.
    planned = plan_market_coverage("AAA", exposure)
    assert planned == ["AAA"]
    assert MARKET_COVERAGE_TARGET == 0.80


# --------------------------------------------------------------------------- #
# resolve_planned_markets
# --------------------------------------------------------------------------- #


def _instant_resolve_fn(sym: str) -> Tuple[Optional[str], str]:
    return f"market-{sym}", "RESOLVED_CEX"


def test_resolve_empty_planned_returns_empty_dict():
    assert resolve_planned_markets([], "AAA", _instant_resolve_fn) == {}


def test_resolve_single_symbol_skips_threadpool_entirely(monkeypatch):
    """Đúng một symbol (bot chỉ giao dịch một mã) -- gọi thẳng `resolve_fn`,
    không dựng ThreadPoolExecutor cho một future duy nhất."""
    import Agent.backend.market.coverage as coverage_module

    def _boom(*args, **kwargs):  # pragma: no cover - phải không bao giờ chạy
        raise AssertionError("không được dựng ThreadPoolExecutor cho 1 symbol")

    monkeypatch.setattr(coverage_module.concurrent.futures, "ThreadPoolExecutor", _boom)
    result = resolve_planned_markets(["AAA"], "AAA", _instant_resolve_fn)
    assert result == {"AAA": ("market-AAA", "RESOLVED_CEX")}


def test_resolve_all_symbols_resolve_within_budget():
    result = resolve_planned_markets(
        ["AAA", "BBB", "CCC"], "AAA", _instant_resolve_fn, timeout_seconds=1.0
    )
    assert result == {
        "AAA": ("market-AAA", "RESOLVED_CEX"),
        "BBB": ("market-BBB", "RESOLVED_CEX"),
        "CCC": ("market-CCC", "RESOLVED_CEX"),
    }


def test_resolve_primary_waits_beyond_the_secondary_timeout_budget():
    """Thị trường CHÍNH đợi TỚI KHI XONG, không hạn chờ -- ngay cả khi nó
    chậm hơn NHIỀU so với ngân sách chờ của các thị trường phụ."""

    def resolve_fn(sym: str) -> Tuple[Optional[str], str]:
        if sym == "AAA":
            time.sleep(0.2)
        return f"market-{sym}", "RESOLVED_CEX"

    started = time.monotonic()
    result = resolve_planned_markets(
        ["AAA", "BBB"], "AAA", resolve_fn, timeout_seconds=0.01, max_workers=2
    )
    elapsed = time.monotonic() - started
    assert elapsed >= 0.2, "thị trường CHÍNH bị cắt ngang trước khi xong"
    assert result["AAA"] == ("market-AAA", "RESOLVED_CEX")
    assert result["BBB"] == ("market-BBB", "RESOLVED_CEX")


def test_resolve_drops_a_secondary_symbol_that_exceeds_the_shared_timeout():
    """Một thị trường PHỤ quá hạn chờ chung thì bị bỏ qua (vắng mặt trong
    kết quả) -- không được kéo cả lượt phân tích chờ theo."""

    def resolve_fn(sym: str) -> Tuple[Optional[str], str]:
        if sym == "SLOW":
            time.sleep(0.3)
        return f"market-{sym}", "RESOLVED_CEX"

    result = resolve_planned_markets(
        ["AAA", "SLOW", "FAST"],
        "AAA",
        resolve_fn,
        timeout_seconds=0.05,
        max_workers=3,
    )
    assert result["AAA"] == ("market-AAA", "RESOLVED_CEX")
    assert result["FAST"] == ("market-FAST", "RESOLVED_CEX")
    assert "SLOW" not in result


def test_resolve_shared_timeout_budget_is_not_multiplied_by_symbol_count():
    """Ngân sách chờ `timeout_seconds` là DÙNG CHUNG cho MỌI thị trường phụ
    trong một lượt gọi -- không nhân theo số lượng (5 thị trường phụ cùng
    chậm không được kéo dài 5x thời gian chờ)."""

    def resolve_fn(sym: str) -> Tuple[Optional[str], str]:
        if sym != "AAA":
            time.sleep(0.2)
        return f"market-{sym}", "RESOLVED_CEX"

    started = time.monotonic()
    result = resolve_planned_markets(
        ["AAA", "S1", "S2", "S3", "S4", "S5"],
        "AAA",
        resolve_fn,
        timeout_seconds=0.05,
        max_workers=6,
    )
    elapsed = time.monotonic() - started
    # Mọi thị trường phụ đều chậm hơn ngân sách -- tất cả bị bỏ qua, nhưng
    # tổng thời gian chờ THÊM (ngoài thời gian giải CHÍNH, ở đây gần như 0)
    # vẫn bị chặn ở đúng một lần `timeout_seconds`, không phải 5 lần.
    assert elapsed < 0.15
    assert set(result) == {"AAA"}


def test_resolve_an_unexpected_exception_in_a_secondary_symbol_is_swallowed():
    """Một lỗi bất ngờ khi giải thị trường PHỤ không được phép làm hỏng cả
    lượt phân tích -- symbol đó đơn giản vắng mặt trong kết quả."""

    def resolve_fn(sym: str) -> Tuple[Optional[str], str]:
        if sym == "BOOM":
            raise RuntimeError("OKX trả về something không mong đợi")
        return f"market-{sym}", "RESOLVED_CEX"

    result = resolve_planned_markets(
        ["AAA", "BOOM"], "AAA", resolve_fn, timeout_seconds=1.0, max_workers=2
    )
    assert result["AAA"] == ("market-AAA", "RESOLVED_CEX")
    assert "BOOM" not in result


def test_resolve_max_workers_never_exceeds_symbol_count():
    """Không tạo dư luồng so với số symbol cần giải -- xem
    `resolve_planned_markets`'s `workers = max(1, min(len(...), max_workers))`.
    Subclass THẬT của `ThreadPoolExecutor` (chỉ ghi lại `max_workers` rồi gọi
    `super().__init__`) để `submit`/`concurrent.futures.wait` bên trong hàm
    vẫn hoạt động y hệt bình thường -- không dùng một stand-in giả không
    tương thích với `concurrent.futures.wait`.
    """
    import concurrent.futures

    import Agent.backend.market.coverage as coverage_module

    seen_max_workers = {}

    class _RecordingExecutor(concurrent.futures.ThreadPoolExecutor):
        def __init__(self, max_workers=None, thread_name_prefix=""):
            seen_max_workers["value"] = max_workers
            super().__init__(
                max_workers=max_workers, thread_name_prefix=thread_name_prefix
            )

    original = coverage_module.concurrent.futures.ThreadPoolExecutor
    coverage_module.concurrent.futures.ThreadPoolExecutor = _RecordingExecutor
    try:
        resolve_planned_markets(
            ["AAA", "BBB", "CCC"], "AAA", _instant_resolve_fn, max_workers=6
        )
    finally:
        coverage_module.concurrent.futures.ThreadPoolExecutor = original
    assert seen_max_workers["value"] == 3
