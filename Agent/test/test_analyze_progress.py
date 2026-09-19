"""Test cho `Agent/backend/web/progress.py` (Việc B, plan_progress.md) --
registry trong bộ nhớ, thread-safe, cho thanh tiến độ THẬT của `POST
/api/analyze`. Module này là module-level state (một registry DÙNG CHUNG
cho cả tiến trình test, giống hệt production) -- mọi test dưới đây gọi
`progress._reset_for_tests()` TRƯỚC KHI chạy để không thấy bản ghi của test
khác để lại.
"""

from __future__ import annotations

import threading
import time

import pytest

from Agent.backend.web import progress


@pytest.fixture(autouse=True)
def _clean_registry():
    progress._reset_for_tests()
    yield
    progress._reset_for_tests()


def test_get_unknown_code_returns_none() -> None:
    assert progress.get("NEVER_SEEN_CODE") is None


def test_start_then_get_reports_running_at_stage_zero() -> None:
    progress.start("CODE1")
    record = progress.get("CODE1")
    assert record is not None
    assert record["state"] == "running"
    assert record["stage"] is None
    assert record["stage_index"] == 0
    assert record["stage_count"] == progress.STAGE_COUNT
    assert record["stage_label"] is None
    assert record["error"] is None
    assert record["elapsed_ms"] >= 0


def test_mark_advances_stage_index_in_declared_order() -> None:
    progress.start("CODE1")
    for expected_index, stage in enumerate(progress.STAGES, start=1):
        progress.mark("CODE1", stage)
        record = progress.get("CODE1")
        assert record["state"] == "running"
        assert record["stage"] == stage
        assert record["stage_index"] == expected_index
        assert record["stage_label"] == progress.STAGE_LABELS_VI[stage]


def test_mark_unknown_stage_name_keeps_previous_index_but_updates_label() -> None:
    progress.start("CODE1")
    progress.mark("CODE1", "ledger")
    progress.mark("CODE1", "some_future_stage_not_declared_yet")
    record = progress.get("CODE1")
    # Không đoán chỉ số -- giữ nguyên stage_index của chặng đã biết gần nhất.
    assert record["stage_index"] == 1
    assert record["stage"] == "some_future_stage_not_declared_yet"
    assert record["stage_label"] is None


def test_mark_on_never_started_code_is_a_silent_noop() -> None:
    progress.mark("GHOST_CODE", "ledger")
    assert progress.get("GHOST_CODE") is None


def test_mark_after_finish_is_a_silent_noop() -> None:
    progress.start("CODE1")
    progress.finish("CODE1")
    progress.mark("CODE1", "ledger")
    record = progress.get("CODE1")
    assert record["state"] == "done"
    assert record["stage"] == "done"


def test_finish_sets_done_state_at_full_stage_count() -> None:
    progress.start("CODE1")
    progress.mark("CODE1", "ledger")
    progress.finish("CODE1")
    record = progress.get("CODE1")
    assert record["state"] == "done"
    assert record["stage"] == "done"
    assert record["stage_index"] == progress.STAGE_COUNT
    assert record["error"] is None


def test_finish_without_prior_start_still_produces_a_done_record() -> None:
    progress.finish("NEVER_STARTED")
    record = progress.get("NEVER_STARTED")
    assert record is not None
    assert record["state"] == "done"


def test_fail_sets_error_state_and_keeps_message() -> None:
    progress.start("CODE1")
    progress.mark("CODE1", "markets")
    progress.fail("CODE1", "OKX không trả lời")
    record = progress.get("CODE1")
    assert record["state"] == "error"
    assert record["error"] == "OKX không trả lời"
    # Chặng đã đạt được TRƯỚC khi lỗi vẫn được giữ lại, không bị xoá.
    assert record["stage"] == "markets"
    assert record["stage_index"] == 2


def test_fail_without_prior_start_still_produces_an_error_record() -> None:
    progress.fail("NEVER_STARTED", "quá tải")
    record = progress.get("NEVER_STARTED")
    assert record is not None
    assert record["state"] == "error"
    assert record["error"] == "quá tải"


def test_start_again_for_same_code_resets_not_accumulates() -> None:
    progress.start("CODE1")
    progress.mark("CODE1", "decision")
    progress.finish("CODE1")
    progress.start("CODE1")
    record = progress.get("CODE1")
    assert record["state"] == "running"
    assert record["stage"] is None
    assert record["stage_index"] == 0


def test_get_returns_a_copy_not_the_live_record() -> None:
    """Mutating the dict `get()` handed back must never leak back into the
    registry -- callers (app.py's JSON response builder) are free to treat
    it as a disposable snapshot."""
    progress.start("CODE1")
    record = progress.get("CODE1")
    record["state"] = "corrupted"
    record["stage_index"] = 999
    fresh = progress.get("CODE1")
    assert fresh["state"] == "running"
    assert fresh["stage_index"] == 0


