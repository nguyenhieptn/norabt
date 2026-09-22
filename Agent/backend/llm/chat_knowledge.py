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
# Nguồn đối chiếu cho từng dòng (đã đọc thẳng mã nguồn khi viết, không suy
# đoán -- xem lại nguồn này mỗi khi một công thức engine đổi):
#   * win rate / profit factor / payoff / expectancy:
#       backend/report/qc/evaluator/lenses/
#   * max drawdown, VaR, CVaR, p_ruin, MAR ratio, loss-streak baseline/excess,
#     horizon sensitivity, terminal equity distribution, deferred-loss bias:
#       backend/bot/mcp/analytics/simulation/monte_carlo.py
#   * DSR / PSR / MinTRL / kurtosis convention:
#       backend/bot/mcp/analytics/simulation/inference.py
#   * marked (open-book) vs closed-book: backend/bot/mcp/analytics/performance/
#   * deferred-loss confidence penalty: backend/report/qc/evaluator/lenses/tail_risk.py
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
        "PnL skewness",
        "the third standardised moment of the closed-trade PnL distribution. "
        "Negative means the distribution has a longer, fatter LEFT tail: most "
        "trades cluster as small results while the rare bad trade is much "
        "larger than the rare good one. A strategy can show a high win rate "
        "and negative skew at the same time -- that combination describes "
        "many small wins funding a few large losses, not a contradiction.",
    ),
    (
        "PnL kurtosis",
        "the fourth standardised moment of the closed-trade PnL distribution, "
        "reported here as RAW kurtosis, where 3.0 is the value a normal "
        "(bell-curve) distribution produces -- NOT the more common 'excess "
        "kurtosis' convention where 0.0 is normal. Compare this figure "
        "against 3.0, not against 0.0. A value well above 3.0 means extreme "
        "results (in either direction) happen far more often than a bell "
        "curve predicts -- exactly the situation that makes Sharpe-based "
        "confidence claims (PSR, DSR) unreliable without the correction "
        "those two figures already apply.",
    ),
    (
        "VaR 95% / VaR 99%",
        "the loss level the simulated outcomes stayed above in 95 (or 99) out "
        "of 100 runs, reported as a LOSS (a positive number means money "
        "lost). It is a threshold the tail starts at, not the tail itself and "
        "not a worst case -- CVaR describes what happens beyond this line.",
    ),
    (
        "CVaR 95% / CVaR 99% (expected shortfall)",
        "the AVERAGE loss across the worst 5% (or worst 1%) of simulated "
        "runs, reported as a loss. It is always at least as large as VaR at "
        "the same confidence level; a CVaR far larger than its matching VaR "
        "means the tail beyond the threshold is unusually severe, not just "
        "unusually frequent.",
    ),
    (
        "Probability of ruin",
        "the share of simulated runs in which the account lost the capital "
        "it had at risk.",
    ),
    (
        "MAR ratio (simulated)",
        "one simulated run's profit percentage divided by that SAME run's "
        "own max drawdown percentage -- return priced against the worst pain "
        "that specific run actually produced, which is what a capital "
        "allocator sizing a position actually cares about, rather than "
        "return priced against average volatility (Sharpe/Sortino). Reported "
        "as a median and a p05 (worst-case-band) across all simulated runs. "
        "Two bots with an identical Sharpe ratio can have very different MAR "
        "ratios if one of them concentrates its variance into rare, deep "
        "drawdowns instead of spreading it evenly.",
    ),
    (
        "Loss-streak probability, baseline, and excess",
        "the simulated probability of a losing streak of a given length (5 "
        "or 10 trades in a row) is compared against an exact mathematical "
        "BASELINE: the probability that same streak would occur ANYWAY, "
        "purely from having this many independent trades at this bot's own "
        "win rate -- a bot that has simply traded a lot is near-certain to "
        "show a long losing streak somewhere even if every trade were an "
        "independent coin flip. EXCESS is the simulated figure minus that "
        "baseline: what is left over after sample size alone is accounted "
        "for, and the only part of the number that can indicate genuine "
        "streak-dependence (losses clustering together more than chance "
        "would produce) rather than an artifact of having a long ledger.",
    ),
    (
        "Horizon sensitivity / horizon stability label",
        "how much the simulated probability of profit changes between a "
        "SHORT and a LONG simulated horizon, run independently at each "
        "length. STABLE ACROSS HORIZONS means the picture does not depend on "
        "how long the strategy is held or watched. HOLDS ONLY AT SHORT "
        "HORIZON describes a strategy that looks fine briefly and unsafe if "
        "extended; NEEDS MORE TIME describes the reverse -- unsafe-looking "
        "briefly, healthier over a longer run. Neither label is a defect in "
        "the number: it is a property of the strategy's own time dependence.",
    ),
    (
        "Terminal equity distribution",
        "the full spread of simulated ending account values -- expected "
        "(mean), median, a p10 (worse-case band) and a p90 (better-case "
        "band), plus the single worst simulated outcome. A median or "
        "expected figure quoted alone hides how wide this spread is; the "
        "gap between p10 and p90 is itself the size of the uncertainty.",
    ),
    (
        "Probability of exceeding the current drawdown",
        "the share of simulated runs whose max drawdown goes deeper than the "
        "drawdown this account is ALREADY carrying right now. A high figure "
        "here means the account's present position is not near the "
        "simulated worst case -- it means further deterioration of a similar "
        "or larger size is a common outcome in the simulation, not a tail "
        "event.",
    ),
    (
        "Probability drawdown recovery exceeds 30 days",
        "the share of simulated runs whose longest underwater period (peak "
        "to full recovery) is longer than 30 calendar days, converted from "
        "trade count using this bot's own observed trading frequency. Two "
        "bots with the same max drawdown can have very different recovery "
        "profiles depending on how often each one trades.",
    ),
    (
        "Deferred-loss bias flag",
        "set when the simulation is built from CLOSED trades only while the "
        "bot is holding an unrealised loss on open positions right now. Every "
        "probability the simulation reports is then drawn from a history "
        "that excludes that loss, so EVERY figure in the simulation section "
        "is more optimistic than the account's real current position -- this "
        "is not a caveat on one number, it recolours the whole simulation.",
    ),
    (
        "Deflated Sharpe Ratio (DSR)",
        "Bailey & Lopez de Prado (2014). The probability the observed edge is "
        "real once the search that found this bot is discounted: it raises "
        "the bar to the Sharpe ratio expected from the BEST of "
        "`selection_trials` candidates by chance alone, because this bot was "
        "chosen as the top performer out of that many candidates on the same "
        "asset -- exactly the selection effect DSR is built to remove. A DSR "
        "near zero means the record is statistically indistinguishable from "
        "having picked the luckiest of many random performers, whatever the "
        "raw Sharpe ratio looks like on its own.",
    ),
    (
        "Probabilistic Sharpe Ratio (PSR)",
        "Bailey & Lopez de Prado (2012), 'The Sharpe Ratio Efficient "
        "Frontier'. The probability the TRUE Sharpe ratio clears a benchmark "
        "(zero, by default) once sample size, skewness and kurtosis are "
        "accounted for -- a Sharpe ratio computed from few, fat-tailed trades "
        "is weaker evidence than the same Sharpe ratio computed from many, "
        "well-behaved ones, and PSR is what converts that difference into a "
        "single probability. PSR answers a WEAKER question than DSR: PSR "
        "ignores how many other candidates were tried before this bot was "
        "picked, DSR does not.",
    ),
    (
        "Minimum Track Record Length (MinTRL)",
        "how many trades would be needed, at this bot's own observed Sharpe "
        "ratio, skew and kurtosis, before its record could clear the "
        "benchmark with the stated confidence. A bot below its own MinTRL "
        "has not traded enough to be judged yet, whatever its numbers look "
        "like today; it is a statement about the SAMPLE, not the strategy.",
    ),
    (
        "Stationary bootstrap",
        "the resampling method behind the simulation -- Politis & Romano "
        "(1994), 'The Stationary Bootstrap'. Rather than a fixed block "
        "length (which would bake an arbitrary guess into the answer), each "
        "resampled block ends with a fixed probability, so block lengths "
        "follow a geometric distribution with a mean length near the cube "
        "root of the trade count. This resamples BLOCKS of consecutive "
        "trades rather than single trades, so streaks and clustering that "
        "exist in the real ledger survive into the simulated ones -- a plain "
        "trade-by-trade (i.i.d.) bootstrap would understate tail risk by "
        "erasing exactly that clustering.",
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
# 1b. Mẫu suy luận định lượng -- KHÁC hẳn mục 1 (định nghĩa một chỉ tiêu):
# đây là mối quan hệ THỐNG KÊ đã được công nhận giữa NHIỀU chỉ tiêu, cho phép
# model tạo ra một câu trả lời có chiều sâu thật thay vì đọc từng số rời rạc.
#
# VÌ SAO AN TOÀN để đưa vào, dù rubric của `narrative.py` cấm "quy kết một
# HÀNH VI mà nguồn không nói tới": mỗi mục dưới đây là một QUAN HỆ GIỮA CÁC
# CHỈ TIÊU (nếu số A và số B cùng thoả điều kiện thì đó là dấu hiệu của điều
# gì), không phải một CÁO BUỘC về bot đang xem. Bản thân câu chữ luôn nhắc lại
# điều kiện ("chỉ nêu khi bản ghi thực sự có cả hai số"), nên nó dạy CÁCH ĐỌC
# số liệu, không cấy sẵn một kết luận. `chat.BOUNDARY_RULES`'s luật 6 ("never
# name a behaviour the record does not name") vẫn áp dụng nguyên vẹn phía sau
# -- mục này không nới nó.
# --------------------------------------------------------------------------- #

_REASONING_PATTERNS: Tuple[str, ...] = (
    "A high win rate together with a low payoff ratio and negative PnL skew "
    "describes an asymmetric payoff shape: many small wins funding a few "
    "large losses. This is the numerical signature shared by strategies that "
    "avoid closing losers or that sell volatility/insurance. State this "
    "pattern only when the record's own win rate, payoff ratio AND skew all "
    "point the same way together -- any one of the three alone does not "
    "establish it.",
    "The gap between profit factor and marked profit factor is not itself a "
    "behaviour -- it is, by construction, the exact size of the unrealised "
    "loss the closed book excludes. When the record's own numbers show both "
    "a widening gap and a true deferred-loss-bias flag, they describe the "
    "SAME underlying fact from two different angles: the closed-book "
    "statistics currently understate the account's real position.",
    "When the record's own Probabilistic Sharpe Ratio sits near 1.0 while "
    "its Deflated Sharpe Ratio sits near 0.0, that is not a contradiction: "
    "PSR asks whether this bot's own Sharpe ratio is real given its own "
    "sample; DSR asks the strictly harder question of whether it still "
    "looks real once the fact that it was chosen as the best of many "
    "candidates is priced in. A bot can pass the first question and fail "
    "the second.",
    "When the record's own loss-streak excess is small (roughly single "
    "digits, in percentage points), that is consistent with sample size "
    "alone explaining the observed streaks. A large excess is a separate "
    "signal from a low win rate: a low win rate explains frequent losses "
    "without requiring them to cluster, while a large excess means the "
    "losses are clustering together more than that same win rate would "
    "predict on its own.",
    "When the record shows the same max drawdown figure alongside a "
    "distinct MAR ratio and a distinct probability of recovery exceeding 30 "
    "days, treat all three as necessary together: max drawdown describes "
    "the worst single fall, MAR ratio describes how return compares to "
    "that fall, and the recovery probability describes how long the "
    "account stayed underwater. None of the three substitutes for the "
    "others.",
    "When the record's own horizon_stability_label is anything other than "
    "STABLE ACROSS HORIZONS, that means the strategy's apparent safety "
    "depends on how long a position is held or watched, not that a number "
    "is wrong -- HOLDS ONLY AT SHORT HORIZON and NEEDS MORE TIME describe "
    "opposite time-dependencies, and neither is more 'correct' than the "
    "other in isolation.",
    "Kurtosis meaningfully above 3.0 in this engine's convention, alongside "
    "a Sharpe ratio that looks acceptable on its own, is a case where the "
    "Sharpe ratio is the LESS trustworthy of the two figures: the fat tails "
    "kurtosis is reporting are exactly what the PSR/DSR corrections exist "
    "to discount, so those two figures -- not the raw Sharpe -- are the ones "
    "to lean on when the record shows this combination.",
)


def reasoning_patterns_block() -> str:
    """Mẫu suy luận, đánh số để model trích dẫn được đúng mẫu nó đang dùng."""
    return "\n".join(
        f"{index}. {pattern}" for index, pattern in enumerate(_REASONING_PATTERNS, start=1)
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
