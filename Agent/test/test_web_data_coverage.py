"""`Agent/backend/web/data.py::_market_coverage_evidence` -- ánh xạ phủ sóng
theo mục tiêu (Agent/backend/market/coverage.py) từ `RiskSupervisionResult`
(nhánh LIVE, pipeline.py) sang hình dạng dict `report_page.py` đọc, cùng
hình dạng `assessment_store.py::_resolved_markets_payload`/
`_unresolved_markets_payload` ghi xuống assessment.json.

Dùng SimpleNamespace để giả lập `RiskSupervisionResult.resolved_markets`/
`unresolved_markets` (List[ResolvedMarketShare]/List[UnresolvedMarketShare],
pipeline.py) mà không phải dựng cả một MarketResult thật -- hàm này chỉ đọc
đúng vài thuộc tính (`.symbol`, `.share_pct`, `.market.venue_type`,
`.market.structure_state.trend_state.value`, ...), không tính toán gì.
"""

from __future__ import annotations

from types import SimpleNamespace

from Agent.backend.web.data import _market_coverage_evidence


def _fake_market(
    *,
    venue_type="CEX",
    trend="BULLISH",
    volatility="NORMAL",
    liquidity_tier="DEEP",
    flow_bias="BUY_PRESSURE",
    last_price=100.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        venue_type=venue_type,
        structure_state=SimpleNamespace(
            trend_state=SimpleNamespace(value=trend),
            volatility_state=SimpleNamespace(value=volatility),
        ),
        liquidity_state=SimpleNamespace(
            state_tier=SimpleNamespace(value=liquidity_tier)
        ),
        orderflow_state=SimpleNamespace(flow_bias=flow_bias),
        price_state=SimpleNamespace(last_price=last_price),
    )


def test_market_coverage_evidence_degrades_when_result_has_no_coverage_fields():
    """Một `RiskSupervisionResult` từ TRƯỚC đợt phủ sóng theo mục tiêu này
    (hoặc một fake/mocked result trong test khác không set các trường mới)
    không có `resolved_markets`/`unresolved_markets`/`coverage_achieved_pct`
    -- degrade về `[]`/`[]`/`None`, không raise."""
    result = SimpleNamespace()
    evidence = _market_coverage_evidence(result)
    assert evidence == {
        "resolved_markets": [],
        "unresolved_markets": [],
        "coverage_achieved_pct": None,
    }


def test_market_coverage_evidence_maps_resolved_and_unresolved_markets():
    result = SimpleNamespace(
        resolved_markets=[
            SimpleNamespace(symbol="AAA", share_pct=52.6, market=_fake_market()),
            SimpleNamespace(
                symbol="BBB",
                share_pct=21.1,
                market=_fake_market(
                    trend="BEARISH",
                    volatility="HIGH",
                    liquidity_tier="SHALLOW",
                    flow_bias="SELL_PRESSURE",
                    last_price=50.0,
                ),
            ),
        ],
        unresolved_markets=[
            SimpleNamespace(
                symbol="DDD", share_pct=10.5, reason="NO_MARKET_DATA_FOR_TRADED_SYMBOL"
            ),
        ],
        coverage_achieved_pct=73.7,
    )
    evidence = _market_coverage_evidence(result)
    assert evidence["resolved_markets"] == [
        {
            "symbol": "AAA",
            "share_pct": 52.6,
            "venue_type": "CEX",
            "trend": "BULLISH",
            "volatility": "NORMAL",
            "liquidity_tier": "DEEP",
            "flow_bias": "BUY_PRESSURE",
            "last_price": 100.0,
        },
        {
            "symbol": "BBB",
            "share_pct": 21.1,
            "venue_type": "CEX",
            "trend": "BEARISH",
            "volatility": "HIGH",
            "liquidity_tier": "SHALLOW",
            "flow_bias": "SELL_PRESSURE",
            "last_price": 50.0,
        },
    ]
    assert evidence["unresolved_markets"] == [
        {
            "symbol": "DDD",
            "share_pct": 10.5,
            "reason": "NO_MARKET_DATA_FOR_TRADED_SYMBOL",
        }
    ]
    assert evidence["coverage_achieved_pct"] == 73.7
