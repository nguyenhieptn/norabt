"""Step 3's verdict has to be readable one bot at a time, text included."""

from __future__ import annotations

import json

from pathlib import Path

from Agent.backend.report.qc.reporting.assessment_store import (
    rebuild_index,
    build_assessment,
    load_bot,
    persist,
)
from Agent.backend.report.qc.reporting.cohort import BotEvaluationRow


def _row(**overrides) -> BotEvaluationRow:
    base = dict(
        rank=1,
        status="OK",
        bot_id="bot_53AEED5A8E4EBBB2",
        unique_code="53AEED5A8E4EBBB2",
        nick_name="HaveARestin",
        traded_symbol="ETH",
        asset_context="ETH",
        venue_type="CEX",
        snapshot_venue="OKX",
        bot_folder="bot_53AEED5A8E4EBBB2",
        trade_count=143,
        win_rate=92.0,
        profit_factor=11.12,
        marked_profit_factor=0.16,
        payoff_ratio=1.02,
        average_win=80.0,
        average_loss=79.0,
        expectancy=67.0,
        total_pnl=9583.0,
        capital_at_risk=131_958.0,
        capital_basis="WEEKLY_EQUITY_CURVE",
        open_positions=95,
        open_loss=86_132.0,
        open_loss_to_capital_pct=65.0,
        max_drawdown_pct=0.5,
        max_loss_streak=3,
        max_win_streak=34,
        sharpe_ratio=16.13,
        sortino_ratio=9.65,
        pnl_median=58.0,
        pnl_skew=-0.1,
        pnl_kurtosis=18.0,
        trades_per_day=1.56,
        median_hold_minutes=1476.0,
        ledger_coverage_days=91.7,
        declared_lead_days=580,
        directional_bias="TWO_WAY",
        entry_style="MEAN_REVERSION",
        phase_coverage_pct=83.0,
        regime_dependence_pct=39.0,
        best_phase="UPTREND_VOLATILE",
        worst_phase="RANGE_VOLATILE",
        tested_in_downtrend=True,
        mc_iterations=10_000,
        mc_horizon=143,
        profit_pct_worst=3.9,
        profit_pct_p05=5.8,
        profit_pct_p50=7.3,
        profit_pct_p95=8.6,
        var_95_pct=-5.8,
        cvar_95_pct=-5.5,
        mar_ratio_median=19.0,
        p95_max_drawdown=0.4,
        worst_drawdown=1.0,
        p_ruin=0.0,
        p_loss_after_horizon=0.0,
        simulation_deferred_loss_bias=True,
        psr=1.0,
        deflated_sharpe=0.998,
        min_track_record_trades=20.0,
        selection_trials=9,
        inference_reliable=False,
        stress_verdict="SURVIVED",
        risk_score=70.0,
        quality_score=54.5,
        verdict="DRAWDOWN: HIGH · QUALITY: WEAK",
        verdict_reason="chốt hết sổ mở thì profit factor chỉ còn 0.16",
        hidden_risk_flags=["lỗ chưa chốt bằng 65% vốn"],
        confidence=80.0,
        risk_tier="CAO",
        recommended_action="REDUCE",
        measurement_mode="PARTIAL",
        reconciliation_status="PARTIAL_LEDGER",
        weighted_average=55.3,
        veto_floor=70.0,
        veto_reasons=["chốt hết sổ mở thì profit factor chỉ còn 0.16"],
        quality_components={"profitability": 0.0, "consistency": 100.0},
        quality_notes=["PF dùng để chấm là PF sau khi chốt hết sổ mở"],
        conclusion="DRAWDOWN: HIGH · QUALITY: WEAK",
    )
    base.update(overrides)
    return BotEvaluationRow(**base)


def _row_other(**overrides) -> BotEvaluationRow:
    """Bot THỨ HAI, để phân biệt "ghi đè index" với "hợp nhất index"."""
    base = dict(
        unique_code="0EAF7292CE2FAAC2",
        bot_id="bot_0EAF7292CE2FAAC2",
        nick_name="k001",
        bot_folder="bot_0EAF7292CE2FAAC2",
    )
    base.update(overrides)
    return _row(**base)


