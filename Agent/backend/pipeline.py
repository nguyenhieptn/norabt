from __future__ import annotations

import logging
from pathlib import Path
import threading
from typing import Callable, List, Optional

from pydantic import BaseModel, Field

from Agent.backend.control.execution.okx_executor import OKXControlExecutor
from Agent.backend.control.policy.decision_engine import ControlDecisionEngine
from Agent.backend.control.schemas.control_decision import (
    ControlDecision,
    ExecutionMode,
)
from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.coverage import plan_market_coverage, resolve_planned_markets
from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.bot.mcp.service import BotObservationService
from Agent.backend.report.qc.schemas.risk_assessment import BotRiskAssessment
from Agent.backend.report.qc.history.store import AssessmentHistoryStore
from Agent.backend.report.qc.service import QCCoreService
from Agent.backend.market.universe.registry import UniverseRegistry

logger = logging.getLogger(__name__)


class ResolvedMarketShare(BaseModel):
    """Một thị trường ĐÃ GIẢI ĐƯỢC trong lượt phủ sóng theo mục tiêu (xem
    `Agent/backend/market/coverage.py`) -- CHỈ để trình bày/đo độ phủ,
    KHÔNG BAO GIỜ đi vào `QCCoreService.assess_bot()` (hàm đó vẫn chỉ nhận
    đúng MỘT `market`, thị trường CHÍNH -- xem `run()` bên dưới).
    """

    symbol: str
    share_pct: float
    market: MarketResult


class UnresolvedMarketShare(BaseModel):
    """Một thị trường NẰM TRONG kế hoạch phủ sóng nhưng KHÔNG lấy được dữ
    liệu -- lý do thường gặp nhất là bot giao dịch một công cụ OKX không
    công khai (cổ phiếu: SNDK, MU, SKHYNIX, LITE, PUMP, HYPE, CRCL...), hoặc
    hết hạn chờ (`reason="TIMEOUT"`). KHÔNG BAO GIỜ suy diễn/thay bằng thị
    trường khác.
    """

    symbol: str
    share_pct: float
    reason: str


class RiskSupervisionResult(BaseModel):
    traded_symbol: str
    market_available: bool
    market_resolution: str
    universe_eligible: bool
    eligibility_reason: str
    market_result: Optional[MarketResult] = None
    bot_result: BotResult
    risk_assessment: BotRiskAssessment
    control_decision: ControlDecision
    # Việc 3 (đứng tên gốc, giữ nguyên): thị trường đứng thứ hai -- CHỈ để
    # trình bày (web/data.py's `_secondary_market_evidence` / report_page.py),
    # KHÔNG BAO GIỜ đưa vào `QCCoreService.assess_bot()` bên dưới (công thức
    # chấm điểm chỉ nhận đúng `market_result` ở trên, không đổi bởi hai
    # trường này). Từ khi có phủ sóng theo mục tiêu (`resolved_markets` bên
    # dưới), đây là thị trường XẾP HẠNG CAO NHẤT (theo `share_pct`) trong
    # `resolved_markets` khác thị trường CHÍNH -- không nhất thiết còn là
    # đúng thị trường có exposure cao thứ nhì bot BÁO CÁO (nếu mã đó không
    # có dữ liệu thị trường, một mã thấp hơn nhưng GIẢI ĐƯỢC sẽ đứng vào
    # đây thay). `None` khi bot chỉ giao dịch một mã, hoặc không mã phụ nào
    # giải được -- xem `run()`.
    secondary_traded_symbol: Optional[str] = None
    secondary_market_result: Optional[MarketResult] = None
    # Phủ sóng theo mục tiêu (xem Agent/backend/market/coverage.py) -- thay
    # "luôn đúng 2 thị trường: chính + phụ" ở trên bằng "giải tới khi đạt
    # X% phủ sóng exposure, có trần cứng". `resolved_markets` liệt kê MỌI
    # thị trường đã giải được (bao gồm cả thị trường CHÍNH, luôn đứng đầu
    # sau khi sort theo `share_pct` giảm dần), `unresolved_markets` liệt kê
    # những mã nằm trong kế hoạch phủ sóng nhưng KHÔNG lấy được dữ liệu
    # (không suy diễn/thay thế), `coverage_achieved_pct` là tỉ trọng THẬT
    # đã phủ được (0-100, tổng `share_pct` của `resolved_markets`) -- KHÔNG
    # phải mục tiêu, `None` khi bot không đo được exposure nào cả (khác
    # `0.0`, tránh đọc nhầm thành "phủ được 0%").
    resolved_markets: List[ResolvedMarketShare] = Field(default_factory=list)
    unresolved_markets: List[UnresolvedMarketShare] = Field(default_factory=list)
    coverage_achieved_pct: Optional[float] = None


