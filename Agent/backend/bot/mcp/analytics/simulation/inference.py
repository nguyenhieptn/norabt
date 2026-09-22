"""Is the record real, or did it come from luck and from us picking the winner?

The bootstrap answers "what else could this edge have produced". It does not
answer whether the edge exists at all, and it cannot see that we chose this bot
after looking at dozens of others. Two published corrections do:

* Probabilistic Sharpe Ratio — Bailey & López de Prado (2012), "The Sharpe Ratio
  Efficient Frontier". Probability the true Sharpe clears a threshold once the
  sample length, skewness and fat tails of the return distribution are taken into
  account. A Sharpe of 16 on 143 fat-tailed trades is not the same evidence as a
  Sharpe of 2 on 500 clean ones.
* Deflated Sharpe Ratio — Bailey & López de Prado (2014). Raises the threshold to
  the Sharpe one would expect from the best of N candidates by chance alone. This
  applies directly here: each asset's bot was chosen as the best performer out of
  its candidate pool, which is exactly the selection bias the DSR corrects.

Minimum Track Record Length answers the practical question the other two raise:
how many trades this bot still needs before its Sharpe would mean anything.

Skewness is the third standardised moment; kurtosis here is RAW (3 for a normal
distribution), which is what these formulas take -- with normal returns the
variance term collapses to 1 + SR^2/2, the textbook asymptotic variance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

EULER_MASCHERONI = 0.5772156649015329
MIN_OBSERVATIONS = 10

# These formulas are asymptotic in n and use the sample third and fourth moments.
# A kurtosis this large relative to the sample means a handful of fills are
# producing the moment, and the approximation stops being trustworthy -- without
# this guard a 121-trade ledger with one outlier reports PSR 1.000.
KURTOSIS_PER_SAMPLE_LIMIT = 10.0
# Below this the skew/kurtosis terms, not the data, are driving the confidence.
MIN_VARIANCE_TERM = 0.25


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _normal_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


@dataclass(frozen=True)
class SharpeInference:
    sharpe_per_trade: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    sample_size: int = 0
    psr: Optional[float] = None
    # Mốc so sánh SR* mà PSR/MinTRL được đo tương đối với nó. Phơi ra ngoài vì
    # "PSR = 0,97" tự nó vô nghĩa nếu người đọc không biết nó đang vượt mốc
    # nào: với SR* = 0 thì PSR chỉ nói "gần như chắc chắn Sharpe thật > 0",
    # một mốc mà hầu hết bot có lãi đều vượt.
    psr_benchmark_sharpe: float = 0.0
    min_track_record_trades: Optional[float] = None
    deflated_sharpe: Optional[float] = None
    reliable: bool = True
    selection_trials: Optional[int] = None
    expected_max_sharpe: Optional[float] = None
    notes: tuple = ()


def _moments(returns: np.ndarray) -> tuple:
    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))
    if std <= 1e-15:
        return mean, std, None, None
    centred = (returns - mean) / std
    skew = float(np.mean(centred**3))
    kurt = float(np.mean(centred**4))
    return mean, std, skew, kurt


def _sharpe_variance_term(sharpe: float, skew: float, kurt: float) -> Optional[float]:
    """1 - g3*SR + (g4-1)/4 * SR^2 -- the variance factor both formulas share."""
    term = 1.0 - skew * sharpe + (kurt - 1.0) / 4.0 * sharpe**2
    return term if term > 1e-12 else None


def analyse(
    returns: Sequence[float],
    benchmark_sharpe: float = 0.0,
    selection_trials: Optional[int] = None,
    confidence: float = 0.95,
    trial_sharpe_variance: Optional[float] = None,
) -> SharpeInference:
    """PSR, MinTRL and (when the selection size is known) the deflated Sharpe."""
    values = np.asarray([float(r) for r in returns], dtype=np.float64)
    if len(values) < MIN_OBSERVATIONS:
        return SharpeInference(
            sample_size=len(values),
            notes=(f"At least {MIN_OBSERVATIONS} trades are needed for statistical inference",),
        )

    mean, std, skew, kurt = _moments(values)
    if skew is None or kurt is None or std <= 1e-15:
        return SharpeInference(
            sample_size=len(values),
            notes=("Returns have no variance, so the Sharpe ratio cannot be computed",),
        )

    n = len(values)
    sharpe = mean / std  # per trade, which is the unit PSR is defined on
    variance_term = _sharpe_variance_term(sharpe, skew, kurt)
    notes: list = []
    if variance_term is None:
        return SharpeInference(
            sharpe_per_trade=sharpe,
            skewness=skew,
            kurtosis=kurt,
            sample_size=n,
            notes=("The Sharpe variance term is undefined for this skew/kurtosis",),
        )

    psr = _normal_cdf(
        (sharpe - benchmark_sharpe) * math.sqrt(n - 1) / math.sqrt(variance_term)
    )

    reliable = True
    if kurt > n / KURTOSIS_PER_SAMPLE_LIMIT:
        reliable = False
        notes.append(
            f"Kurtosis {kurt:.0f} is too large relative to {n} trades: a handful of "
            "individual trades are driving the fourth moment, the asymptotic "
            "approximation is not reliable"
        )
    if variance_term < MIN_VARIANCE_TERM:
        reliable = False
        notes.append(
            f"The Sharpe variance term is only {variance_term:.3f}: this confidence "
            "comes from the skew/kurtosis, not from the data"
        )

    min_trl = None
    if abs(sharpe - benchmark_sharpe) > 1e-12:
        z = _normal_ppf(confidence)
        min_trl = 1.0 + variance_term * (z / (sharpe - benchmark_sharpe)) ** 2
        if sharpe <= benchmark_sharpe:
            # A negative edge never reaches significance above the benchmark.
            min_trl = None
            notes.append("Sharpe is below the benchmark, so there is no track record length that reaches significance")

    deflated = expected_max = None
    if selection_trials and selection_trials > 1:
        # Ngưỡng mà kẻ tốt nhất trong N ứng viên vượt được CHỈ nhờ may mắn.
        #
        # Công thức công bố (Bailey & López de Prado, 2014):
        #     SR*₀ = √(V[{SR̂ₙ}]) · [(1−γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e))]
        # trong đó V[{SR̂ₙ}] là phương sai CHÉO của Sharpe giữa N ứng viên, ước
        # lượng thực nghiệm từ chính N lần thử đó.
        #
        # Ở đây ta KHÔNG có V chéo đó: pool ứng viên (`selection_trials`) đến
        # từ bước tuyển bot, mà ta chỉ chấm điểm những bot ĐƯỢC CHỌN — Sharpe
        # của các ứng viên bị loại không tồn tại ở đâu cả. Muốn có V chéo thật
        # thì phải chấm toàn bộ pool, đắt hơn nhiều bậc.
        #
        # Thay vào đó dùng V theo GIẢ THUYẾT KHÔNG: `variance_term/(n−1)` là
        # phương sai ước lượng của một Sharpe trên n quan sát. Dưới đúng giả
        # thuyết mà DSR đặt ra -- không ứng viên nào có lợi thế thật, cùng cỡ
        # mẫu -- hai đại lượng này TRÙNG NHAU, nên đây là bản "null" của cùng
        # công thức chứ không phải một xấp xỉ tuỳ tiện.
        #
        # CHIỀU SAI LỆCH, phải biết để đọc cho đúng: khi các ứng viên thật sự
        # chênh nhau về kỹ năng hoặc về độ dài sổ lệnh, V chéo thật LỚN HƠN V
        # theo giả thuyết không. Khi đó ngưỡng `expected_max` ở đây bị ước
        # lượng THẤP, và DSR trả về CAO HƠN mức đáng có. Nói cách khác: DSR ở
        # đây là cận TRÊN lạc quan, sai về phía dễ dãi với bot chứ không phải
        # về phía khắt khe. Đọc nó như "kể cả tính rộng rãi thế này mà vẫn
        # thấp thì đúng là yếu", chứ đừng đọc ngược lại.
        trials = float(selection_trials)
        max_z = (1.0 - EULER_MASCHERONI) * _normal_ppf(
            1.0 - 1.0 / trials
        ) + EULER_MASCHERONI * _normal_ppf(1.0 - 1.0 / (trials * math.e))
        # Ưu tiên phương sai CHÉO thật đo được trên quần thể bot đã chấm
        # (`trial_sharpe_variance`) -- đó đúng là V[{SR̂ₙ}] mà công thức công
        # bố đòi. Chỉ khi không có mới rơi về bản "null" nói ở trên.
        #
        # Khoảng cách giữa hai lựa chọn này KHÔNG nhỏ. Đo trên 30 bot thật của
        # dự án: phương sai chéo = 0.0877 (độ lệch chuẩn Sharpe/lệnh 0.296),
        # trong khi bản null cho một bot 300 lệnh chỉ ra ~0.0033 -- thấp hơn
        # 26 lần. Ngưỡng `expected_max` vì thế nhảy từ ~0.13 lên ~0.67, tức
        # bản null đang dễ hơn công thức thật khoảng 5 lần. Dùng bản null làm
        # mặc định là tự nới chuẩn cho chính mình.
        if trial_sharpe_variance is not None and trial_sharpe_variance > 0.0:
            sharpe_variance = float(trial_sharpe_variance)
            variance_source = "the population"
        else:
            sharpe_variance = variance_term / (n - 1)
            variance_source = "the null hypothesis"
            notes.append(
                "The deflated Sharpe threshold is computed from the null-hypothesis "
                "variance (no Sharpe distribution across the candidate population yet): "
                "the threshold is underestimated, so the DSR here is an optimistic upper bound"
            )
        expected_max = math.sqrt(sharpe_variance) * max_z
        notes.append(
            f"Lucky-selection threshold for {selection_trials} candidates: "
            f"Sharpe/trade {expected_max:.3f} (Sharpe variance taken from "
            f"{variance_source})"
        )
        deflated = _normal_cdf(
            (sharpe - expected_max) * math.sqrt(n - 1) / math.sqrt(variance_term)
        )

    return SharpeInference(
        sharpe_per_trade=sharpe,
        skewness=skew,
        kurtosis=kurt,
        sample_size=n,
        psr=psr,
        psr_benchmark_sharpe=benchmark_sharpe,
        min_track_record_trades=min_trl,
        deflated_sharpe=deflated,
        selection_trials=selection_trials,
        expected_max_sharpe=expected_max,
        reliable=reliable,
        notes=tuple(notes),
    )
