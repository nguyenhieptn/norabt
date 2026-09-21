"""Dữ liệu cho khối "CHÚ THÍCH GIẢI THÍCH ĐIỂM SỐ" trên trang `/bot/<code>`.

VÌ SAO TỒN TẠI: yêu cầu gốc của chủ dự án là "nên có sao ở đó để giải thích
những tiêu chí và công thức để ra được score đấy" -- ba con số lớn nhất
trang (điểm rủi ro, điểm chất lượng, độ tin cậy) trước đây không có cách nào
để người đọc tự kiểm được CHÚNG ĐẾN TỪ ĐÂU cho đúng bot đang xem, ngoài việc
đọc mã nguồn.

Module này CHỈ GOM/TÍNH dữ liệu để giải thích -- không dựng HTML (đó là việc
của `Agent/backend/web/report_page.py`, xem hàm `_render_score_basis`), và
KHÔNG tính lại bất kỳ điểm rủi ro/chất lượng/độ tin cậy nào của
`Agent/backend/qc/scoring/fusion.py` hay `Agent/backend/analysis/limited.py`
-- cùng kỷ luật `loss_analysis.py`/`limited_view.py` đã theo: đọc lại đúng
những con số hai module đó đã tính và đã ghi vào `evidence`, không suy diễn
số mới. Ngoại lệ DUY NHẤT là ba phép TỔNG HỢP thuần cộng/nhân bên dưới
(`_noisy_or_combine`, tính phủ sóng, tính trần theo số luồng) cho nhánh
LIMITED: `Agent/backend/analysis/limited.py` không tự ghi các số hạng trung
gian này ra `evidence` (chỉ ghi con số `confidence` cuối cùng đã làm tròn),
nên đây là nơi DUY NHẤT có thể tái dựng chúng cho người đọc mà không phải
sửa `limited.py`. Ba hằng số dùng để tái dựng (`_SOURCE_DEPENDENCE_DISCOUNT`,
`_CONFIDENCE_CEILING_BASE`, `_CONFIDENCE_CEILING_PER_STREAM`,
`_CONFIDENCE_CEILING_ABSOLUTE`) là bản SAO CÓ CHỦ Ý của đúng hằng số cùng
tên trong `limited.py` -- cùng lý do và cùng quy ước
`Agent/backend/web/report_page.py` đã nêu cho `DIMENSION_LABEL_VI`/
`TIER_LABEL_VI` của nó (cây `Agent/backend/analysis/*` không phải chỗ module
trình bày này được sửa, nên sao chép rồi ghi rõ nguồn thay vì import riêng
tư). `Agent/none/test/test_score_basis.py` khoá chặt bằng cách so số tái dựng ở
đây với `result["confidence"]` thật của `assess_limited_bot` -- lệch hằng số
nào ở trên sẽ làm test đó đỏ ngay, không âm thầm trôi.

KHÔNG BỊA SỐ: mọi hàm dưới đây trả `None`/`[]` khi thiếu dữ liệu cần thiết,
không thay bằng 0 hay bằng giá trị "trung bình có vẻ hợp lý".
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

__all__ = [
    "VALIDATION_FULL_VI",
    "VALIDATION_LIMITED_VI",
    "QUALITY_METHOD_FULL_VI",
    "full_risk_dimensions",
    "full_fusion_summary",
    "full_confidence_basis",
    "limited_risk_components",
    "limited_fusion_summary",
    "limited_confidence_breakdown",
    "quality_basis_limited",
]


# --------------------------------------------------------------------------- #
# Văn bản kiểm chứng cố định -- giống hệt mọi bot trong cùng nhánh (đây là
# bằng chứng về PHƯƠNG PHÁP, không phải một phép tính riêng cho bot đang
# xem), nên đặt thành hằng số thay vì build lại mỗi lần render.
# --------------------------------------------------------------------------- #

# Đúng các con số `Agent/docs/out_of_sample_validation.md` đã công bố (36
# bot, chia 60/40 theo thời gian, không chia ngẫu nhiên -- xem tài liệu đó
# cho toàn bộ phương pháp). Nêu CẢ HAI chiều: cái đã chứng minh được và cái
# CHƯA -- tài liệu gốc tự nói rõ điều đó, nói một nửa sẽ là phóng đại.
VALIDATION_FULL_VI = (
    "This scale HAS been validated out of sample on 36 eligible bots "
    "(80 or more closed trades), scored with the production pipeline on the "
    "first 60% of trades (split by close time, not at random) and then "
    "measured against what actually happened over the remaining 40%: the "
    "Spearman rank correlation between the risk score and max drawdown in the "
    "second half is 0.64 (95% bootstrap confidence interval [0.39, 0.80], "
    "permutation test p = 0.000), and against whether the bot blew up at all "
    "it is 0.41 (95% CI [0.21, 0.59], p = 0.013) \u2014 neither interval contains "
    "zero. That same document ALSO states what it could not show: the "
    "correlation with second-half return (0.205, 95% CI [-0.20, 0.54]) and "
    "with second-half win rate (-0.161, 95% CI [-0.48, 0.17]) both have "
    "confidence intervals containing zero, so neither is established. Read a "
    "high risk score as a higher probability of drawdown or blow-up, NOT as "
    "\u2018this bot will earn less\u2019. See Agent/docs/out_of_sample_validation.md "
    "for the full method and its limits (sample of 36 bots, a single market "
    "period, and bots that are not independent of one another)."
)

VALIDATION_LIMITED_VI = (
    "This scale has NOT been validated out of sample. The validation run on "
    "the full branch (36 bots, split 60/40 by trade close time, then measured "
    "against what actually happened in the second half) needs the trade-by-"
    "trade ledger in order to split it into two halves at all \u2014 a bot that "
    "hides its ledger (OKX returns error 60004) does not expose that data, so "
    "the same validation cannot be run for this branch. The score here rests "
    "only on internal grounds: an explicit formula plus the bot\u2019s percentile "
    "within the population already scored (see below). There is no measured "
    "evidence that it predicts future outcomes."
)

# Mô tả 5 thành phần điểm chất lượng nhánh FULL bằng lời -- KHÔNG kèm trọng
# số cụ thể (những con số đó sống trong `Agent/backend/qc/scoring/quality.py`,
# một cây off-limits cho việc này; nêu lại bằng số ở đây có nguy cơ trôi khỏi
# module thật mà không ai biết). Đây là mô tả PHƯƠNG PHÁP, đúng với mọi bot,
# không phải số liệu riêng của bot đang xem.
QUALITY_METHOD_FULL_VI = (
    "The quality score measures whether a bot is GOOD \u2014 a different question "
    "from whether it is risky (a bot that barely trades can look safe on every "
    "risk dimension while earning nothing). It has five components, each "
    "scored from zero to one hundred with its own weight, computed separately "
    "from the risk score above: ability to make money (measured on the book "
    "marked to market, so a position sitting at a loss is not counted as a "
    "gain), stability, drawdown control, honesty (published PnL reconciled "
    "against PnL recomputed from the ledger itself) and strategy durability. "
    "A component that cannot be measured is dropped from BOTH the numerator "
    "and the denominator of the weighted average; it is never given a neutral "
    "value. How much each component contributed for THIS particular bot is "
    "not yet surfaced on the report page \u2014 only the total appears here."
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _finite_float(value: Any) -> Optional[float]:
    """`float(value)` if that is a finite real number, `None` otherwise.

    Accepts a numeric STRING too (`"0.62"`, `"400"`) -- `evidence.profile`/
    `evidence.stats` are the raw OKX dicts passed straight through by
    `Agent/backend/analysis/limited.py` (see that module's `_float`, which
    does the exact same string parsing before this module ever sees the
    values), so refusing strings here would silently read every real
    `leadDays`/`winRatio`/... field as missing.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None
    return (
        number
        if number == number and number not in (float("inf"), float("-inf"))
        else None
    )