def test_assessment_leads_with_the_text_and_keeps_the_numbers():
    payload = build_assessment(_row(), 1_789_000_000_000)
    paragraphs = payload["recommendation"]["text"]

    joined = payload["recommendation"]["text_full"]
    assert joined == "\n\n".join(paragraphs)

    # The argument comes first and is the long part: it is what has to
    # convince. Everything after it is evidence to be checked against it.
    assert paragraphs[1].startswith("WHY THIS HAPPENED:")
    assert len(paragraphs[1]) == max(len(p) for p in paragraphs)
    # A verdict a reader will only glance at for a few seconds cannot afford
    # a paragraph that keeps arguing past the point it already made.
    assert len(paragraphs[1]) <= 350
    assert "0.16" in paragraphs[1] and "86,132" in paragraphs[1]
    # Cơ chế phải được NÊU TÊN, không chỉ nêu con số: người đọc cần biết
    # vì sao sổ đẹp mà vẫn nguy hiểm.
    assert "wins taken early" in paragraphs[1]

    # Then the proof, as bullets a reader can scan rather than a wall of prose.
    assert "EVIDENCE:" in paragraphs
    bullets = [p for p in paragraphs if p.startswith("• ")]
    assert len(bullets) <= 6
    assert all(len(b) < 160 for b in bullets)

    assert paragraphs[-1].startswith("CONCLUSION:")
    for fragment in ("payoff 1.02", "Monte Carlo 10,000 scenarios"):
        assert fragment in joined
    # The whole verdict has to stay a quick read, not just each piece of it.
    # Upper bound raised from 1100 to 1200 (task's own Việc 3): the closing
    # line used to end on a short imperative ("GIẢM tỷ trọng đang copy", ~24
    # chars) and now states one of this bot's own measured numbers plus the
    # consequence and hands the decision back to the reader instead of
    # ordering one -- unavoidably longer, still a bounded single sentence.
    assert 600 <= len(joined) <= 1200
    assert payload["scoring"]["veto_reasons"]
    assert payload["simulation"]["scope"] == "CLOSED_TRADES_ONLY"


def test_tail_that_stays_profitable_is_not_reported_as_a_loss():
    profitable = "\n\n".join(build_assessment(_row(), 1)["recommendation"]["text"])
    assert "worst 5% tail still profit 5.5%" in profitable

    losing = "\n\n".join(
        build_assessment(_row(cvar_95_pct=12.0), 1)["recommendation"]["text"]
    )
    assert "worst 5% tail loss 12.0%" in losing


def test_persist_mirrors_the_step_2_layout_and_reads_back(tmp_path):
    report = type(
        "Report", (), {"generated_at_ms": 1_789_000_000_000, "rows": [_row()]}
    )()
    written = persist(report, tmp_path)

    expected = tmp_path / "report" / "53AEED5A8E4EBBB2" / "latest.json"
    assert str(expected) in written
    assert expected.exists()

    loaded = load_bot(tmp_path, "CEX", "ETH", "53AEED5A8E4EBBB2")
    assert loaded["recommendation"]["verdict"] == "DRAWDOWN: HIGH · QUALITY: WEAK"

    index = json.loads((tmp_path / "report" / "index.json").read_text("utf-8"))
    assert index["bots_assessed"] == 1
    assert index["bots"][0]["unique_code"] == "53AEED5A8E4EBBB2"


def test_rows_without_a_verdict_are_not_written_as_assessments(tmp_path):
    broken = _row(rank=2, verdict=None, error="NO_LEDGER")
    report = type("Report", (), {"generated_at_ms": 1, "rows": [broken]})()
    written = persist(report, tmp_path)

    assert written == [str(tmp_path / "report" / "index.json")]
    assert load_bot(tmp_path, "CEX", "ETH", "53AEED5A8E4EBBB2") is None


