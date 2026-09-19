"""A Sharpe ratio is a claim; these tests check the claim is tested properly."""

from __future__ import annotations

import json
import math
import statistics

import numpy as np
import pytest

from Agent.backend.mcp.analytics.simulation.inference import (
    MIN_OBSERVATIONS,
    _normal_cdf,
    _normal_ppf,
    analyse,
)


def test_the_normal_quantile_and_cdf_match_published_values():
    assert _normal_ppf(0.975) == pytest.approx(1.959964, abs=1e-5)
    assert _normal_ppf(0.95) == pytest.approx(1.644854, abs=1e-5)
    assert _normal_cdf(1.959964) == pytest.approx(0.975, abs=1e-5)
    assert _normal_cdf(0.0) == pytest.approx(0.5, abs=1e-12)


def test_the_variance_term_collapses_to_the_textbook_value_on_normal_returns():
    """With skew 0 and kurtosis 3 the formula must reduce to 1 + SR^2/2."""
    rng = np.random.default_rng(11)
    returns = rng.normal(0.01, 0.04, 20_000)

    result = analyse(returns)
    sharpe = result.sharpe_per_trade
    observed = 1 - result.skewness * sharpe + (result.kurtosis - 1) / 4 * sharpe**2

    assert result.kurtosis == pytest.approx(3.0, abs=0.1)
    assert observed == pytest.approx(1 + sharpe**2 / 2, rel=0.02)


def test_a_losing_record_gets_a_low_probabilistic_sharpe():
    rng = np.random.default_rng(3)
    losing = rng.normal(-0.004, 0.03, 400)

    result = analyse(losing)

    assert result.psr < 0.1
    assert result.min_track_record_trades is None


def test_a_longer_record_needs_less_faith_than_a_short_one():
    """Same edge, more trades: the probability the Sharpe is real must rise."""
    rng = np.random.default_rng(5)
    short = analyse(rng.normal(0.003, 0.03, 40))
    long = analyse(rng.normal(0.003, 0.03, 4_000))

    assert long.psr > short.psr


def test_picking_the_best_of_many_candidates_deflates_the_sharpe():
    """The bot was chosen as the best of its pool; DSR must price that in."""
    rng = np.random.default_rng(9)
    returns = rng.normal(0.004, 0.03, 300)

    alone = analyse(returns)
    picked = analyse(returns, selection_trials=60)

    assert picked.deflated_sharpe is not None
    assert picked.deflated_sharpe < alone.psr
    assert picked.expected_max_sharpe > 0


def test_more_candidates_means_a_harder_threshold():
    rng = np.random.default_rng(13)
    returns = rng.normal(0.004, 0.03, 300)

    few = analyse(returns, selection_trials=5)
    many = analyse(returns, selection_trials=200)

    assert many.expected_max_sharpe > few.expected_max_sharpe
    assert many.deflated_sharpe < few.deflated_sharpe


def test_minimum_track_record_length_is_consistent_with_the_psr():
    """MinTRL is the n at which PSR would reach the confidence level."""
    rng = np.random.default_rng(17)
    returns = rng.normal(0.002, 0.03, 500)

    result = analyse(returns, confidence=0.95)
    variance_term = (
        1
        - result.skewness * result.sharpe_per_trade
        + (result.kurtosis - 1) / 4 * result.sharpe_per_trade**2
    )
    expected = 1 + variance_term * (1.644854 / result.sharpe_per_trade) ** 2

    assert result.min_track_record_trades == pytest.approx(expected, rel=1e-3)


def test_a_moment_driven_by_one_outlier_is_marked_unreliable():
    """One 50 % fill in a 120-trade ledger must not produce confident stats."""
    rng = np.random.default_rng(23)
    returns = np.concatenate([rng.normal(0.002, 0.01, 120), [0.5]])

    result = analyse(returns)

    assert result.reliable is False
    assert any("Kurtosis" in note for note in result.notes)