# --------------------------------------------------------------------------- #
# Nhánh FULL -- đọc `evidence.dimensions` / `evidence.score_breakdown`.
#
# Hai hình dạng khác nhau tồn tại song song cho CÙNG hai khoá này (xem
# `Agent/backend/web/data.py`):
#   * đường CHẤM SỐNG (`_full_result`): `dimensions[k]` có đủ
#     `score/weight/status/tier/confidence/key_findings`; `score_breakdown`
#     có đủ `contributions/total_weight/applicable_dimensions/...`.
#   * đường ĐỌC TỪ ĐĨA (`assessment_to_analyze_result`, phục vụ phần lớn
#     lượt xem thật -- bot đã chấm sẵn): nay mang đủ `weight`/`confidence`
#     từng chiều, `total_weight`/`applicable_dimensions`, `data_quality` và
#     `market_available`. Hai hình dạng vì thế đã HỘI TỤ ở mọi trường có
#     hiển thị; phần còn lệch (`contributions`, `current_state`,
#     `reconciliation`, `market_resolution`, `eligibility_reason`,
#     `universe_eligible`) không chỗ nào trên trang đọc tới -- đã kiểm bằng
#     grep từng khoá trong `report_page.py` -- nên để nguyên thay vì phình
#     bản ghi trên đĩa bằng dữ liệu không ai đọc.
#     Bản ghi ghi TRƯỚC đợt hội tụ này vẫn thiếu các trường trên và vẫn
#     phải đọc được (mọi hàm dưới đây degrade về `None`, không bịa số).
# Mọi hàm dưới đây đọc CẢ HAI hình dạng, để `None` đúng những trường hình
# dạng đọc-từ-đĩa không có, thay vì bịa trọng số bằng nhau cho mọi chiều.
# --------------------------------------------------------------------------- #


