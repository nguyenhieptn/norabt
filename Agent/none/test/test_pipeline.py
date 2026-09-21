"""Test cho `RiskSupervisionPipeline.run()`'s tham số `progress` mới (Việc A,
plan_progress.md) -- xem `Agent/backend/pipeline.py`'s docstring cho 4 ranh
giới THẬT nơi callback được gọi. Dùng lại đúng fixture on-disk
("MU"/"bot_BB3398A957270A39") mà `test_full_vertical_pipeline_is_safe_and_
typed` (test_new_architecture.py) đã dùng -- không cần mạng, không cần OKX
thật, đọc thẳng từ `Agent/data/` đã commit sẵn trong repo.
"""

from __future__ import annotations

from typing import List

import pytest

from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.none.test.conftest import FIXED_AS_OF_MS

_ASSET = "MU"
_BOT_FOLDER = "bot_BB3398A957270A39"


def _run_pipeline(**kwargs):
    return RiskSupervisionPipeline().run(
        _ASSET,
        _BOT_FOLDER,
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=100,
        **kwargs,
    )


def test_progress_none_default_never_called_and_result_unchanged() -> None:
    """`progress=None` (mặc định, không truyền) -- hành vi/kết quả PHẢI y
    hệt trước khi tham số này tồn tại. So sánh với một lượt gọi TƯỜNG MINH
    `progress=None` và với `test_full_vertical_pipeline_is_safe_and_typed`'s
    chính bộ tham số này (test_new_architecture.py)."""
    result_default = _run_pipeline()
    result_explicit_none = _run_pipeline(progress=None)

    for result in (result_default, result_explicit_none):
        assert result.traded_symbol == "MU"
        assert result.market_available is True
        assert result.risk_assessment.assessment_id
    assert (
        result_default.risk_assessment.assessment_id
        == result_explicit_none.risk_assessment.assessment_id
    )
    assert (
        result_default.risk_assessment.risk_score
        == result_explicit_none.risk_assessment.risk_score
    )


def test_progress_called_with_exactly_the_four_real_stages_in_order() -> None:
    """4 ranh giới THẬT, đúng thứ tự, đúng MỘT lần mỗi chặng -- không phải
    đồng hồ giả, không lặp lại, không thiếu chặng nào (xem pipeline.py's
    docstring của tham số `progress` cho vị trí từng lời gọi)."""
    calls: List[str] = []
    result = _run_pipeline(progress=calls.append)

    assert calls == ["ledger", "markets", "scoring", "decision"]
    # Kết quả vẫn đúng/đầy đủ như không có progress -- callback chỉ là một
    # side-channel quan sát, không được phép đổi hành vi tính toán.
    assert result.traded_symbol == "MU"
    assert result.risk_assessment.assessment_id


def test_progress_callback_exception_does_not_break_the_pipeline(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Một callback progress LỖI (vd. registry phía web có bug) không bao
    giờ được phép làm hỏng `run()` -- pipeline vẫn phải chạy xong và trả về
    kết quả hợp lệ y hệt như không có callback nào cả."""

    def _boom(stage: str) -> None:
        raise RuntimeError(f"test: progress callback lỗi giả lập ở {stage!r}")

    result = _run_pipeline(progress=_boom)

    assert result.traded_symbol == "MU"
    assert result.risk_assessment.assessment_id
    assert result.market_available is True


def test_progress_receives_string_stage_names_only() -> None:
    """Chỉ 4 tên chặng đã tài liệu hoá được gọi -- không có giá trị nào
    khác (số, None, object bí ẩn) lọt vào callback."""
    calls: List[str] = []
    _run_pipeline(progress=calls.append)
    assert all(isinstance(stage, str) for stage in calls)
    assert set(calls) <= {"ledger", "markets", "scoring", "decision"}


# --------------------------------------------------------------------------- #
# Speculative market pre-fetch (guess the primary market by the caller's own
# `asset` while the ledger loads, warm the process cache; correct itself for
# free when the guess is wrong).
# --------------------------------------------------------------------------- #


def test_speculative_prefetch_never_fires_under_pinned_as_of_ms():
    """The process-wide market cache is deliberately scoped to `as_of_ms is
    None` (live mode) only -- pinning a snapshot clock must stay fully
    reproducible, so the speculative thread must not even start."""
    import Agent.backend.pipeline as pipeline_module

    calls = []
    original = pipeline_module.RiskSupervisionPipeline.resolve_market

    def spy(self, traded_symbol, as_of_ms=None):  # noqa: ANN001
        calls.append(traded_symbol)
        return original(self, traded_symbol, as_of_ms)

    pipeline = RiskSupervisionPipeline(persist_history=False)
    pipeline.resolve_market = spy.__get__(pipeline, RiskSupervisionPipeline)
    pipeline.run(
        "MU",
        "bot_BB3398A957270A39",
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=10,
        simulation_horizon=5,
    )
    # Exactly one resolve per planned symbol -- no extra speculative call
    # sneaked in ahead of the ledger read.
    assert calls.count("MU") == 1


def test_speculative_prefetch_does_not_change_the_resolved_market():
    """With `as_of_ms=None` the speculative thread DOES start (it only warms
    the process cache). The result must be identical to the pinned-clock path:
    the primary market is whatever the LEDGER says, never whatever the guess
    happened to fetch."""
    from Agent.backend.pipeline import RiskSupervisionResult

    pipeline = RiskSupervisionPipeline(persist_history=False)
    result = pipeline.run(
        "MU",
        "bot_BB3398A957270A39",
        as_of_ms=None,
        simulation_iterations=10,
        simulation_horizon=5,
    )
    assert isinstance(result, RiskSupervisionResult)
    # Primary market comes from the ledger's own symbol, and matches it.
    assert result.traded_symbol == result.bot_result.identity.symbol
    if result.market_result is not None:
        assert result.market_result.symbol == result.traded_symbol


def test_a_brand_new_never_crawled_market_never_gets_substituted():
    """`CRCL` (real fixture) has a ledger but genuinely no crawled market
    data anywhere -- exactly a bot trading a brand-new/unknown market. Must
    fail closed (`market_available=False`, `market_result=None`), NEVER
    silently substitute a different, available market. The speculative
    pre-fetch thread must not change this: it is keyed on the EXACT symbol
    string, so warming the cache for one symbol can never leak into the
    resolution of a different, unrelated symbol."""
    from Agent.backend.pipeline import RiskSupervisionResult

    pipeline = RiskSupervisionPipeline(persist_history=False)
    result = pipeline.run(
        "CRCL",
        "bot_ACE79CAACA13F8B9",
        as_of_ms=None,  # speculative thread IS active for this call
        simulation_iterations=10,
        simulation_horizon=5,
    )
    assert isinstance(result, RiskSupervisionResult)
    assert result.traded_symbol == "CRCL"
    assert result.market_available is False
    assert result.market_resolution == "NO_MARKET_DATA_FOR_TRADED_SYMBOL"
    assert result.market_result is None