def test_a_clean_sample_is_not_marked_unreliable():
    rng = np.random.default_rng(29)

    assert analyse(rng.normal(0.004, 0.03, 1_000)).reliable is True


def test_too_few_trades_yields_no_inference_rather_than_a_guess():
    result = analyse([0.01] * (MIN_OBSERVATIONS - 1))

    assert result.psr is None
    assert result.sharpe_per_trade is None
    assert result.notes


def test_a_flat_return_series_is_refused_instead_of_dividing_by_zero():
    result = analyse([0.0] * 50)

    assert result.psr is None
    assert not math.isnan(result.sample_size)


def test_psr_matches_the_published_closed_form_digit_for_digit() -> None:
    """Khoá PSR vào ĐÚNG công thức Bailey & López de Prado (2012).

        PSR(SR*) = Φ[ (SR̂ − SR*)·√(n−1) / √(1 − γ₃·SR̂ + ((γ₄−1)/4)·SR̂²) ]

    Tính lại vế phải ở đây bằng tay từ chính các mô men mà hàm trả về, rồi so
    với giá trị hàm tính. Nếu ai đó đổi mẫu số (ví dụ dùng kurtosis THỪA thay
    vì kurtosis THÔ, hay bỏ mất số hạng skew, hay dùng √n thay vì √(n−1)) thì
    bài này gãy ngay -- đó chính là việc của nó.
    """
    rng = np.random.default_rng(12345)
    returns = rng.normal(0.004, 0.02, 400).tolist()
    result = analyse(returns)

    sr = result.sharpe_per_trade
    g3, g4, n = result.skewness, result.kurtosis, result.sample_size
    assert sr is not None and g3 is not None and g4 is not None

    variance_term = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr**2
    expected = 0.5 * (
        1.0
        + math.erf(
            ((sr - result.psr_benchmark_sharpe) * math.sqrt(n - 1))
            / math.sqrt(variance_term)
            / math.sqrt(2.0)
        )
    )
    assert result.psr == pytest.approx(expected, rel=1e-12)


def test_kurtosis_is_raw_not_excess() -> None:
    """Công thức PSR nhận kurtosis THÔ (bằng 3 với phân phối chuẩn).

    Nhầm sang kurtosis THỪA (bằng 0 với phân phối chuẩn) là lỗi kinh điển và
    im lặng: mẫu số thành 1 − γ₃·SR − SR²/4 thay vì 1 + SR²/2, tức tự tin hơn
    thực tế. Với mẫu chuẩn đủ lớn, kurtosis phải quanh 3 chứ không quanh 0.
    """
    rng = np.random.default_rng(777)
    result = analyse(rng.normal(0.003, 0.015, 2000).tolist())
    assert result.kurtosis == pytest.approx(3.0, abs=0.35)
    assert result.skewness == pytest.approx(0.0, abs=0.2)


def test_min_track_record_length_matches_the_published_closed_form() -> None:
    """MinTRL = 1 + V·(Z_α/(SR̂ − SR*))², đúng nguyên văn công thức."""
    rng = np.random.default_rng(2468)
    result = analyse(rng.normal(0.005, 0.02, 300).tolist(), confidence=0.95)
    sr, g3, g4 = result.sharpe_per_trade, result.skewness, result.kurtosis
    variance_term = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr**2
    z = _normal_ppf(0.95)
    expected = 1.0 + variance_term * (z / (sr - result.psr_benchmark_sharpe)) ** 2
    assert result.min_track_record_trades == pytest.approx(expected, rel=1e-12)