def full_risk_dimensions(evidence: Any) -> List[Dict[str, Any]]:
    """Từng chiều rủi ro của bot, theo đúng thứ tự trong `evidence.dimensions`.

    Mỗi phần tử: `{"name", "score", "status", "tier", "weight", "confidence"}`
    -- hai trường cuối là `None` khi hình dạng `evidence` không mang chúng
    (đọc từ đĩa). `[]` khi `evidence.dimensions` thiếu/không phải dict.
    """
    dims = _mapping(evidence).get("dimensions")
    if not isinstance(dims, Mapping) or not dims:
        return []
    rows: List[Dict[str, Any]] = []
    for name, raw in dims.items():
        dim = _mapping(raw)
        rows.append(
            {
                "name": name,
                "score": _finite_float(dim.get("score")),
                "status": dim.get("status"),
                "tier": dim.get("tier"),
                "weight": _finite_float(dim.get("weight")),
                "confidence": _finite_float(dim.get("confidence")),
                # Câu do CHÍNH ống kính viết ra khi nó không đo được
                # (`qc/evaluator/common.py::unknown`). Chỉ lấy ở chiều không
                # đo được: ở chiều đo được, `key_findings` là bằng chứng chấm
                # điểm và đã hiển thị ở chỗ khác. `None` với bản ghi cũ.
                "reason": _unknown_reason(dim),
            }
        )
    return rows


def _unknown_reason(dim: Mapping) -> Optional[str]:
    if str(dim.get("status") or "").upper() == "AVAILABLE":
        return None
    findings = dim.get("key_findings")
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, str) and finding.strip():
                return finding.strip()
    return None


