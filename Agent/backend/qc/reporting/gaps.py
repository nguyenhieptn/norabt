from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from Agent.backend.market.schemas.market_result import MarketResult

DIM_LABEL = {
    "market_alignment": "Đồng thuận thị trường",
    "performance_quality": "Chất lượng hiệu suất",
    "return_r_quality": "Chất lượng lợi nhuận / R",
    "drawdown_risk": "Rủi ro sụt vốn",
    "tail_risk": "Rủi ro đuôi",
    "leverage_exposure": "Đòn bẩy / Exposure",
    "behavioral_risk": "Hành vi giao dịch",
    "strategy_drift": "Độ bền chiến lược qua các pha",
    "liquidity_execution": "Thanh khoản / Khớp lệnh",
    "portfolio_risk": "Rủi ro danh mục",
}


class EvidenceGap(BaseModel):
    """One missing input, and what collecting it would unlock."""

    gap_id: str
    scope: str
    evidence: str
    detail: str
    unlocks: List[str] = Field(default_factory=list)
    affected_bots: List[str] = Field(default_factory=list)
    priority: str = "MEDIUM"

    @property
    def weight(self) -> int:
        return len(self.unlocks) * max(1, len(self.affected_bots))


def build_gaps(rows, markets: Dict[str, Optional[MarketResult]]) -> List[EvidenceGap]:
    """Derive the collection backlog from what the assessment could not evaluate."""
    gaps: Dict[str, EvidenceGap] = {}

    def add(
        gap_id: str,
        scope: str,
        evidence: str,
        detail: str,
        unlocks: List[str],
        bot: Optional[str] = None,
    ) -> None:
        gap = gaps.get(gap_id)
        if gap is None:
            gap = EvidenceGap(
                gap_id=gap_id,
                scope=scope,
                evidence=evidence,
                detail=detail,
                unlocks=unlocks,
            )
            gaps[gap_id] = gap
        if bot and bot not in gap.affected_bots:
            gap.affected_bots.append(bot)

    for row in rows:
        if row.status != "EVALUATED":
            continue
        who = row.nick_name

        if not row.market_available:
            add(
                f"market:{row.traded_symbol}",
                f"Thị trường {row.traded_symbol}",
                "OHLCV + order book cho instrument bot đang trade",
                f"Bot giao dịch {row.traded_symbol} nhưng chưa có dữ liệu thị trường nào cho symbol này.",
                ["market_alignment", "liquidity_execution"],
                who,
            )
        if row.positions_outside_ledger_universe:
            add(
                "positions:outside_ledger_universe",
                "Vị thế ngoài sổ lệnh",
                "Sổ lệnh sâu hơn, hoặc danh sách instrument đầy đủ",
                f"{row.positions_outside_ledger_universe} vị thế không khớp bất kỳ "
                "instrument nào bot từng đóng gần đây; cần lịch sử sâu hơn để mở rộng "
                "tập ứng viên suy luận.",
                ["market_alignment", "liquidity_execution"],
                who,
            )
        if row.unknown_positions_count:
            if row.instrument_withheld_upstream:
                add(
                    "positions:instrument_id_upstream",
                    "Vị thế mở (OKX không công bố)",
                    "instId — không thu thập được",
                    "OKX trả instId rỗng cho trader này. Hệ thống đã suy luận được "
                    f"{row.inferred_positions_count} vị thế từ biến động giá ngụ ý; "
                    f"{row.unknown_positions_count} vị thế còn lại chưa quy được.",
                    ["market_alignment", "liquidity_execution"],
                    who,
                )
            else:
                add(
                    "positions:instrument_id",
                    "Vị thế mở",
                    "instId cho từng vị thế đang mở",
                    "Vị thế có side/margin/leverage nhưng thiếu mã instrument, nên exposure không quy được về thị trường.",
                    ["market_alignment", "liquidity_execution", "leverage_exposure"],
                    who,
                )
        if row.capital_basis == "UNAVAILABLE":
            add(
                "capital:equity_history",
                "Vốn tài khoản",
                "Lịch sử equity hoặc nạp/rút",
                "AUM nhỏ hơn PnL lũy kế nên không dựng được vốn khởi điểm; sụt vốn lịch sử chỉ báo được bằng USDT.",
                ["drawdown_risk"],
                who,
            )
        if row.reconciliation_status == "IDENTITY_MISMATCH":
            add(
                "ledger:wrong_owner",
                "Sổ lệnh sai chủ sở hữu",
                "Sổ lệnh đúng của bot này",
                "File sổ lệnh thuộc về một uniqueCode khác và đã bị từ chối; bot đang được "
                "đánh giá mà không có lịch sử lệnh.",
                [
                    "performance_quality",
                    "return_r_quality",
                    "tail_risk",
                    "drawdown_risk",
                ],
                who,
            )
        if row.reconciliation_status == "PARTIAL_LEDGER":
            add(
                "ledger:full_history",
                "Sổ lệnh",
                "Lịch sử đầy đủ theo leadDays",
                "Sổ lệnh mới phủ một phần thời gian hoạt động; cần phân trang sâu hơn để "
                "phủ hết lịch sử.",
                ["performance_quality", "tail_risk"],
                who,
            )
        if row.reconciliation_status == "MISMATCH":
            add(
                "ledger:completeness",
                "Sổ lệnh",
                "Sổ lệnh đầy đủ khớp với PnL tổng",
                "PnL sổ lệnh lệch so với báo cáo tổng, nghĩa là sổ lệnh chưa đầy đủ.",
                ["performance_quality", "return_r_quality", "tail_risk"],
                who,
            )
        if "strategy_drift" in (row.unknown_dimensions or []):
            add(
                "bot:declared_strategy",
                "Khai báo chiến lược",
                "Chiến lược bot tự khai báo",
                "Không có chiến lược khai báo nên không so được với hành vi quan sát.",
                ["strategy_drift"],
                who,
            )

    for symbol, market in markets.items():
        if market is None:
            continue
        for source in market.data_quality.missing_sources:
            unlocks = {
                "orderbook_l2": ["liquidity_execution"],
                "taker_flow": ["market_alignment"],
                "derivatives_oi": ["leverage_exposure"],
                "macro": ["portfolio_risk"],
                "token_security": ["portfolio_risk"],
                "sentiment": ["market_alignment"],
            }.get(source, [])
            add(
                f"market_source:{symbol}:{source}",
                f"Thị trường {symbol}",
                source,
                f"Nguồn {source} chưa được thu thập cho {symbol}.",
                unlocks,
            )
        for source in market.data_quality.stale_sources:
            add(
                f"market_stale:{symbol}:{source}",
                f"Thị trường {symbol}",
                f"{source} (cũ)",
                f"Nguồn {source} lệch quá xa mốc dữ liệu của {symbol}; cần crawl lại cùng nhịp.",
                ["liquidity_execution"] if "orderbook" in source else [],
            )

    ordered = sorted(gaps.values(), key=lambda gap: -gap.weight)
    for gap in ordered:
        gap.priority = (
            "HIGH" if gap.weight >= 4 else "MEDIUM" if gap.weight >= 2 else "LOW"
        )
    return ordered
