"""Nguyên tắc: ít dữ liệu thì phải KẾT HỢP NHIỀU NGUỒN, và độ tin cậy phải
tỉ lệ với lượng bằng chứng thật.

Người dùng phát biểu nguyên tắc này hai lần, nên nó được khoá lại bằng test
chứ không chỉ nằm trong comment: (1) càng nhiều dữ liệu càng tin cậy,
(2) càng nhiều nguồn kết hợp được càng tin cậy, (3) thêm một nguồn KHÔNG BAO
GIỜ làm tin cậy giảm, (4) nhưng một bot giấu sổ lệnh dù giàu dữ liệu tới đâu
cũng không được tin bằng bot công khai kém tin cậy nhất.

Tính chất (3) chính là thứ bản đầu tiên làm sai: dùng trung bình có trọng
số nên thêm chiều `return_path` khiến độ tin cậy TỤT 12,8% -> 8,6%.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from Agent.backend.bot.analysis.limited import (
    STATUS_LIMITED,
    _CONFIDENCE_CEILING_ABSOLUTE,
    assess_limited_bot,
)

# Độ tin cậy THẤP NHẤT đo được trong 31 bot công khai đầy đủ của kho hiện
# tại (18/09). Trần của nhánh LIMITED phải luôn nằm dưới mốc này.
LOWEST_TRANSPARENT_BOT_CONFIDENCE = 50.8

_WEEK_MS = 604_800_000
_BASE_EQUITY = 10_000.0


def _weekly(n: int) -> List[Dict[str, Any]]:
    """Chuỗi tuần có quy mô vốn ỔN ĐỊNH (pnl/pnlRatio ~ hằng số) để không
    chạm chốt chặn `_MAX_IMPLIED_BASE_SPREAD` -- ở đây ta đang kiểm độ tin
    cậy, không kiểm chốt chặn đó."""
    out = []
    for i in range(n):
        pnl = 300.0 if i % 3 else -200.0
        out.append(
            {
                "beginTs": str(1_785_081_600_000 + i * _WEEK_MS),
                "pnl": f"{pnl:.2f}",
                "pnlRatio": f"{pnl / _BASE_EQUITY:.4f}",
            }
        )
    return out


def _profile(ratio_points: int = 0, rich: bool = True) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = (
        {
            "nickName": "Bot thử",
            "aum": "50000",
            "pnl": "5000",
            "pnlRatio": "0.1",
            "leadDays": "300",
        }
        if rich
        else {}
    )
    if ratio_points:
        payload["pnlRatios"] = [
            {
                "beginTs": str(1_785_081_600_000 + i * 432_000_000),
                "pnlRatio": f"{i * 0.05:.4f}",
            }
            for i in range(ratio_points)
        ]
    return payload or None


def _stats(days: int) -> Optional[Dict[str, Any]]:
    if not days:
        return None
    wins = int(days * 0.55)
    return {
        "winRatio": "0.55",
        "profitDays": str(wins),
        "lossDays": str(days - wins),
        "investAmt": "20000",
    }


def _confidence(
    *, weeks: int = 0, days: int = 0, ratio_points: int = 0, rich_profile: bool = True
) -> float:
    result = assess_limited_bot(
        code="TESTCODE00000001",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_profile(ratio_points, rich_profile),
        stats=_stats(days),
        weekly=_weekly(weeks) if weeks else None,
    )
    return float(result["confidence"])


# --------------------------------------------------------------------------- #
# (1) Càng nhiều DỮ LIỆU càng tin cậy
# --------------------------------------------------------------------------- #


def test_confidence_rises_with_the_volume_of_evidence() -> None:
    thin = _confidence(weeks=10, days=30, ratio_points=6)
    middling = _confidence(weeks=26, days=120, ratio_points=19)
    rich = _confidence(weeks=52, days=365, ratio_points=52)
    assert thin < middling < rich, (thin, middling, rich)


def test_a_single_extra_week_never_reduces_confidence() -> None:
    previous = 0.0
    for weeks in (10, 16, 24, 40, 52):
        current = _confidence(weeks=weeks, days=180, ratio_points=19)
        assert current >= previous - 1e-9, (weeks, current, previous)
        previous = current


# --------------------------------------------------------------------------- #
# (2)+(3) Càng nhiều NGUỒN càng tin cậy, và thêm nguồn không bao giờ làm giảm
# --------------------------------------------------------------------------- #


def test_each_additional_source_raises_or_holds_confidence() -> None:
    """Đây là tính chất bản đầu làm SAI: gộp bằng trung bình có trọng số nên
    thêm chiều `return_path` làm tụt 12,8% -> 8,6%."""
    steps = [
        _confidence(weeks=12, rich_profile=False),
        _confidence(weeks=12, days=172, rich_profile=False),
        _confidence(weeks=12, days=172, ratio_points=19, rich_profile=False),
        _confidence(weeks=12, days=172, ratio_points=19, rich_profile=True),
    ]
    assert all(steps[i] <= steps[i + 1] + 1e-9 for i in range(len(steps) - 1)), steps
    # Và phải TĂNG THẬT, không chỉ đứng yên: hai nguồn phải hơn hẳn một nguồn.
    assert steps[1] > steps[0]
    assert steps[2] > steps[1]


def test_combining_sources_beats_the_best_single_source() -> None:
    only_weekly = _confidence(weeks=12, rich_profile=False)
    only_stats = _confidence(days=172, rich_profile=False)
    combined = _confidence(weeks=12, days=172, ratio_points=19, rich_profile=False)
    assert combined > max(only_weekly, only_stats)


# --------------------------------------------------------------------------- #
# (4) Nhưng giấu sổ lệnh không bao giờ được tin bằng công khai
# --------------------------------------------------------------------------- #


def test_even_the_richest_limited_bot_stays_below_a_transparent_one() -> None:
    richest = _confidence(weeks=200, days=1000, ratio_points=200)
    assert richest <= _CONFIDENCE_CEILING_ABSOLUTE
    assert richest < LOWEST_TRANSPARENT_BOT_CONFIDENCE


def test_a_bot_with_no_usable_stream_gets_no_confidence() -> None:
    assert _confidence(rich_profile=False) == 0.0