# --------------------------------------------------------------------------- #
# TTL cho bản ghi done/error, và trần cứng số bản ghi -- cả hai monkeypatch
# thẳng `time.monotonic`/hằng số module để test không phải NGỦ THẬT.
# --------------------------------------------------------------------------- #


def test_done_record_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_now = [1_000.0]
    monkeypatch.setattr(progress.time, "monotonic", lambda: fake_now[0])
    monkeypatch.setattr(progress, "DONE_TTL_SECONDS", 60)

    progress.start("CODE1")
    progress.finish("CODE1")
    assert progress.get("CODE1") is not None

    # Vẫn trong hạn (59s < 60s TTL) -- một prune ngẫu nhiên (start() của một
    # mã khác) không được phép xoá sớm.
    fake_now[0] += 59
    progress.start("CODE2")
    assert progress.get("CODE1") is not None

    # Quá hạn (61s > 60s TTL) -- lần prune tiếp theo (bất kỳ start/finish/
    # fail nào) phải dọn CODE1.
    fake_now[0] += 2
    progress.start("CODE3")
    assert progress.get("CODE1") is None


def test_running_record_never_expires_by_ttl_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TTL chỉ áp dụng cho done/error -- một mã đang "running" (pipeline
    thật sự còn chạy) không bao giờ bị dọn chỉ vì trôi qua TTL, kể cả khi nó
    chạy lâu hơn DONE_TTL_SECONDS thật (một lượt phân tích Monte Carlo nặng
    hoàn toàn có thể mất hơn 5 phút)."""
    fake_now = [1_000.0]
    monkeypatch.setattr(progress.time, "monotonic", lambda: fake_now[0])
    monkeypatch.setattr(progress, "DONE_TTL_SECONDS", 60)

    progress.start("CODE1")
    fake_now[0] += 10_000  # rất lâu sau TTL
    progress.start("CODE2")  # kích hoạt một lượt prune
    record = progress.get("CODE1")
    assert record is not None
    assert record["state"] == "running"


def test_max_records_evicts_oldest_first(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_now = [1_000.0]
    monkeypatch.setattr(progress.time, "monotonic", lambda: fake_now[0])
    monkeypatch.setattr(progress, "MAX_RECORDS", 3)

    for i in range(3):
        fake_now[0] += 1
        progress.start(f"CODE{i}")
    # Đủ 3 mã, đúng trần -- chưa ai bị dọn.
    for i in range(3):
        assert progress.get(f"CODE{i}") is not None

    # Mã thứ 4 vượt trần -- CODE0 (cũ nhất theo updated_ms) phải bị dọn.
    fake_now[0] += 1
    progress.start("CODE3")
    assert progress.get("CODE0") is None
    assert progress.get("CODE1") is not None
    assert progress.get("CODE2") is not None
    assert progress.get("CODE3") is not None


def test_max_records_cap_applies_even_to_running_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trần cứng áp dụng cho MỌI trạng thái, kể cả "running" -- một mã chạy
    quá lâu, bị hàng trăm mã khác đè lên, chỉ mất thanh tiến độ (registry),
    KHÔNG làm pipeline thật của nó (chạy hoàn toàn độc lập với registry này)
    bị huỷ hay lỗi gì cả -- test này chỉ khoá hành vi của registry, không
    đụng gì tới pipeline thật."""
    fake_now = [1_000.0]
    monkeypatch.setattr(progress.time, "monotonic", lambda: fake_now[0])
    monkeypatch.setattr(progress, "MAX_RECORDS", 1)

    progress.start("OLDEST_STILL_RUNNING")
    fake_now[0] += 1
    progress.start("NEWER")
    assert progress.get("OLDEST_STILL_RUNNING") is None
    assert progress.get("NEWER") is not None


# --------------------------------------------------------------------------- #
# Thread-safety: pipeline thật chạy trên một worker thread (run_in_
# threadpool), trong khi GET /api/analyze/status đọc từ thread chính chạy
# vòng lặp asyncio -- registry phải chịu được đọc/ghi đồng thời từ nhiều
# thread mà không crash/deadlock/mất dữ liệu.
# --------------------------------------------------------------------------- #


def test_concurrent_mark_and_get_from_many_threads_does_not_crash() -> None:
    codes = [f"CONC_CODE_{i}" for i in range(20)]
    for code in codes:
        progress.start(code)

    errors: list[BaseException] = []

    def _writer(code: str) -> None:
        try:
            for stage in progress.STAGES:
                progress.mark(code, stage)
                time.sleep(0.001)
            progress.finish(code)
        except BaseException as exc:  # noqa: BLE001 - test assertion, not prod code
            errors.append(exc)

    def _reader() -> None:
        try:
            for _ in range(200):
                for code in codes:
                    progress.get(code)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_writer, args=(code,)) for code in codes]
    threads += [threading.Thread(target=_reader) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert not errors, f"lỗi trong thread nền: {errors!r}"
    for code in codes:
        record = progress.get(code)
        assert record is not None
        assert record["state"] == "done"
