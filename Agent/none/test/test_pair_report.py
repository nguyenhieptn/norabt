"""Step 2 pairs each asset's two bots; the report must not lose or invent either."""

from __future__ import annotations

import json
from pathlib import Path

from Agent.backend.qc.reporting.pair_report import (
    ROLE_LAGGARD,
    ROLE_LEAD,
    PairedBotReportService,
)
from Agent.backend.qc.reporting.render import render_pair_report
from Agent.none.test.conftest import FIXED_AS_OF_MS, write_bot_dataset, write_market_dataset

LAST_CANDLE_MS = 1_789_000_000_000


def _ledger(count: int, pnl: float, symbol: str, side: str = "long"):
    return [
        {
            "subPosId": str(3_900_000_000_000_000_000 + i),
            "instId": f"{symbol}-USDT-SWAP",
            "posSide": side,
            "openTime": str(LAST_CANDLE_MS - (count - i) * 3_600_000),
            "closeTime": str(LAST_CANDLE_MS - (count - i) * 3_600_000 + 60_000),
            "pnl": str(pnl),
            "pnlRatio": "0.05",
            "margin": "100.0",
            "lever": "10",
            "subPos": "5",
        }
        for i in range(count)
    ]


def _dataset(tmp_path: Path):
    write_market_dataset(tmp_path, asset="AAA", last_candle_ms=LAST_CANDLE_MS)
    for code, pnl in (("LEAD", 50.0), ("LAG", -20.0)):
        write_bot_dataset(
            tmp_path,
            asset="AAA",
            folder=f"bot_{code}",
            overview={
                "uniqueCode": code,
                "nickName": f"Bot {code}",
                "aum": 10_000.0,
                "weekly_pnl_history": [
                    {"beginTs": "1788710400000", "pnl": "100.0", "pnlRatio": "0.01"}
                ],
            },
            closed_trades=_ledger(30, pnl, "AAA"),
        )
    selection = {
        "assets": [
            {
                "venue": "CEX",
                "symbol": "AAA",
                "underlying": "AAA",
                "candidates": 2,
                "evidence_bar": {"min_total_trades": 30, "min_trades_on_asset": 3},
                "mid_basis": "WEAKER_PERFORMER",
                "top": {
                    "code": "LEAD",
                    "name": "Bot LEAD",
                    "okx_rank": 1,
                    "roi_pct": 50.0,
                    "trades_on_asset": 30,
                },
                "mid": {
                    "code": "LAG",
                    "name": "Bot LAG",
                    "okx_rank": 40,
                    "roi_pct": 5.0,
                    "trades_on_asset": 30,
                },
            }
        ],
        "unique_codes": ["LEAD", "LAG"],
    }
    path = tmp_path / "universe" / "bot_selection.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(selection), encoding="utf-8")
    return path


def test_every_slot_reports_both_bots_with_their_roles(tmp_path):
    selection = _dataset(tmp_path)

    report = PairedBotReportService(data_dir=tmp_path).build(
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=50,
        simulation_horizon=50,
        selection_path=selection,
    )

    assert report.slots == 1
    assert report.bots_evaluated == 2 and report.bots_failed == 0
    roles = [bot.role for bot in report.blocks[0].bots]
    assert roles == [ROLE_LEAD, ROLE_LAGGARD]


def test_the_asset_trade_count_comes_from_the_ledger_not_the_sample(tmp_path):
    """The selection profiled 100 fills; a 500-trade ledger must not be truncated."""
    selection = _dataset(tmp_path)
    data = json.loads(selection.read_text(encoding="utf-8"))
    data["assets"][0]["top"]["trades_on_asset"] = 4
    selection.write_text(json.dumps(data), encoding="utf-8")

    report = PairedBotReportService(data_dir=tmp_path).build(
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=50,
        simulation_horizon=50,
        selection_path=selection,
    )

    assert report.blocks[0].bots[0].trades_on_asset == 30


def test_a_bot_without_crawled_data_is_reported_as_an_error_not_skipped(tmp_path):
    selection = _dataset(tmp_path)
    data = json.loads(selection.read_text(encoding="utf-8"))
    data["assets"][0]["mid"]["code"] = "NOTCRAWLED"
    selection.write_text(json.dumps(data), encoding="utf-8")

    report = PairedBotReportService(data_dir=tmp_path).build(
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=50,
        simulation_horizon=50,
        selection_path=selection,
    )
    laggard = report.blocks[0].bots[1]

    assert report.bots_failed == 1
    assert laggard.error
    assert "Not enough bots with data to compare" in report.blocks[0].comparison[0]


def test_the_rendered_report_marks_a_capped_drawdown(tmp_path):
    selection = _dataset(tmp_path)
    report = PairedBotReportService(data_dir=tmp_path).build(
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=50,
        simulation_horizon=50,
        selection_path=selection,
    )
    for bot in report.blocks[0].bots:
        bot.max_drawdown_pct = 100.0
        bot.max_drawdown_capped = True

    text = render_pair_report(report)

    assert "100.0%*" in text
    assert "is a floor" in text


def test_the_report_states_it_is_not_a_verdict(tmp_path):
    selection = _dataset(tmp_path)
    report = PairedBotReportService(data_dir=tmp_path).build(
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=50,
        simulation_horizon=50,
        selection_path=selection,
    )

    assert any("not a risk verdict" in note for note in report.notes)
