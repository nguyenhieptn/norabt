"""Tri thức nền cho lớp hỏi-đáp (`chat.py`) -- CỐ Ý là DỮ LIỆU trong repo
này, không phải thứ để model tự nhớ ra.

VÌ SAO PHẢI TÁCH LÀM HAI LOẠI, và vì sao chỉ một loại nằm ở đây:

  * KHÁI NIỆM TÀI CHÍNH CHUNG (profit factor là gì, CVaR đọc thế nào,
    Deflated Sharpe khử thiên lệch ra sao) là tri thức ổn định -- một model
    hiện đại giải thích đúng, và rubric kiểm của `narrative.py` đã ghi nhận
    điều đó ("Naming a metric by its DEFINITION is correct, not an error").
    Nhưng ở sản phẩm này chúng vẫn được viết ra đây, vì một lý do KHÁC hẳn
    độ tin cậy: mỗi định nghĩa phải khớp ĐÚNG công thức engine dùng để tính
    con số đang hiển thị. Một lời giải thích đúng-về-mặt-sách-vở nhưng lệch
    với công thức engine thì vẫn là một câu sai trong ngữ cảnh báo cáo này.
    Giai đoạn 7 (19/09) đã phải sửa 5 định nghĩa lệch đúng kiểu đó.

  * SỰ KIỆN RIÊNG CỦA OKX (cơ chế copy-trading, ý nghĩa các trường sổ lệnh,
    ranh giới dữ liệu công khai) thì KHÔNG được để model nhớ: nó thay đổi
    theo thời gian và model không có cách nào biết bản ghi nhớ của mình đã
    cũ. Mọi mục dưới đây phải là thứ đã kiểm được từ chính đường nạp dữ
    liệu của dự án (`Agent/backend/sources/`), không phải chép từ trí nhớ.

QUY TẮC BẢO TRÌ: mỗi mục là một câu tự đứng được, không số liệu của bot cụ
thể nào. Số liệu bot đi đường khác (`chat.ChatContext`), và chỉ đường đó
mới qua cổng khoá số. Nhét một con số vào đây là mở một lỗ cho phép model
nói ra con số không thuộc bot đang xem.
"""

from __future__ import annotations

from typing import Dict, Tuple

# --------------------------------------------------------------------------- #
# 1. Chỉ tiêu định lượng -- định nghĩa phải khớp công thức engine.
#
# Nguồn đối chiếu cho từng dòng:
#   * win rate / profit factor / payoff / expectancy: qc/evaluator/lenses/
#   * max drawdown, CVaR, VaR, p_ruin: mcp/analytics/simulation/monte_carlo.py
#   * DSR / PSR / MinTRL: mcp/analytics/simulation/inference.py
#   * marked (open-book) vs closed-book: mcp/analytics/performance/
# --------------------------------------------------------------------------- #

_METRIC_GLOSSARY: Tuple[Tuple[str, str], ...] = (
    (
        "Win rate",
        "the share of CLOSED trades that ended in profit. It says nothing "
        "about how large the wins were, so a high win rate next to a low "
        "payoff ratio describes many small wins and few large losses.",
    ),
    (
        "Payoff ratio",
        "average winning trade divided by average losing trade, on closed "
        "trades only.",
    ),
    (
        "Profit factor",
        "total money won divided by total money lost across closed trades. "
        "Above 1 means closed trades made money overall; it is a ratio, not "
        "a percentage.",
    ),
    (
        "Marked profit factor",
        "the same ratio recomputed as if every currently open position were "
        "closed at the mark price right now. The gap between profit factor "
        "and marked profit factor is the size of the unrealised loss the "
        "closed book is not showing.",
    ),
    (
        "Expectancy",
        "the average result per closed trade, in account currency.",
    ),
    (
        "Max drawdown",
        "the deepest fall from a peak in account value to the next low, as a "
        "percentage of that peak. It is measured on the reconstructed equity "
        "curve, not on individual trades.",
    ),
    (
        "Sharpe ratio",
        "return per unit of price swing. Negative means the account moved "
        "against itself more than it gained.",
    ),
    (
        "Sortino ratio",
        "the same idea as Sharpe but counting only downward swings, so an "
        "account that is volatile mostly upward is not penalised for it.",
    ),
    (
        "VaR 95%",
        "the loss level the simulated outcomes stayed above in 95 out of 100 "
        "runs. It is a threshold, not a worst case.",
    ),
    (
        "CVaR 95% (expected shortfall)",
        "the AVERAGE loss across the worst 5 out of 100 simulated runs. It "
        "is always at least as bad as VaR and describes the tail itself.",
    ),
    (
        "Probability of ruin",
        "the share of simulated runs in which the account lost the capital "
        "it had at risk.",
    ),
    (
        "Deflated Sharpe Ratio (DSR)",
        "the probability the observed edge is real once the search that "
        "found this bot is discounted. Picking the best of many candidates "
        "produces a good-looking record by luck alone, and DSR removes that "
        "selection effect. A DSR near zero means the record is "
        "indistinguishable from a lucky draw.",
    ),
    (
        "Probabilistic Sharpe Ratio (PSR)",
        "the probability the true Sharpe ratio is above zero, given how many "
        "trades were observed and how skewed they were.",
    ),
    (
        "Minimum Track Record Length (MinTRL)",
        "how many trades would be needed before this bot's record could "
        "support a conclusion at all. A bot below its own MinTRL has not "
        "traded enough to be judged, whatever its numbers look like.",
    ),
    (
        "Stationary bootstrap",
        "the resampling method behind the simulation (Politis & Romano). It "
        "resamples blocks of consecutive trades rather than single trades, "
        "so streaks and clustering survive the resampling.",
    ),
    (
        "Risk score",
        "a composite measure of the PROBABILITY OF LOSING CAPITAL, not a "
        "forecast of profit or loss and not a percentage. Higher means more "
        "chance of losing capital.",
    ),
    (
        "Quality score",
        "a separate composite describing how well-run the strategy looks "
        "(profitability, consistency, drawdown control, honesty, "
        "robustness). It is deliberately a second axis: a bot can be "
        "low-risk and low-quality at the same time.",
    ),
    (
        "Veto floor",
        "a hard safety rule that can raise the risk score regardless of the "
        "weighted average. When the verdict says it was decided by the veto "
        "floor, one of those rules fired.",
    ),
    (
        "Hidden risk flag",
        "a marker for a risk the surface numbers do not show, most often an "
        "unrealised loss carried on open positions while closed trades look "
        "profitable.",
    ),
    (
        "Closed book vs open book",
        "the closed book is realised, finished trades. The open book is "
        "positions still running. Simulation and most performance statistics "
        "cover the CLOSED book only, so they describe a narrower slice "
        "whenever open positions carry an unrealised loss.",
    ),
)

