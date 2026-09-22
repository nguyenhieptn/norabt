"""Normalize full and persisted compact market observations for reporting.

Live reports contain a typed `MarketResult`; persisted batch reports contain a
smaller market-posture document. This adapter preserves the distinction and
never fabricates missing full-market fields.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping


def normalize_market_payload(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {
            "source_shape": "MISSING",
            "status": "UNKNOWN",
            "metrics": {},
            "limitations": ["No market observation is available"],
        }
    if hasattr(raw, "model_dump"):
        payload = raw.model_dump(mode="json")
        return {
            "source_shape": "FULL_MARKET_RESULT",
            "status": "OBSERVED",
            "symbol": payload.get("symbol"),
            "venue": payload.get("venue"),
            "venue_type": payload.get("venue_type"),
            "as_of_ms": payload.get("as_of_ms"),
            "metrics": {
                "price": (payload.get("price_state") or {}).get("last_price"),
                "trend": (payload.get("structure_state") or {}).get("trend_state"),
                "volatility": (payload.get("structure_state") or {}).get("volatility_state"),
                "liquidity": payload.get("liquidity_state"),
                "orderflow": payload.get("orderflow_state"),
                "derivatives": payload.get("derivatives_state"),
            },
            "data_quality": payload.get("data_quality"),
            "limitations": list((payload.get("data_quality") or {}).get("warnings") or []),
        }
    if not isinstance(raw, Mapping):
        return {
            "source_shape": "INVALID",
            "status": "UNKNOWN",
            "metrics": {},
            "limitations": ["Market observation has an unsupported shape"],
        }
    payload = dict(raw)
    # `analysis_store`'s persisted shape is intentionally compact. A missing
    # field is not reconstructed from a similarly named full result field.
    known = {
        "posture": payload.get("posture"),
        "posture_evidence": payload.get("posture_evidence"),
        "trend": payload.get("trend"),
        "volatility": payload.get("volatility"),
        "liquidity": payload.get("liquidity"),
        "comparison": payload.get("comparison"),
    }
    limitations = list((payload.get("data_quality") or {}).get("warnings") or [])
    limitations.append("Persisted market posture is compact; unavailable full-market fields were not measured")
    return {
        "source_shape": "COMPACT_MARKET_POSTURE",
        "status": "OBSERVED" if payload.get("available", True) else "UNKNOWN",
        "symbol": payload.get("symbol"),
        "venue": payload.get("venue_type") or payload.get("venue"),
        "venue_type": payload.get("venue_type"),
        "as_of_ms": payload.get("generated_at_ms"),
        "metrics": known,
        "data_quality": payload.get("data_quality"),
        "limitations": limitations,
    }