class RiskSupervisionPipeline:
    """One vertical slice: bot snapshot -> its real market -> QC -> control record."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        market_service: Optional[MarketService] = None,
        bot_service: Optional[BotObservationService] = None,
        controller: Optional[ControlDecisionEngine] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        history: Optional[AssessmentHistoryStore] = None,
        persist_history: bool = True,
    ) -> None:
        self.history = history or AssessmentHistoryStore()
        self.persist_history = persist_history
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.market_service = market_service or MarketService(
            self.data_dir, evaluation_mode
        )
        self.bot_service = bot_service or BotObservationService(
            self.data_dir, evaluation_mode
        )
        self.controller = controller or ControlDecisionEngine(
            mode=ExecutionMode.READ_ONLY
        )

    def resolve_market(
        self, traded_symbol: str, as_of_ms: Optional[int] = None
    ) -> tuple[Optional[MarketResult], str]:
        """Find the market the bot actually trades, never a substitute."""
        for venue_type in ("CEX", "DEX"):
            try:
                return (
                    self.market_service.get_market_result(
                        traded_symbol, venue_type=venue_type, as_of_ms=as_of_ms
                    ),
                    f"RESOLVED_{venue_type}",
                )
            except (MarketDataUnavailableError, ValueError):
                continue
        return None, "NO_MARKET_DATA_FOR_TRADED_SYMBOL"

    def run(
        self,
        asset: str,
        bot_folder_name: str,
        venue_type: str = "CEX",
        seed: int = 42,
        as_of_ms: Optional[int] = None,
        previous_assessment: Optional[BotRiskAssessment] = None,
        portfolio_bots: Optional[List[BotResult]] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: int = 500,
        # Việc thanh tiến độ THẬT (xem plan_progress.md mục A): tuỳ chọn,
        # `None` mặc định -- MỌI caller hiện có (run_report.py, agent_server.py,
        # test cũ) không đổi hành vi một chút nào khi không truyền tham số
        # này. Khi có, được gọi đúng 4 lần, đúng 4 ranh giới THẬT trong hàm
        # này (không phải đồng hồ giả): "ledger" trước khi nạp sổ lệnh OKX +
        # Monte Carlo, "markets" trước khi giải các thị trường liên quan,
        # "scoring" trước khi chấm 10 chiều rủi ro, "decision" trước khi ra
        # quyết định kiểm soát cuối cùng. Không bao giờ được phép làm hỏng
        # `run()` -- một exception từ chính callback (vd. registry phía web
        # lỗi) bị nuốt tại chỗ, giống mọi side-channel phụ trợ khác trong dự
        # án này (snapshot.set_snapshot, narrative sinh nền, ...).
        progress: Optional[Callable[[str], None]] = None,
    ) -> RiskSupervisionResult:
        def _notify(stage: str) -> None:
            if progress is None:
                return
            try:
                progress(stage)
            except Exception:  # noqa: BLE001 - xem docstring tham số `progress`
                logger.exception(
                    "RiskSupervisionPipeline.run: progress callback failed at "
                    "stage %r -- ignoring, must never break the pipeline",
                    stage,
                )

        # Suy đoán trước thị trường CHÍNH bằng đúng cái tên gọi vào (`asset`),
        # chạy song song với việc đọc sổ lệnh bên dưới -- không phải lúc nào
        # cũng đúng (bot DEX được xếp theo slot, không theo instrument thật;
        # `traded_symbol` chỉ biết chắc SAU khi đọc xong sổ lệnh, xem
        # `BotObservationService`'s docstring cho ví dụ thật). Không đoán bừa
        # kết quả: chỉ LÀM ẤM sẵn cache tiến trình 45s mà `MarketService` đã
        # có cho `LiveMarketDataSource` (xem service.py's
        # `_market_result_cache`) -- khi đoán đúng, `resolve_planned_markets`
        # bên dưới đọc trúng cache thay vì gọi OKX lại; khi đoán sai thì kết
        # quả bị bỏ, mọi thứ chạy TUẦN TỰ y hệt trước, không mất gì.
        #
        # Với đường `--source file` mặc định (không mạng, không cache) đây
        # gần như không tốn gì: đọc file cục bộ vốn đã rẻ hơn phí khởi tạo
        # một luồng.
        speculative_market: Optional[threading.Thread] = None
        if as_of_ms is None:
            speculative_market = threading.Thread(
                target=self.resolve_market,
                args=(asset, None),
                name="norabt-speculative-market",
                daemon=True,
            )
            speculative_market.start()

        _notify("ledger")
        bot = self.bot_service.get_bot_result(
            asset,
            bot_folder_name,
            seed=seed,
            venue_type=venue_type,
            as_of_ms=as_of_ms,
            simulation_iterations=simulation_iterations,
            simulation_horizon=simulation_horizon,
        )
        traded_symbol = bot.identity.symbol
        if speculative_market is not None:
            # Cache ấm hay không thì luồng này cũng phải join trước khi tiếp
            # tục -- không để nó rơi vào nền qua khỏi đời `run()`.
            speculative_market.join()

        # Phủ sóng theo mục tiêu (thay "luôn đúng 2 thị trường: chính + phụ"
        # ở bản trước) -- xem Agent/backend/market/coverage.py cho toàn bộ
        # lý do (đo thật trên 30 bot: chỉ giải 1-2 mã như trước chỉ phủ
        # trung vị 44.1%/61.7% giá trị giao dịch, trong khi trung vị chỉ
        # cần 4 mã để đạt 80%). `plan_market_coverage` chọn bộ symbol cần
        # thử (thị trường CHÍNH luôn đứng đầu), `resolve_planned_markets`
        # giải chúng song song qua ĐÚNG `self.resolve_market` (đi qua
        # MarketService/AdaptiveThrottle như trước, không vòng qua nhịp
        # tiết chế OKX) -- thị trường CHÍNH đợi tới khi xong, các thị
        # trường còn lại chia nhau một ngân sách chờ chung, quá hạn thì bỏ
        # qua chứ không kéo cả lượt phân tích.
        exposure_share = bot.identity.symbol_exposure_share or {}
        planned_symbols = plan_market_coverage(traded_symbol, exposure_share)
        _notify("markets")
        raw_results = resolve_planned_markets(
            planned_symbols,
            traded_symbol,
            lambda symbol: self.resolve_market(symbol, as_of_ms),
        )
        market, resolution = raw_results.get(
            traded_symbol, (None, "NO_MARKET_DATA_FOR_TRADED_SYMBOL")
        )

        # RÀNG BUỘC CỨNG (chưa đổi trong đợt này): `market` ở trên -- và chỉ
        # nó -- là thứ đi vào `QCCoreService.assess_bot()` bên dưới. Mọi thị
        # trường khác trong `resolved_markets`/`unresolved_markets` CHỈ để
        # trình bày/đo độ phủ thật đã đạt được.
        resolved_markets: List[ResolvedMarketShare] = []
        unresolved_markets: List[UnresolvedMarketShare] = []
        for symbol in planned_symbols:
            # KHÔNG làm tròn ở đây -- xem cùng comment ở cohort.py: làm tròn
            # chỉ diễn ra ở tầng trình bày/serialize.
            share_pct = float(exposure_share.get(symbol, 0.0) or 0.0) * 100.0
            outcome = raw_results.get(symbol)
            if outcome is None:
                # Vắng mặt trong `raw_results` = hết hạn chờ chung của thị
                # trường phụ (xem resolve_planned_markets) -- không phải
                # "không có dữ liệu", nhưng cách xử lý ở tầng trình bày là
                # như nhau: ghi nhận CHƯA ĐO ĐƯỢC, không suy diễn.
                unresolved_markets.append(
                    UnresolvedMarketShare(
                        symbol=symbol, share_pct=share_pct, reason="TIMEOUT"
                    )
                )
                continue
            resolved_market, resolved_reason = outcome
            if resolved_market is None:
                unresolved_markets.append(
                    UnresolvedMarketShare(
                        symbol=symbol, share_pct=share_pct, reason=resolved_reason
                    )
                )
            else:
                resolved_markets.append(
                    ResolvedMarketShare(
                        symbol=symbol, share_pct=share_pct, market=resolved_market
                    )
                )
        resolved_markets.sort(key=lambda item: item.share_pct, reverse=True)
        coverage_achieved_pct = (
            round(sum(item.share_pct for item in resolved_markets), 2)
            if exposure_share
            else None
        )
        secondary = next(
            (item for item in resolved_markets if item.symbol != traded_symbol),
            None,
        )
        secondary_traded_symbol = secondary.symbol if secondary is not None else None
        secondary_market_result = secondary.market if secondary is not None else None

        eligible = False
        reason = "NO_MARKET_DATA_FOR_TRADED_SYMBOL"
        if market is not None:
            registry = UniverseRegistry(self.data_dir)
            eligible = any(
                candidate.asset_id == market.asset_id
                for candidate in registry.list_all()
            )
            reason = registry.list_rejections().get(
                market.asset_id, "ELIGIBLE" if eligible else "NOT_IN_UNIVERSE"
            )

        prior = previous_assessment or self.history.latest(bot.identity.bot_id)
        _notify("scoring")
        assessment = QCCoreService.assess_bot(
            market,
            bot,
            previous_assessment=prior,
            portfolio_bots=portfolio_bots,
        )
        if self.persist_history:
            self.history.append(assessment)
        _notify("decision")
        decision = OKXControlExecutor.execute(
            self.controller.decide(assessment, now_ms=as_of_ms)
        )
        return RiskSupervisionResult(
            traded_symbol=traded_symbol,
            market_available=market is not None,
            market_resolution=resolution,
            universe_eligible=eligible,
            eligibility_reason=reason,
            market_result=market,
            bot_result=bot,
            risk_assessment=assessment,
            control_decision=decision,
            secondary_traded_symbol=secondary_traded_symbol,
            secondary_market_result=secondary_market_result,
            resolved_markets=resolved_markets,
            unresolved_markets=unresolved_markets,
            coverage_achieved_pct=coverage_achieved_pct,
        )