def test_a_dex_slot_is_filed_under_the_slot_not_the_traded_instrument(tmp_path):
    """The payload records the slot it was picked for (DEX/WETH), not the
    instrument its ledger names (ETH) -- even though the unified layout
    (one folder per bot_id, see assessment_store.py's module docstring) no
    longer segregates the FILE itself by venue/asset, so `load_bot` finds the
    same document regardless of which venue_type/symbol it is called with.
    """
    selection = tmp_path / "universe" / "bot_selection.json"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "venue": "DEX",
                        "symbol": "WETH",
                        "underlying": "ETH",
                        "top": {"code": "53AEED5A8E4EBBB2"},
                        "mid": {"code": "OTHER"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    report = type("Report", (), {"generated_at_ms": 1, "rows": [_row()]})()

    persist(report, tmp_path)

    assert load_bot(tmp_path, "DEX", "WETH", "53AEED5A8E4EBBB2") is not None

    document = load_bot(tmp_path, "DEX", "WETH", "53AEED5A8E4EBBB2")
    assert document["bot"]["slot"] == "DEX/WETH"
    assert document["bot"]["traded_symbol"] == "ETH"


def test_a_bot_that_loses_more_per_loss_than_it_wins_says_so_in_plain_terms():
    text = "\n\n".join(
        build_assessment(_row(payoff_ratio=0.2, win_rate=77.0), 1)["recommendation"][
            "text"
        ]
    )
    assert "payoff 0.20 → one losing trade erases 5.0 winning trades" in text


# --------------------------------------------------------------------------- #
# Việc 1/Việc 4 -- strategy/behavioural extras and the narrative field
# `run_report.py` now wires into every assessment.json (see
# `build_assessment`/`build_assessments`/`persist`'s own docstrings for the
# full design: `row` alone cannot carry these fields, off-limits cohort.py
# schema, so they arrive via `strategy_extra`/`behavioral_extra`/
# `narrative_text` instead).
# --------------------------------------------------------------------------- #

from Agent.backend.report.qc.reporting.assessment_store import build_assessments  # noqa: E402


def test_build_assessment_without_extras_degrades_new_fields_to_none():
    """Every pre-existing caller (no extras passed) must keep working --
    the new keys appear (so a reader can rely on their presence) but hold
    `None`/empty, never a fabricated guess.
    """
    payload = build_assessment(_row(), 1)
    bang_chung = payload["evidence"]
    assert bang_chung["observed_profile"] is None
    assert bang_chung["declared_strategy"] is None
    assert bang_chung["entry_style_evidence"] is None
    assert bang_chung["tested_in_trend"] is None
    assert bang_chung["phase_breakdown"] == []
    assert bang_chung["behavioral_risk_tier"] is None
    assert bang_chung["martingale_escalation_detected"] is None
    assert payload["expert_assessment"] is None
    # Fields `row` DOES carry directly are untouched by the missing extras.
    assert bang_chung["directional_bias"] == "TWO_WAY"
    assert bang_chung["best_phase"] == "UPTREND_VOLATILE"
    # The chart/table-restoring fix (closed_trade_series/horizon_scenarios/
    # assets) degrades exactly like every other extra above: present, `[]`,
    # never a fabricated guess.
    assert bang_chung["closed_trade_series"] == []
    assert bang_chung["assets"] == []
    assert payload["simulation"]["horizon_scenarios"] == []
    assert payload["schema_version"] == "bot_assessment.v3"


def test_build_assessment_merges_closed_trade_series_horizon_scenarios_and_assets():
    """The three fields that fix the "file-sourced page is stuck at 5
    <svg>/8 <details>" gap (see this module's own docstring on
    `build_assessment`) round-trip through `bang_chung`/`mo_phong` exactly
    as given -- no reshaping, no key renaming.
    """
    closed_trade_series = [
        {"close_time": 1_700_000_000_000, "realized_pnl": 12.5},
        {"close_time": 1_700_003_600_000, "realized_pnl": -4.0},
    ]
    horizon_scenarios = [
        {
            "label": "SHORT",
            "horizon_trades": 5,
            "probability_of_profit": 90.0,
            "p_loss_after_horizon": 10.0,
            "p_ruin": 0.0,
        },
        {
            "label": "MEDIUM",
            "horizon_trades": 50,
            "probability_of_profit": 85.0,
            "p_loss_after_horizon": 15.0,
            "p_ruin": 0.01,
        },
    ]
    assets = [
        {
            "asset": "ETH",
            "state": "ĐANG GIAO DỊCH",
            "open_positions": 0,
            "closed_seen": 2,
            "last_close_days": 0.1,
        }
    ]
    payload = build_assessment(
        _row(),
        1,
        closed_trade_series=closed_trade_series,
        horizon_scenarios=horizon_scenarios,
        assets=assets,
    )
    assert payload["evidence"]["closed_trade_series"] == closed_trade_series
    assert payload["evidence"]["assets"] == assets
    assert payload["simulation"]["horizon_scenarios"] == horizon_scenarios
    assert payload["schema_version"] == "bot_assessment.v3"


def test_an_old_v1_shaped_document_still_reads_back_without_the_new_charts():
    """Regression guard for the OTHER half of the contract: a genuinely OLD
    file on disk (no `closed_trade_series`/`horizon_scenarios`/`assets` at
    all, not even as `[]` -- `build_assessment` itself never produces this
    shape anymore, but files written before this fix are exactly this
    shape) must still round-trip through `assessment_to_analyze_result`
    (data.py) without raising, degrading only the three new fields to
    empty. See `Agent/none/test/test_web_app.py`'s
    `test_bot_report_from_assessment_file_has_full_sections_and_charts` for
    the same proof at the full HTTP-response level.
    """
    from Agent.backend.web.data import assessment_to_analyze_result

    doc = build_assessment(_row(), 1)
    # Simulate a genuinely old file: delete the keys entirely, not just
    # empty them -- `dict.get(...)` must degrade the same way for "key
    # missing" as it does for "key present but []".
    del doc["evidence"]["closed_trade_series"]
    del doc["evidence"]["assets"]
    del doc["simulation"]["horizon_scenarios"]
    doc["schema_version"] = "bot_assessment.v1"

    result = assessment_to_analyze_result(doc)
    assert result is not None
    assert result["evidence"]["closed_trade_series"] == []
    assert result["assets"] == []
    assert result["mc"]["horizon_scenarios"] == []
    # Everything else keeps working -- the missing keys degrade in
    # isolation, they do not take down the rest of the reshape.
    assert result["risk"] == _row().risk_score


def test_build_assessment_merges_strategy_and_behavioral_extras():
    strategy_extra = {
        "observed_profile": "DayTrading",
        "declared_strategy": "Grid bot",
        "entry_style_evidence": "7/28 lệnh mở thuận chiều biến động 24h trước đó",
        "tested_in_trend": True,
        "phase_breakdown": [
            {"phase": "UPTREND_VOLATILE", "trades": 15, "total_pnl": 9857.0}
        ],
    }
    behavioral_extra = {
        "martingale_escalation_detected": False,
        "averaging_down_detected": True,
        "loss_chasing_score": 0.42,
        "overtrading_score": 0.1,
        "reentry_loop_detected": False,
        "size_escalation_score": 0.0,
        "leverage_escalation_detected": True,
        "behavioral_risk_tier": "HIGH",
    }
    payload = build_assessment(
        _row(),
        1,
        strategy_extra=strategy_extra,
        behavioral_extra=behavioral_extra,
        narrative_text="Bot này đánh ngược đà, thiên về hai chiều khá cân bằng.",
    )
    bang_chung = payload["evidence"]
    assert bang_chung["observed_profile"] == "DayTrading"
    assert bang_chung["declared_strategy"] == "Grid bot"
    assert bang_chung["tested_in_trend"] is True
    assert bang_chung["phase_breakdown"] == strategy_extra["phase_breakdown"]
    assert bang_chung["averaging_down_detected"] is True
    assert bang_chung["leverage_escalation_detected"] is True
    assert bang_chung["behavioral_risk_tier"] == "HIGH"
    assert payload["expert_assessment"] == (
        "Bot này đánh ngược đà, thiên về hai chiều khá cân bằng."
    )


def test_persist_write_false_builds_payloads_without_touching_disk(tmp_path):
    """`run_report.py --no-write`'s own contract: every payload (narrative
    included) is still fully built and returned/inspectable, but nothing
    lands on disk.
    """
    report = type(
        "Report", (), {"generated_at_ms": 1_789_000_000_000, "rows": [_row()]}
    )()
    extra_by_code = {
        "53AEED5A8E4EBBB2": {
            "strategy": {"observed_profile": "DayTrading"},
            "behavioral": {"behavioral_risk_tier": "LOW"},
            "narrative": "Bot này chơi kiểu day-trading hai chiều.",
        }
    }
    written = persist(report, tmp_path, extra_by_code=extra_by_code, write=False)

    expected = tmp_path / "report" / "53AEED5A8E4EBBB2" / "latest.json"
    assert str(expected) in written
    assert not expected.exists()
    assert not (tmp_path / "report" / "index.json").exists()

    # The narrative built for this exact run is still recoverable via
    # build_assessments, without any file having been written.
    built = build_assessments(report, tmp_path, extra_by_code=extra_by_code)
    assert len(built) == 1
    path, payload = built[0]
    assert path == expected
    assert payload["expert_assessment"] == "Bot này chơi kiểu day-trading hai chiều."
    assert payload["evidence"]["observed_profile"] == "DayTrading"


def test_persist_write_true_is_unaffected_by_the_new_optional_parameters(tmp_path):
    """Backward-compatibility check: calling `persist()` exactly like every
    pre-existing caller (no `extra_by_code`, no `write`) must still write to
    disk -- the new parameters only ever ADD behaviour, opt-in.
    """
    report = type("Report", (), {"generated_at_ms": 1, "rows": [_row()]})()
    written = persist(report, tmp_path)
    expected = tmp_path / "report" / "53AEED5A8E4EBBB2" / "latest.json"
    assert expected.exists()
    assert str(expected) in written


# --------------------------------------------------------------------------- #
# Việc 2/3 -- `observed_symbols`/`symbol_exposure_share`/`primary_share_pct`/
# `secondary_market`. Unlike strategy/behavioral extras above, these come
# straight off `row` itself (`BotEvaluationRow.exposure_share`/
# `secondary_*`, cohort.py) -- no `extra_by_code` plumbing needed, so every
# pre-existing `build_assessment(row, ...)` call (no new kwargs) already
# exercises this path.
# --------------------------------------------------------------------------- #


def test_build_assessment_degrades_symbol_exposure_fields_to_empty_when_row_has_none():
    """`_row()` sets no `exposure_share`/`secondary_*` override -- matches a
    bot whose `bot.identity.symbol_exposure_share` came back empty (no
    notional on any closed trade). `{}`/`None`, never a fabricated guess.
    """
    payload = build_assessment(_row(), 1)
    bang_chung = payload["evidence"]
    assert bang_chung["observed_symbols"] == []
    assert bang_chung["symbol_exposure_share"] == {}
    assert bang_chung["primary_share_pct"] is None
    assert bang_chung["secondary_market"] is None


def test_build_assessment_writes_symbol_exposure_and_secondary_market_from_row():
    """`row.exposure_share`/`row.secondary_*` (cohort.py, computed from
    `bot.identity.symbol_exposure_share` --
    Agent/backend/mcp/service.py::_resolve_identity_market -- at scan time)
    round-trip into `bang_chung` verbatim: `observed_symbols` sorted by
    exposure descending, `primary_share_pct` the CURRENT `row.traded_symbol`'s
    own share (0-100, rounded), `secondary_market` the compact dict
    `report_page.py` renders directly.
    """
    from Agent.backend.report.qc.reporting.cohort import MarketSnapshotRow

    row = _row(
        traded_symbol="ETH",
        exposure_share={"ETH": 0.6, "SOL": 0.25, "BTC": 0.15},
        secondary_traded_symbol="SOL",
        secondary_share_pct=25.0,
        secondary_market=MarketSnapshotRow(
            symbol="SOL",
            venue_type="CEX",
            trend="BULLISH",
            volatility="NORMAL",
            liquidity_tier="DEEP",
            flow_bias="BUY_PRESSURE",
            last_price=150.0,
            data_quality=0.9,
        ),
    )
    payload = build_assessment(row, 1)
    bang_chung = payload["evidence"]
    assert bang_chung["observed_symbols"] == ["ETH", "SOL", "BTC"]
    assert bang_chung["symbol_exposure_share"] == {"ETH": 0.6, "SOL": 0.25, "BTC": 0.15}
    assert bang_chung["primary_share_pct"] == 60.0
    assert bang_chung["secondary_market"] == {
        "symbol": "SOL",
        "share_pct": 25.0,
        "venue_type": "CEX",
        "trend": "BULLISH",
        "volatility": "NORMAL",
        "liquidity_tier": "DEEP",
        "flow_bias": "BUY_PRESSURE",
        "last_price": 150.0,
    }


def test_an_old_document_without_symbol_exposure_fields_still_reads_back():
    """A genuinely old assessment.json (written before Việc 2/3 -- no
    `observed_symbols`/`symbol_exposure_share`/`primary_share_pct`/
    `secondary_market` at all in `bang_chung`) must still round-trip through
    `assessment_to_analyze_result` -- degrade only, never raise.
    """
    from Agent.backend.web.data import assessment_to_analyze_result

    doc = build_assessment(_row(), 1)
    del doc["evidence"]["observed_symbols"]
    del doc["evidence"]["symbol_exposure_share"]
    del doc["evidence"]["primary_share_pct"]
    del doc["evidence"]["secondary_market"]

    result = assessment_to_analyze_result(doc)
    assert result is not None
    evidence = result["evidence"]
    assert evidence["observed_symbols"] == []
    assert evidence["symbol_exposure_share"] == {}
    assert evidence["primary_share_pct"] is None
    assert evidence["secondary_market"] is None


# --------------------------------------------------------------------------- #
# Phủ sóng theo mục tiêu (Agent/backend/market/coverage.py) --
# `row.resolved_markets`/`unresolved_markets`/`coverage_achieved_pct`
# (cohort.py/pipeline.py) round-trip vào `bang_chung` giống hệt cách bốn
# khoá Việc 2/3 ở trên đã làm -- không đi qua `extra_by_code`.
# --------------------------------------------------------------------------- #


def test_build_assessment_degrades_market_coverage_fields_to_empty_when_row_has_none():
    """`_row()` không đặt `resolved_markets`/`unresolved_markets` -- khớp
    một bot chỉ giải được thị trường CHÍNH qua đường cũ (hoặc file trước
    đợt phủ sóng theo mục tiêu này)."""
    payload = build_assessment(_row(), 1)
    bang_chung = payload["evidence"]
    assert bang_chung["resolved_markets"] == []
    assert bang_chung["unresolved_markets"] == []
    assert bang_chung["coverage_achieved_pct"] is None


def test_build_assessment_writes_market_coverage_from_row():
    """`row.resolved_markets`/`unresolved_markets`/`coverage_achieved_pct`
    (cohort.py, tính từ `plan_market_coverage`/`resolve_planned_markets`)
    round-trip nguyên vẹn vào `bang_chung`."""
    from Agent.backend.report.qc.reporting.cohort import (
        CoveredMarketRow,
        MarketSnapshotRow,
        UncoveredMarketRow,
    )

    row = _row(
        exposure_share={"ETH": 0.6, "SOL": 0.25, "BTC": 0.15},
        resolved_markets=[
            CoveredMarketRow(
                symbol="ETH",
                share_pct=60.0,
                market=MarketSnapshotRow(
                    symbol="ETH",
                    venue_type="CEX",
                    trend="BULLISH",
                    volatility="NORMAL",
                    liquidity_tier="DEEP",
                    flow_bias="BUY_PRESSURE",
                    last_price=3000.0,
                    data_quality=0.9,
                ),
            ),
            CoveredMarketRow(
                symbol="SOL",
                share_pct=25.0,
                market=MarketSnapshotRow(
                    symbol="SOL",
                    venue_type="CEX",
                    trend="BEARISH",
                    volatility="HIGH",
                    liquidity_tier="SHALLOW",
                    flow_bias="SELL_PRESSURE",
                    last_price=150.0,
                    data_quality=0.8,
                ),
            ),
        ],
        unresolved_markets=[
            UncoveredMarketRow(
                symbol="BTC", share_pct=15.0, reason="NO_MARKET_DATA_FOR_TRADED_SYMBOL"
            ),
        ],
        coverage_achieved_pct=85.0,
    )
    payload = build_assessment(row, 1)
    bang_chung = payload["evidence"]
    assert bang_chung["resolved_markets"] == [
        {
            "symbol": "ETH",
            "share_pct": 60.0,
            "venue_type": "CEX",
            "trend": "BULLISH",
            "volatility": "NORMAL",
            "liquidity_tier": "DEEP",
            "flow_bias": "BUY_PRESSURE",
            "last_price": 3000.0,
        },
        {
            "symbol": "SOL",
            "share_pct": 25.0,
            "venue_type": "CEX",
            "trend": "BEARISH",
            "volatility": "HIGH",
            "liquidity_tier": "SHALLOW",
            "flow_bias": "SELL_PRESSURE",
            "last_price": 150.0,
        },
    ]
    assert bang_chung["unresolved_markets"] == [
        {
            "symbol": "BTC",
            "share_pct": 15.0,
            "reason": "NO_MARKET_DATA_FOR_TRADED_SYMBOL",
        }
    ]
    assert bang_chung["coverage_achieved_pct"] == 85.0


def test_an_old_document_without_market_coverage_fields_still_reads_back():
    """File ghi TRƯỚC đợt phủ sóng theo mục tiêu (không có
    `resolved_markets`/`unresolved_markets`/`coverage_achieved_pct` trong
    `bang_chung`) phải vẫn round-trip qua `assessment_to_analyze_result` --
    degrade only, never raise."""
    from Agent.backend.web.data import assessment_to_analyze_result

    doc = build_assessment(_row(), 1)
    del doc["evidence"]["resolved_markets"]
    del doc["evidence"]["unresolved_markets"]
    del doc["evidence"]["coverage_achieved_pct"]

    result = assessment_to_analyze_result(doc)
    assert result is not None
    evidence = result["evidence"]
    assert evidence["resolved_markets"] == []
    assert evidence["unresolved_markets"] == []
    assert evidence["coverage_achieved_pct"] is None


# --------------------------------------------------------------------------- #
# `index.json` -- hợp nhất thay vì ghi đè, và dựng lại từ đĩa.
#
# Lỗi ngày 19/09: `persist` dựng lại index từ đúng tập bot của LƯỢT CHẠY
# hiện tại. Lượt chấm cả đàn thì đó là toàn bộ, nên không ai thấy gì. Nhưng
# nút "Re-analyze" chạy lại MỘT bot cũng đi qua đây, và khi đó index bị cắt
# từ cả đàn xuống một hàng. Web không lộ (trang danh sách duyệt thẳng thư
# mục), MCP thì chết: `list_assessed_bots`/`get_assessment` đọc index, nên
# 30/31 bot bị báo "chưa được chấm". Không test nào bắt được vì mọi test đều
# chỉ persist một lần rồi kiểm.
# --------------------------------------------------------------------------- #


def test_persisting_one_bot_does_not_drop_the_other_bots_from_the_index(tmp_path):
    first = type(
        "Report", (), {"generated_at_ms": 1, "rows": [_row(), _row_other()]}
    )()
    persist(first, tmp_path)
    index = json.loads((tmp_path / "report" / "index.json").read_text("utf-8"))
    assert index["bots_assessed"] == 2

    # Đúng hình dạng lượt chạy lại lẻ: report chỉ mang MỘT bot.
    again = type("Report", (), {"generated_at_ms": 2, "rows": [_row()]})()
    persist(again, tmp_path)

    index = json.loads((tmp_path / "report" / "index.json").read_text("utf-8"))
    assert index["bots_assessed"] == 2, "bot không nằm trong lượt chạy đã bị cắt"
    assert index["bots_this_run"] == 1
    assert {row["unique_code"] for row in index["bots"]} == {
        "53AEED5A8E4EBBB2",
        "0EAF7292CE2FAAC2",
    }


def test_the_index_drops_a_row_whose_file_no_longer_exists(tmp_path):
    """Hợp nhất KHÔNG được biến index thành nơi bot đã xoá sống mãi."""
    report = type(
        "Report", (), {"generated_at_ms": 1, "rows": [_row(), _row_other()]}
    )()
    persist(report, tmp_path)
    gone = json.loads((tmp_path / "report" / "index.json").read_text("utf-8"))
    removed = next(
        row for row in gone["bots"] if row["unique_code"] == "0EAF7292CE2FAAC2"
    )
    # `file` là đường dẫn TƯƠNG ĐỐI so với data_dir (xem
    # `assessment_store._index_relative_path`): index phải dùng chung được
    # giữa host và container, nên không thể lưu đường tuyệt đối.
    removed_path = tmp_path / removed["file"]
    assert removed_path.is_file(), f"không thấy {removed_path}"
    removed_path.unlink()

    persist(type("Report", (), {"generated_at_ms": 2, "rows": [_row()]})(), tmp_path)
    index = json.loads((tmp_path / "report" / "index.json").read_text("utf-8"))
    assert [row["unique_code"] for row in index["bots"]] == ["53AEED5A8E4EBBB2"]


def test_rebuild_index_restores_every_bot_from_the_files_themselves(tmp_path):
    report = type(
        "Report", (), {"generated_at_ms": 1, "rows": [_row(), _row_other()]}
    )()
    persist(report, tmp_path)

    # Cắt index bằng tay, đúng trạng thái lỗi đã tìm thấy trên máy thật.
    index_path = tmp_path / "report" / "index.json"
    broken = json.loads(index_path.read_text("utf-8"))
    broken["bots"] = broken["bots"][:1]
    broken["bots_assessed"] = 1
    index_path.write_text(json.dumps(broken), encoding="utf-8")

    rebuilt = rebuild_index(tmp_path)
    assert rebuilt["bots_assessed"] == 2
    assert rebuilt["rebuilt_from_disk"] is True
    on_disk = json.loads(index_path.read_text("utf-8"))
    assert {row["unique_code"] for row in on_disk["bots"]} == {
        "53AEED5A8E4EBBB2",
        "0EAF7292CE2FAAC2",
    }


# --------------------------------------------------------------------------- #
# `rank_in_cohort` -- thuộc tính của CẢ QUẦN THỂ, không phải của lượt chạy.
# --------------------------------------------------------------------------- #


def test_rank_tier_order_matches_the_cohort_module_it_copies() -> None:
    """`_RANK_TIER_ORDER` là bản sao có chủ ý (tránh vòng import). Lệch bảng
    này thì hạng đọc từ đĩa và hạng của một lượt chấm cả đàn sẽ nói hai điều
    khác nhau -- test này là thứ duy nhất chặn nó trôi."""
    from Agent.backend.report.qc.reporting.assessment_store import _RANK_TIER_ORDER
    from Agent.backend.report.qc.reporting.cohort import TIER_ORDER

    assert {tier.value: order for tier, order in TIER_ORDER.items()} == _RANK_TIER_ORDER


def test_rescoring_one_bot_does_not_give_it_rank_one(tmp_path):
    """Đúng con bug: chấm lại lẻ luôn ra cohort một bot, nên `row.rank` là 1
    với mọi bot. Trên đĩa đã từng có HAI bot cùng hạng 1."""
    both = type(
        "Report", (), {"generated_at_ms": 1, "rows": [_row(), _row_other()]}
    )()
    persist(both, tmp_path)
    ranks = _ranks_on_disk(tmp_path)
    assert sorted(ranks.values()) == [1, 2]
    worse_bot = min(ranks, key=lambda code: ranks[code])

    # Chạy lại MỘT bot -- bot xếp sau, nên nếu hạng bị bịa nó sẽ nhảy lên 1.
    loser = next(code for code in ranks if code != worse_bot)
    only = _row() if loser == "53AEED5A8E4EBBB2" else _row_other()
    persist(type("Report", (), {"generated_at_ms": 2, "rows": [only]})(), tmp_path)

    after = _ranks_on_disk(tmp_path)
    assert sorted(after.values()) == [1, 2], f"hạng trùng hoặc hụt: {after}"
    assert after == ranks, "chạy lại một bot không được đổi thứ hạng của cả đàn"


def test_renumber_ranks_orders_by_tier_then_risk_score(tmp_path):
    from Agent.backend.report.qc.reporting.assessment_store import renumber_ranks

    safe = _row_other(risk_score=10.0, risk_tier="HEALTHY", rank=99)
    risky = _row(risk_score=90.0, risk_tier="CRITICAL", rank=99)
    persist(type("Report", (), {"generated_at_ms": 1, "rows": [safe, risky]})(), tmp_path)

    renumber_ranks(tmp_path)
    ranks = _ranks_on_disk(tmp_path)
    assert ranks[risky.unique_code] == 1, "bot rủi ro hơn phải đứng trước"
    assert ranks[safe.unique_code] == 2


def _ranks_on_disk(tmp_path) -> dict:
    out = {}
    for path in (tmp_path / "report").glob("*/latest.json"):
        doc = json.loads(path.read_text("utf-8"))
        out[doc["bot"]["unique_code"]] = doc["bot"]["rank_in_cohort"]
    return out