def full_fusion_summary(evidence: Any) -> Dict[str, Any]:
    """Cách 10 chiều trên được hợp nhất thành MỘT điểm rủi ro.

    `has_rich_breakdown=True` khi `score_breakdown` mang đủ `contributions`/
    `total_weight` (đường chấm sống) -- báo cho nơi gọi biết có thể nói cụ
    thể "N chiều, tổng trọng số W" hay chỉ có thể nói chung chung "trung bình
    có trọng số, chi tiết trọng số không có trong bản ghi đã lưu".
    """
    sb = _mapping(_mapping(evidence).get("score_breakdown"))
    veto_reasons = [r for r in (sb.get("veto_reasons") or []) if isinstance(r, str)]
    return {
        "decided_by": sb.get("decided_by")
        if isinstance(sb.get("decided_by"), str)
        else None,
        "veto_reasons": veto_reasons,
        "weighted_average": _finite_float(sb.get("weighted_average")),
        "final_score": _finite_float(sb.get("final_score")),
        "total_weight": _finite_float(sb.get("total_weight")),
        "applicable_dimensions": (
            int(sb["applicable_dimensions"])
            if isinstance(sb.get("applicable_dimensions"), (int, float))
            and not isinstance(sb.get("applicable_dimensions"), bool)
            else None
        ),
        # Khoá vào ĐÚNG hai số câu giải thích dùng ("N chiều, tổng trọng
        # số W"), chứ không vào `contributions` -- danh sách đó không
        # xuất hiện trong câu nào cả, nên đòi nó chỉ khiến đường đọc-từ-
        # đĩa (phần lớn lượt xem thật) vĩnh viễn rơi về câu chung chung.
        "has_rich_breakdown": (
            _finite_float(sb.get("total_weight")) is not None
            and sb.get("applicable_dimensions") is not None
        ),
    }


def full_confidence_basis(evidence: Any) -> Dict[str, Any]:
    """Những mảnh có sẵn để giải thích độ tin cậy của MỘT bot FULL.

    Công thức thật (`Agent/backend/qc/scoring/fusion.py::fuse`) là
    `min(100, nguồn_tin_cậy x độ_tin_cậy_theo_chiều x 100)`, trong đó
    `nguồn_tin_cậy` trộn chất lượng dữ liệu của bot (và của thị trường, nếu
    có) còn `độ_tin_cậy_theo_chiều` là trung bình có trọng số của
    `confidence` từng chiều. Chỉ mảnh ĐẦU (`evidence.data_quality`, có ở
    đường chấm sống, không có ở đường đọc từ đĩa) và cờ "có `confidence`
    riêng từng chiều hay không" là thứ module này có thể đọc lại trung thực
    -- không tự bịa ra hai con số trung gian khi chúng vắng mặt.
    """
    dq = _mapping(_mapping(evidence).get("data_quality"))
    dims = full_risk_dimensions(evidence)
    dims_with_confidence = [d for d in dims if d["confidence"] is not None]
    return {
        "bot_overall_score": _finite_float(dq.get("overall_score")),
        "bot_freshness_score": _finite_float(dq.get("freshness_score")),
        "has_data_quality": bool(dq),
        "has_market_context": bool(_mapping(evidence).get("market_available", True)),
        "dimension_confidence_count": len(dims_with_confidence),
        "dimension_count": len(dims),
    }


# --------------------------------------------------------------------------- #
# Nhánh LIMITED -- đọc `evidence.components` (danh sách phẳng do
# `Agent/backend/analysis/limited.py::assess_limited_bot` ghi ra, mỗi phần
# tử đã là `_Component.to_dict()`: name/label/score/weight/status/
# confidence/findings -- KHÔNG có hình dạng rút gọn nào khác, luôn đủ cả 6
# trường vì đây luôn là đường chấm sống, không có "đọc từ đĩa" riêng).
# --------------------------------------------------------------------------- #