# --------------------------------------------------------------------------- #
# 2. Sự kiện về OKX và về chính ranh giới dữ liệu của sản phẩm này.
#
# CHỈ những điều đã kiểm được từ đường nạp dữ liệu của dự án. KHÔNG có biểu
# phí, KHÔNG có mức đòn bẩy tối đa, KHÔNG có luật thanh lý cụ thể: những thứ
# đó thay đổi theo sản phẩm và theo thời gian, và sản phẩm này không đọc
# chúng từ đâu cả -- nói ra là đoán.
# --------------------------------------------------------------------------- #

_OKX_FACTS: Tuple[str, ...] = (
    "OKX copy-trading lets a lead trader's positions be mirrored by "
    "followers. This system analyses the lead trader's own public record; "
    "it has no visibility into any individual follower's account.",
    "The public record this analysis reads is the lead trader's closed-trade "
    "list and current open positions. Entry reasoning, stop orders that "
    "never filled, and any account activity outside copy-trading are not in "
    "that record and cannot be inferred from it.",
    "A bot's displayed name on OKX is free text chosen by its operator. It "
    "is not evidence of what the strategy does, and this analysis never "
    "infers a strategy from a name.",
    "PnL shown on an exchange surface is usually the realised, closed-book "
    "figure. It can look strong while open positions carry a large "
    "unrealised loss, which is the single most common way a surface number "
    "misleads.",
    "This system is READ-ONLY. It cannot place, copy, pause, close or modify "
    "any order or position, and it has no access to the reader's account.",
    "Market data used here (candles, funding, open interest, order book "
    "depth) comes from OKX public endpoints. A symbol the bot traded that "
    "has no market data on OKX is reported as unresolved rather than "
    "silently dropped.",
)

# --------------------------------------------------------------------------- #
# 3. Ranh giới: model được nói gì và không được nói gì.
#
# Câu chữ lấy thẳng tinh thần từ `Agent/ideallm.md` muc 2 ("Allowed
# language" / "Disallowed language"). Đặt ở đây để prompt và cổng chặn từ
# (`narrative._BANNED_SUBSTRINGS`) cùng mô tả MỘT ranh giới -- cổng chặn hậu
# kiểm, đoạn này dạy trước.
# --------------------------------------------------------------------------- #

BOUNDARY_RULES: Tuple[str, ...] = (
    "Answer ONLY from the ANALYSIS RECORD and the REFERENCE KNOWLEDGE below. "
    "If the record does not contain what was asked, say so plainly and name "
    "what would be needed to answer it.",
    "Never state a number that is not in the ANALYSIS RECORD. Do not "
    "compute, convert, annualise, extrapolate or round a new figure into "
    "existence -- quote the figures as given.",
    "Never tell the reader what to do. No copying, allocating, sizing, "
    "stopping, entering or exiting. Describing what the bot did is correct; "
    "instructing the reader is not.",
    "Never promise a future outcome. A conditional statement about a "
    "scenario the record covers is fine; a prediction is not.",
    "Never upgrade the strength of a finding. If the record calls something "
    "untested, insufficient or unresolved, keep it that way.",
    "Never name a trading behaviour the record does not name. Many open "
    "positions at a loss is an observation; calling it martingale is a "
    "claim the record has to make first.",
    "State plainly when simulation figures cover closed trades only, "
    "whenever the bot is carrying an unrealised loss on open positions.",
)


def metric_glossary_block() -> str:
    """Bảng thuật ngữ, một dòng mỗi chỉ tiêu, cho vào prompt."""
    return "\n".join(f"- {name}: {meaning}" for name, meaning in _METRIC_GLOSSARY)


def okx_facts_block() -> str:
    """Các sự kiện nền về OKX và ranh giới dữ liệu."""
    return "\n".join(f"- {fact}" for fact in _OKX_FACTS)


def boundary_rules_block() -> str:
    """Luật ngôn từ, đánh số để một lượt thử lại trích dẫn được đúng luật
    đã bị vi phạm (cùng khuôn với `narrative._build_retry_prompt`)."""
    return "\n".join(
        f"{index}. {rule}" for index, rule in enumerate(BOUNDARY_RULES, start=1)
    )


def metric_names() -> Dict[str, str]:
    """Bảng tra tên -> định nghĩa, cho test và cho bất kỳ nơi nào cần kiểm
    một thuật ngữ có trong từ điển hay không."""
    return {name: meaning for name, meaning in _METRIC_GLOSSARY}
