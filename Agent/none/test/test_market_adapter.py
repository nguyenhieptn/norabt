from __future__ import annotations

from Agent.backend.market.service import MarketService
from Agent.backend.report.qc.reporting.market_adapter import normalize_market_payload
from Agent.none.test.conftest import FIXED_AS_OF_MS


def test_full_market_result_normalizes_without_losing_shape():
    market = MarketService().get_market_result("MU", venue_type="CEX", as_of_ms=FIXED_AS_OF_MS)
    normalized = normalize_market_payload(market)
    assert normalized["source_shape"] == "FULL_MARKET_RESULT"
    assert normalized["status"] == "OBSERVED"
    assert normalized["symbol"] == "MU"
    assert "trend" in normalized["metrics"]


def test_compact_market_posture_does_not_fabricate_full_fields():
    normalized = normalize_market_payload(
        {
            "symbol": "MU",
            "venue_type": "CEX",
            "available": True,
            "posture": "RANGE",
            "posture_evidence": ["weekly candles"],
            "trend": "RANGING",
            "volatility": "NORMAL",
            "liquidity": "DEEP",
            "data_quality": {"warnings": []},
        }
    )
    assert normalized["source_shape"] == "COMPACT_MARKET_POSTURE"
    assert normalized["metrics"]["trend"] == "RANGING"
    assert normalized["metrics"]["comparison"] is None
    assert "compact" in normalized["limitations"][0]


def test_missing_market_is_explicit():
    normalized = normalize_market_payload(None)
    assert normalized["status"] == "UNKNOWN"
    assert normalized["metrics"] == {}