def test_the_psr_benchmark_is_reported_so_the_number_can_be_read() -> None:
    """ "PSR = 0,97" vô nghĩa nếu không biết nó vượt mốc nào.

    Mặc định SR* = 0, tức PSR chỉ nói "gần như chắc Sharpe thật > 0" -- mốc mà
    hầu hết bot có lãi đều vượt. Mốc đó phải đi kèm con số ra tới ngoài, và
    phải đổi theo khi caller truyền mốc khác.
    """
    returns = np.random.default_rng(99).normal(0.004, 0.02, 250).tolist()
    assert analyse(returns).psr_benchmark_sharpe == 0.0

    strict = analyse(returns, benchmark_sharpe=0.15)
    assert strict.psr_benchmark_sharpe == 0.15
    # Mốc cao hơn thì xác suất vượt mốc phải THẤP hơn -- nếu không, dấu trong
    # tử số đã bị đảo.
    assert strict.psr < analyse(returns).psr


def test_deflated_sharpe_uses_the_population_variance_when_given() -> None:
    """DSR phải dùng phương sai CHÉO của quần thể, đúng công thức công bố.

        SR*₀ = √(V[{SR̂ₙ}]) · [(1−γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e))]

    Đo trên 30 bot thật của dự án: V chéo = 0.0877, trong khi xấp xỉ theo giả
    thuyết không cho một bot 300 lệnh chỉ ~0.0033. Ngưỡng vì thế phải là ~0.67
    chứ không phải ~0.13 — chênh 5 lần, và chênh về phía DỄ nếu dùng xấp xỉ.
    """
    rng = np.random.default_rng(31337)
    returns = rng.normal(0.006, 0.02, 300).tolist()
    trials = 49
    population_variance = 0.087731

    strict = analyse(
        returns, selection_trials=trials, trial_sharpe_variance=population_variance
    )
    lenient = analyse(returns, selection_trials=trials)

    gamma = 0.5772156649015329
    max_z = (1.0 - gamma) * _normal_ppf(1.0 - 1.0 / trials) + gamma * _normal_ppf(
        1.0 - 1.0 / (trials * math.e)
    )
    assert strict.expected_max_sharpe == pytest.approx(
        math.sqrt(population_variance) * max_z, rel=1e-12
    )
    # Ngưỡng thật cao hơn hẳn ngưỡng xấp xỉ -> DSR thật phải THẤP hơn.
    assert strict.expected_max_sharpe > lenient.expected_max_sharpe
    assert strict.deflated_sharpe < lenient.deflated_sharpe


def test_falling_back_to_the_null_variance_says_so_out_loud() -> None:
    """Không có quần thể thì vẫn tính được, nhưng phải tự khai là cận trên."""
    returns = np.random.default_rng(5).normal(0.005, 0.02, 200).tolist()
    result = analyse(returns, selection_trials=30)
    assert result.deflated_sharpe is not None
    assert any("optimistic upper bound" in note for note in result.notes)


def test_population_variance_is_read_from_the_scored_bots(tmp_path) -> None:
    """Nguồn V chéo là chính những bot đã chấm, đọc từ đĩa."""
    from Agent.backend.mcp.analytics.simulation import sharpe_reference

    sharpe_reference.reset_cache()
    analysis = tmp_path / "analysis" / "cex" / "BTC" / "bot"
    values = [0.1, 0.2, -0.05, 0.4, 0.15, 0.0, 0.3, -0.2, 0.25, 0.05, 0.6, -0.1]
    for index, value in enumerate(values):
        folder = analysis / f"bot_{index}"
        folder.mkdir(parents=True)
        (folder / "monte_carlo.json").write_text(
            json.dumps({"sharpe_per_trade": value}), encoding="utf-8"
        )
    measured = sharpe_reference.population_sharpe_variance(tmp_path)
    assert measured == pytest.approx(statistics.variance(values), rel=1e-12)

    # Dưới ngưỡng mẫu tối thiểu thì thà không có còn hơn dựng ngưỡng bịa.
    sharpe_reference.reset_cache()
    thin = tmp_path / "thin"
    (thin / "analysis").mkdir(parents=True)
    assert sharpe_reference.population_sharpe_variance(thin) is None