def limited_risk_components(evidence: Any) -> List[Dict[str, Any]]:
    """Từng thành phần góp vào điểm rủi ro LIMITED, giữ nguyên thứ tự ghi
    trong `evidence.components` (rủi ro giảm dần theo cách `limited.py` xây
    danh sách: sụt vốn, ổn định, nhịp lợi nhuận, Monte Carlo, rồi 4 chiều bị
    che). `[]` khi `evidence.components` thiếu/rỗng.
    """
    components = _mapping(evidence).get("components")
    if not isinstance(components, list):
        return []
    rows: List[Dict[str, Any]] = []
    for raw in components:
        if not isinstance(raw, Mapping):
            continue
        rows.append(
            {
                "name": raw.get("name"),
                "label": raw.get("label"),
                "score": _finite_float(raw.get("score")),
                "weight": _finite_float(raw.get("weight")),
                "status": raw.get("status"),
                "confidence": _finite_float(raw.get("confidence")),
                "findings": [
                    f for f in (raw.get("findings") or []) if isinstance(f, str)
                ],
            }
        )
    return rows


def limited_fusion_summary(components: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Trung bình có trọng số thật sự đứng sau điểm rủi ro LIMITED.

    Nhánh này KHÔNG có sàn veto/quy tắc khẩn cấp nào (khác nhánh FULL) --
    điểm rủi ro LUÔN ĐÚNG BẰNG trung bình có trọng số của các thành phần
    trên, không có ngoại lệ nào ghi đè nó. `weighted_average=None` khi tổng
    trọng số bằng 0 (không có thành phần nào mang trọng số dương).
    """
    total_weight = sum(c["weight"] for c in components if c.get("weight") is not None)
    if total_weight <= 0:
        return {"weighted_average": None, "total_weight": 0.0}
    weighted_sum = sum(
        c["score"] * c["weight"]
        for c in components
        if c.get("weight") is not None and c.get("score") is not None
    )
    return {
        "weighted_average": max(0.0, min(100.0, weighted_sum / total_weight)),
        "total_weight": total_weight,
    }


# Bản sao có chủ đích của các hằng số cùng tên trong
# `Agent/backend/analysis/limited.py` -- xem module docstring ở trên cho lý
# do và cho tấm khoá chống trôi (`Agent/none/test/test_score_basis.py`).
_SOURCE_DEPENDENCE_DISCOUNT = 0.8
_CONFIDENCE_CEILING_BASE = 15.0
_CONFIDENCE_CEILING_PER_STREAM = 7.5
_CONFIDENCE_CEILING_ABSOLUTE = 45.0

_STREAM_LABELS_VI = (
    ("drawdown", "weekly equity curve (public-weekly-pnl)"),
    ("return_path", "cumulative return series (pnlRatios, public-lead-traders)"),
    ("stats", "daily win/loss statistics (public-stats)"),
    ("profile", "lead-trader ranking profile (public-lead-traders)"),
)


def _noisy_or_combine(confidences: Sequence[float]) -> float:
    """`1 - Π(1 - c_i x discount^i)` trên các `c_i` đã sắp giảm dần -- đúng
    quy tắc `Agent/backend/analysis/limited.py::_combine_measured_confidence`
    dùng để gộp độ tin cậy của các chiều ĐO ĐƯỢC (xem module đó cho lý do
    "noisy-OR" thay vì trung bình cộng).
    """
    remaining = 1.0
    for index, value in enumerate(sorted(confidences, reverse=True)):
        discounted = value * (_SOURCE_DEPENDENCE_DISCOUNT**index)
        remaining *= 1.0 - max(0.0, min(1.0, discounted))
    return 1.0 - remaining


def limited_confidence_breakdown(evidence: Any) -> Optional[Dict[str, Any]]:
    """Tái dựng đúng công thức độ tin cậy LIMITED cho bot đang xem, từ dữ
    liệu thô đã có sẵn trong `evidence` (không cần gọi lại `limited.py`).

    Trả `None` khi `evidence.components` thiếu -- không có gì để tái dựng.
    """
    components = limited_risk_components(evidence)
    if not components:
        return None

    measured = [
        c["confidence"]
        for c in components
        if c.get("status") == "AVAILABLE" and (c.get("confidence") or 0.0) > 0.0
    ]
    measured_confidence = _noisy_or_combine(measured) if measured else 0.0

    total_weight = sum(c["weight"] for c in components if c.get("weight") is not None)
    available_weight = sum(
        c["weight"]
        for c in components
        if c.get("status") == "AVAILABLE" and c.get("weight") is not None
    )
    coverage = (available_weight / total_weight) if total_weight > 0 else 0.0

    by_name = {c.get("name"): c for c in components}
    profile = _mapping(evidence).get("profile")
    stats = _mapping(evidence).get("stats")
    stream_present = {
        "drawdown": (by_name.get("drawdown") or {}).get("status") == "AVAILABLE",
        "return_path": (by_name.get("return_path") or {}).get("status") == "AVAILABLE",
        # Cùng vị từ `Agent/backend/analysis/limited.py::_independent_stream_count`
        # dùng, đọc thẳng trên field OKX gốc thay vì gọi lại hàm private đó.
        "stats": bool(
            stats
            and (
                _finite_float(_mapping(stats).get("winRatio")) is not None
                or _finite_float(_mapping(stats).get("investAmt")) is not None
                or _finite_float(_mapping(stats).get("profitDays")) is not None
            )
        ),
        "profile": bool(
            profile
            and any(
                _finite_float(_mapping(profile).get(key)) is not None
                for key in ("aum", "pnl", "pnlRatio")
            )
        ),
    }
    streams = sum(1 for present in stream_present.values() if present)
    ceiling = min(
        _CONFIDENCE_CEILING_ABSOLUTE,
        _CONFIDENCE_CEILING_BASE + _CONFIDENCE_CEILING_PER_STREAM * streams,
    )
    dimension_confidence = measured_confidence * coverage
    implied_confidence_pct = min(ceiling, dimension_confidence * 100.0)

    return {
        "measured_confidence_pct": measured_confidence * 100.0,
        "coverage_pct": coverage * 100.0,
        "streams": streams,
        "stream_detail": [
            (label, stream_present[key]) for key, label in _STREAM_LABELS_VI
        ],
        "ceiling_pct": ceiling,
        "implied_confidence_pct": implied_confidence_pct,
    }


def quality_basis_limited(evidence: Any) -> Optional[Dict[str, Any]]:
    """Các con số ĐẦU VÀO thật của công thức điểm chất lượng LIMITED
    (`Agent/backend/analysis/limited.py::_quality_score`): điểm khởi đầu 50,
    cộng tới 15 theo số ngày lead trader, cộng 10/trừ 20 theo dấu PnL, cộng
    `(tỉ lệ ngày lãi - 50%) x 40`, trừ 30 nếu đường vốn từng về 0, rồi chặn
    trần 75/100. Trả các ĐẦU VÀO (đọc thẳng từ `evidence.profile/stats`),
    không tính lại điểm cuối -- việc tính điểm là của `limited.py`, ở đây
    chỉ nêu căn cứ.

    `None` khi cả `profile` lẫn `stats` đều rỗng -- không có gì để giải
    thích.
    """
    profile = _mapping(_mapping(evidence).get("profile"))
    stats = _mapping(_mapping(evidence).get("stats"))
    if not profile and not stats:
        return None
    dd = _mapping(evidence).get("drawdown_summary")
    wiped_out = (
        bool(_mapping(dd).get("wiped_out")) if isinstance(dd, Mapping) else False
    )
    lead_days_value = _finite_float(profile.get("leadDays"))
    win_ratio = _finite_float(stats.get("winRatio"))
    return {
        "lead_days": int(round(lead_days_value))
        if lead_days_value is not None
        else None,
        "pnl": _finite_float(profile.get("pnl")),
        "win_ratio_pct": win_ratio * 100.0 if win_ratio is not None else None,
        "wiped_out": wiped_out,
        "cap": 75.0,
    }
