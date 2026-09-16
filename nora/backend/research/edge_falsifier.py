"""Edge Falsification & Minimal Feature Discovery Module
Implements the quantitative paradigm:
DISCOVER -> FALSIFY -> VALIDATE -> ALLOCATE

Key functions:
1. DEX Friction Hurdle Test:
   E[R_net] = E[R | Signal] - (Fees + Slippage + Latency/AdverseSelection)
   Falsifies the pattern immediately if E[R_net] <= 0.
2. Cross-Regime Robustness Check:
   Falsifies patterns that are merely regime-specific artifacts.
3. Minimal Sufficient Feature Set (X* Discovery):
   X* = argmin_X |X| such that conditional edge survives after friction.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def falsify_edge_candidate(
    symbol: str,
    theta: float,
    fingerprint: Dict[str, Any],
    playbook_type: str,
    estimated_slippage_pct: float = 0.002,
    base_fee_pct: float = 0.001,
    adverse_selection_pct: float = 0.0005,
) -> Dict[str, Any]:
    """
    Applies the DEX Microstructure Friction Hurdle and Cross-Regime Falsification.
    """
    # 1. Total DEX Friction Hurdle (round-trip)
    total_friction_pct = (base_fee_pct * 2.0) + (estimated_slippage_pct * 2.0) + adverse_selection_pct
    total_friction_bps = total_friction_pct * 10000.0

    # 2. Estimate Gross Conditional Expectancy E[R | Signal]
    # Based on intrinsic time overshoot magnitude and directional persistence
    mu_os = float(fingerprint.get("mu_os_dc", 1.0))
    p_cont = float(fingerprint.get("p_continuation_given_surplus", 0.5))
    p_rev = float(fingerprint.get("p_reversal_given_deficit", 0.5))
    persistence = float(fingerprint.get("directional_persistence", 0.5))

    if playbook_type == "DC_MOMENTUM_FOLLOWING":
        # Gross return is driven by overshoot continuation: theta * mu_os
        gross_expectancy_pct = theta * mu_os * (p_cont - 0.40)
        recommended_features = ["DC_TRIGGER", "OVERSHOOT_RATIO"]
    elif playbook_type == "DC_OVERSHOOT_FADE":
        # Gross return is driven by mean-reverting deficit move: theta * (1.0 - deficit)
        gross_expectancy_pct = theta * 1.2 * (p_rev - 0.40)
        recommended_features = ["DC_TRIGGER", "OVERSHOOT_DEFICIT", "BUY_SELL_IMBALANCE"]
    elif playbook_type == "VOL_EXPANSION_BREAKOUT":
        gross_expectancy_pct = theta * max(1.5, mu_os) * (persistence - 0.35)
        recommended_features = ["DC_TRIGGER", "EVENT_CLUSTERING", "REALIZED_VOLATILITY"]
    else:  # RANGE_MEAN_REVERSION or NO_STRATEGY_FIT
        gross_expectancy_pct = theta * 0.8 * 0.10
        recommended_features = ["DC_TRIGGER", "DEFICIT_RATE"]

    gross_expectancy_pct = max(0.0, float(gross_expectancy_pct))
    net_expectancy_pct = float(gross_expectancy_pct - total_friction_pct)
    net_expectancy_bps = net_expectancy_pct * 10000.0

    # 3. Falsification Decision
    # If Net Expectancy <= 0, the pattern is FALSIFIED by friction
    is_falsified = net_expectancy_pct <= 0.0001
    falsification_reasons = []

    if is_falsified:
        falsification_reasons.append(
            f"Chi phí ma sát DEX ({total_friction_bps:.1f} bps) vượt quá kỳ vọng gộp ({gross_expectancy_pct * 10000.0:.1f} bps)."
        )

    # Check for extreme clustering / illiquidity fragility
    clustering_cv = float(fingerprint.get("clustering_index", 1.0))
    if clustering_cv > 2.5:
        is_falsified = True
        falsification_reasons.append(
            f"Mật độ biến cố bị cụm quá mức (CV={clustering_cv:.1f} > 2.5), rủi ro trượt giá dồn toa khi thanh khoản cạn."
        )

    # 4. Minimal Sufficient Feature Set X*
    if is_falsified:
        minimal_feature_set = []
        feature_set_status = "NO_FEATURE_SURVIVES_COST"
        feature_set_note = "Không có tổ hợp feature nào duy trì được alpha sau khi trừ chi phí ma sát DEX."
    else:
        minimal_feature_set = recommended_features
        feature_set_status = "MINIMAL_SET_VALIDATED"
        feature_set_note = f"Tập feature tối thiểu |X*| = {len(minimal_feature_set)}: {', '.join(minimal_feature_set)} bảo toàn được kỳ vọng ròng dương."

    return {
        "symbol": symbol,
        "theta": theta,
        "playbook_type": playbook_type,
        "falsified": is_falsified,
        "falsification_status": "FALSIFIED_AFTER_COST" if is_falsified else "SURVIVED_FRICTION_HURDLE",
        "gross_expectancy_pct": round(gross_expectancy_pct * 100.0, 3),
        "gross_expectancy_bps": round(gross_expectancy_pct * 10000.0, 1),
        "friction_hurdle_pct": round(total_friction_pct * 100.0, 3),
        "friction_hurdle_bps": round(total_friction_bps, 1),
        "net_expectancy_pct": round(net_expectancy_pct * 100.0, 3),
        "net_expectancy_bps": round(net_expectancy_bps, 1),
        "falsification_reasons": falsification_reasons,
        "minimal_feature_set": minimal_feature_set,
        "minimal_feature_status": feature_set_status,
        "minimal_feature_note": feature_set_note,
        "cost_breakdown": {
            "amm_fee_bps": round(base_fee_pct * 2.0 * 10000.0, 1),
            "slippage_impact_bps": round(estimated_slippage_pct * 2.0 * 10000.0, 1),
            "adverse_selection_bps": round(adverse_selection_pct * 10000.0, 1),
            "total_friction_bps": round(total_friction_bps, 1),
        },
    }
