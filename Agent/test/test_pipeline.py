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
from Agent.test.conftest import FIXED_AS_OF_MS

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
