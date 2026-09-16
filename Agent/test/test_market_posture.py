"""Step 1 has to answer three questions, and say what raised each answer."""

from __future__ import annotations

from types import SimpleNamespace

from Agent.backend.qc.reporting.market_posture import (
    POSTURE_GROWTH,
    POSTURE_RISK,
    POSTURE_STABLE,
    POSTURE_UNCLEAR,
    assess,
)


def _market(
    trend="NEUTRAL",
    volatility="NORMAL",
    vol_pct=40.0,
    depth=2_000_000.0,
    tier="ADEQUATE",
    slippage=0.01,
    flow="NEUTRAL",
    long_short=1.0,
    funding_z=0.0,
    delta_oi=0.0,
    beta=1.0,
    position=50.0,
):
    return SimpleNamespace(
        structure_state=SimpleNamespace(
            trend_state=trend,
            volatility_state=volatility,
            volatility_percentile=vol_pct,
            range_position_pct=position,
        ),
        liquidity_state=SimpleNamespace(
            total_depth_02_usd=depth,
            state_tier=tier,
            estimated_slippage_50k_pct=slippage,
        ),
        orderflow_state=SimpleNamespace(flow_bias=flow),
        derivatives_state=SimpleNamespace(
            long_short_ratio=long_short,
            funding_zscore=funding_z,
            delta_oi_pct=delta_oi,
        ),
        macro_state=SimpleNamespace(btc_beta=beta),
    )


def test_a_thin_crowded_market_is_called_risky():
    posture = assess(
        _market(trend="BEARISH", depth=50_000.0, tier="THIN", long_short=3.2)
    )

    assert posture.posture == POSTURE_RISK
    assert any("thanh khoản mỏng" in flag for flag in posture.risk_flags)
    assert any("dồn một phía" in flag for flag in posture.risk_flags)


def test_a_rising_market_with_money_coming_in_is_called_growing():
    posture = assess(_market(trend="BULLISH", flow="BUY_PRESSURE", delta_oi=3.0))

    assert posture.posture == POSTURE_GROWTH
    assert "xu hướng tăng" in posture.growth_flags


def test_a_deep_quiet_market_is_called_stable():
    posture = assess(_market(vol_pct=10.0, depth=5_000_000.0))

    assert posture.posture == POSTURE_STABLE
    assert any("sổ lệnh dày" in flag for flag in posture.stability_flags)


def test_one_severe_flag_outranks_two_soft_ones():
    """Counting flags let a mild downtrend outrank a book that cannot absorb an exit."""
    posture = assess(
        _market(
            trend="BULLISH",
            flow="BUY_PRESSURE",
            depth=40_000.0,
            tier="THIN",
            slippage=0.9,
            vol_pct=90.0,
        )
    )

    assert posture.posture == POSTURE_RISK
    assert posture.risk_score > posture.growth_score


def test_a_market_with_no_evidence_either_way_is_not_called_calm():
    bare = SimpleNamespace(
        structure_state=SimpleNamespace(
            trend_state="UNKNOWN",
            volatility_state="UNKNOWN",
            volatility_percentile=None,
            range_position_pct=None,
        ),
        liquidity_state=SimpleNamespace(
            total_depth_02_usd=None,
            state_tier="UNKNOWN",
            estimated_slippage_50k_pct=None,
        ),
        orderflow_state=SimpleNamespace(flow_bias="UNKNOWN"),
        derivatives_state=None,
        macro_state=SimpleNamespace(btc_beta=None),
    )

    assert assess(bare).posture == POSTURE_UNCLEAR


def test_a_market_that_reads_both_risky_and_calm_is_flagged_not_reassured():
    # Calm and deep (2 + 2) against a downtrend into a crowded book (1 + 1 + 2).
    posture = assess(
        _market(
            vol_pct=10.0,
            depth=5_000_000.0,
            flow="UNKNOWN",
            trend="BEARISH",
            long_short=4.0,
            position=5.0,
        )
    )

    assert posture.risk_score == posture.stability_score
    assert posture.posture == POSTURE_RISK
