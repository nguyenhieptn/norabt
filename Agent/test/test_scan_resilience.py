"""One bad bot must not abort a cohort scan or a paired-report build.

Context: CohortAssessmentService.scan() and PairedBotReportService.build()
already turned a bad *file* (BotDataUnavailableError / ValueError) into one
FAILED row and kept going. The new live source (Agent/backend/sources/
bot_source.py -- LiveBotDataSource) instead raises BotSourceError on an OKX
failure, and that exception was not in either except clause, so it escaped
the loop uncaught: in live mode, one network hiccup on (say) bot 15 of 30
used to abort the whole scan and waste every request already spent on the
first 14 bots. These tests reproduce that with a fake data source (no
network) and pin down the fix: BotSourceError degrades to a FAILED row like
everything else, the failure reason survives into that row, and the rest of
the cohort is still scored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Set

from Agent.backend.qc.reporting.cohort import CohortAssessmentService
from Agent.backend.qc.reporting.pair_report import PairedBotReportService
from Agent.backend.sources.bot_source import BotSourceError, FileBotDataSource
from Agent.test.conftest import write_bot_dataset

BOT_COUNT = 30


def _closed_trades(code: str, symbol: str, pnl: float = 5.0, count: int = 10):
    return [
        {
            "subPosId": f"{code}-{i}",
            "instId": f"{symbol}-USDT-SWAP",
            "posSide": "long",
            "openTime": str(1_000 + i),
            "closeTime": str(5_000 + i),
            "pnl": str(pnl),
            "margin": "100",
            "lever": "2",
            "uniqueCode": code,
        }
        for i in range(count)
    ]


def _write_cohort(tmp_path: Path, count: int = BOT_COUNT) -> list[str]:
    """30 independent, otherwise-healthy bots on one asset -- a stand-in for
    a live cohort scan, kept on disk so the test needs no network access."""
    codes = [f"CODE{i:02d}" for i in range(count)]
    for code in codes:
        write_bot_dataset(
            tmp_path,
            asset="TEST",
            folder=f"bot_{code}",
            overview={"uniqueCode": code, "nickName": f"Bot {code}", "aum": 1000.0},
            closed_trades=_closed_trades(code, "TEST"),
        )
    return codes


def _break_ledger_for(
    monkeypatch,
    broken_codes: Set[str],
    reason: Callable[[str], str],
) -> None:
    """Make FileBotDataSource.get_ledger raise BotSourceError for a chosen
    set of bots and behave normally for everyone else -- simulating an OKX
    outage that only hits some bots, without ever touching the network."""
    original = FileBotDataSource.get_ledger

    def fake_get_ledger(self, unique_code, bot_dir=None):
        folder_code = bot_dir.name.replace("bot_", "") if bot_dir else unique_code
        if folder_code in broken_codes:
            raise BotSourceError(reason(folder_code))
        return original(self, unique_code, bot_dir=bot_dir)

    monkeypatch.setattr(FileBotDataSource, "get_ledger", fake_get_ledger)


# --------------------------------------------------------------------------
# CohortAssessmentService.scan()
# --------------------------------------------------------------------------


def test_one_bot_source_error_leaves_the_rest_of_the_cohort_scored(
    tmp_path, monkeypatch
):
    codes = _write_cohort(tmp_path)
    broken = codes[14]  # an arbitrary bot in the middle of the scan order
    reason = f"OKX lỗi khi lấy sổ lệnh cho mã {broken}: giả lập mất mạng"
    _break_ledger_for(monkeypatch, {broken}, lambda _code: reason)

    report = CohortAssessmentService(tmp_path, persist_history=False).scan(
        simulation_iterations=10, simulation_horizon=10
    )

    assert report.snapshots_scanned == len(codes)
    assert report.bots_failed == 1
    assert report.distinct_bots == len(codes) - 1

    failed_rows = [row for row in report.rows if row.status == "FAILED"]
    assert len(failed_rows) == 1
    assert failed_rows[0].bot_folder == f"bot_{broken}"
    # The reason must survive into the row -- in live mode it is the only
    # diagnostic an operator has for which bot broke and why.
    assert failed_rows[0].error == reason

    evaluated_codes = {
        row.unique_code for row in report.rows if row.status == "EVALUATED"
    }
    assert evaluated_codes == set(codes) - {broken}


def test_multiple_bot_source_errors_all_reported_and_scan_completes(
    tmp_path, monkeypatch
):
    codes = _write_cohort(tmp_path)
    broken = {codes[3], codes[10], codes[27]}
    _break_ledger_for(monkeypatch, broken, lambda code: f"OKX lỗi mã {code}")

    report = CohortAssessmentService(tmp_path, persist_history=False).scan(
        simulation_iterations=10, simulation_horizon=10
    )

    assert report.snapshots_scanned == len(codes)
    assert report.bots_failed == len(broken)
    assert report.distinct_bots == len(codes) - len(broken)

    failed_codes = {
        row.bot_folder.replace("bot_", "")
        for row in report.rows
        if row.status == "FAILED"
    }
    assert failed_codes == broken
    for row in report.rows:
        if row.status == "FAILED":
            code = row.bot_folder.replace("bot_", "")
            assert row.error == f"OKX lỗi mã {code}"


def test_missing_bot_file_still_produces_one_failed_row_not_a_crash(tmp_path):
    """Regression: the pre-existing BotDataUnavailableError path (a bot folder
    missing trade_list.json) must behave exactly as before the BotSourceError
    fix -- one FAILED row with the same conclusion text, scan continues."""
    codes = _write_cohort(tmp_path)
    broken = codes[0]
    (tmp_path / "cex" / "TEST" / "bot" / f"bot_{broken}" / "trade_list.json").unlink()

    report = CohortAssessmentService(tmp_path, persist_history=False).scan(
        simulation_iterations=10, simulation_horizon=10
    )

    assert report.bots_failed == 1
    assert report.distinct_bots == len(codes) - 1
    failed = next(row for row in report.rows if row.status == "FAILED")
    assert "Missing bot data file: trade_list.json" in failed.error
    assert failed.conclusion == "Could not be assessed because the input data was invalid."


# --------------------------------------------------------------------------
# PairedBotReportService.build()
# --------------------------------------------------------------------------


def _write_pair_dataset(tmp_path: Path, n_assets: int = 3):
    """n_assets asset blocks, each with a lead and a laggard bot -- the same
    shape run_report.py's step-2 pairing produces, kept small but with more
    than one block so a mid-loop failure has other blocks left to prove."""
    codes: list[str] = []
    assets = []
    for i in range(n_assets):
        asset = f"AST{i}"
        lead, lag = f"LEAD{i}", f"LAG{i}"
        codes += [lead, lag]
        for code, pnl in ((lead, 50.0), (lag, -20.0)):
            write_bot_dataset(
                tmp_path,
                asset=asset,
                folder=f"bot_{code}",
                overview={"uniqueCode": code, "nickName": f"Bot {code}", "aum": 1000.0},
                closed_trades=_closed_trades(code, asset, pnl=pnl),
            )
        assets.append(
            {
                "venue": "CEX",
                "symbol": asset,
                "underlying": asset,
                "candidates": 2,
                "top": {
                    "code": lead,
                    "name": f"Bot {lead}",
                    "okx_rank": 1,
                    "roi_pct": 50.0,
                    "trades_on_asset": 10,
                },
                "mid": {
                    "code": lag,
                    "name": f"Bot {lag}",
                    "okx_rank": 2,
                    "roi_pct": 5.0,
                    "trades_on_asset": 10,
                },
            }
        )
    selection = {"assets": assets, "unique_codes": codes}
    path = tmp_path / "universe" / "bot_selection.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(selection), encoding="utf-8")
    return path, codes


def test_pair_report_one_bot_source_error_does_not_abort_the_whole_build(
    tmp_path, monkeypatch
):
    selection, codes = _write_pair_dataset(tmp_path, n_assets=3)
    broken = codes[2]  # the laggard of the second asset block
    reason = f"OKX lỗi khi lấy sổ lệnh cho mã {broken}: giả lập lỗi mạng"
    _break_ledger_for(monkeypatch, {broken}, lambda _code: reason)

    report = PairedBotReportService(data_dir=tmp_path).build(
        simulation_iterations=10,
        simulation_horizon=10,
        selection_path=selection,
    )

    assert report.slots == 3
    assert report.bots_failed == 1
    assert report.bots_evaluated == len(codes) - 1

    failed_bots = [bot for block in report.blocks for bot in block.bots if bot.error]
    assert len(failed_bots) == 1
    assert failed_bots[0].unique_code == broken
    # BotSourceError must not be swallowed: pair_report tags it with its
    # exception type and keeps the original OKX-facing message.
    assert "BotSourceError" in failed_bots[0].error
    assert reason in failed_bots[0].error

    ok_codes = {
        bot.unique_code
        for block in report.blocks
        for bot in block.bots
        if not bot.error
    }
    assert ok_codes == set(codes) - {broken}


def test_pair_report_missing_bot_file_regression_unchanged(tmp_path):
    """Regression: the old BotDataUnavailableError path in pair_report.py
    (get_bot_result raising because overview.json is missing, while
    trade_list.json is still there so _locate can find the bot at all) must
    still yield the same one failed slot, other blocks unaffected."""
    selection, codes = _write_pair_dataset(tmp_path, n_assets=2)
    broken = codes[0]
    asset_dir = next(
        p for p in tmp_path.rglob(f"bot_{broken}") if (p / "trade_list.json").exists()
    )
    (asset_dir / "overview.json").unlink()

    report = PairedBotReportService(data_dir=tmp_path).build(
        simulation_iterations=10,
        simulation_horizon=10,
        selection_path=selection,
    )

    assert report.bots_failed == 1
    assert report.bots_evaluated == len(codes) - 1
    failed_bots = [bot for block in report.blocks for bot in block.bots if bot.error]
    assert len(failed_bots) == 1
    assert failed_bots[0].unique_code == broken
    assert "Missing bot data file: overview.json" in failed_bots[0].error
