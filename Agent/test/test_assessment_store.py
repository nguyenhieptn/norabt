"""Step 3's verdict has to be readable one bot at a time, text included."""

from __future__ import annotations

import json

from Agent.backend.qc.reporting.assessment_store import (
    build_assessment,
    load_bot,
    persist,
)
from Agent.backend.qc.reporting.cohort import BotEvaluationRow


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
        verdict="NGUY HIỂM",
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
        conclusion="NGUY HIỂM",
    )
    base.update(overrides)
    return BotEvaluationRow(**base)


def test_assessment_leads_with_the_text_and_keeps_the_numbers():
    payload = build_assessment(_row(), 1_789_000_000_000)
    paragraphs = payload["khuyen_nghi"]["text"]

    joined = payload["khuyen_nghi"]["text_full"]
    assert joined == "\n\n".join(paragraphs)

    # The argument comes first and is the long part: it is what has to
    # convince. Everything after it is evidence to be checked against it.
    assert paragraphs[1].startswith("NGUYÊN NHÂN TẠI SAO:")
    assert len(paragraphs[1]) == max(len(p) for p in paragraphs)
    # A verdict a reader will only glance at for a few seconds cannot afford
    # a paragraph that keeps arguing past the point it already made.
    assert len(paragraphs[1]) <= 350
    assert "0.16" in paragraphs[1] and "86,132" in paragraphs[1]
    assert "chốt lời sớm" in paragraphs[1]

    # Then the proof, as bullets a reader can scan rather than a wall of prose.
    assert "CHỨNG MINH:" in paragraphs
    bullets = [p for p in paragraphs if p.startswith("• ")]
    assert len(bullets) <= 6
    assert all(len(b) < 160 for b in bullets)

    assert paragraphs[-1].startswith("KẾT LUẬN:")
    for fragment in ("payoff 1.02", "Monte Carlo 10,000 kịch bản"):
        assert fragment in joined
    # The whole verdict has to stay a quick read, not just each piece of it.
    assert 600 <= len(joined) <= 1100
    assert payload["cham_diem"]["veto_reasons"]
    assert payload["mo_phong"]["scope"] == "CHI_LENH_DA_CHOT"


def test_tail_that_stays_profitable_is_not_reported_as_a_loss():
    profitable = "\n\n".join(build_assessment(_row(), 1)["khuyen_nghi"]["text"])
    assert "đuôi 5% tệ nhất vẫn lãi 5.5%" in profitable

    losing = "\n\n".join(
        build_assessment(_row(cvar_95_pct=12.0), 1)["khuyen_nghi"]["text"]
    )
    assert "đuôi 5% tệ nhất lỗ 12.0%" in losing


def test_persist_mirrors_the_step_2_layout_and_reads_back(tmp_path):
    report = type(
        "Report", (), {"generated_at_ms": 1_789_000_000_000, "rows": [_row()]}
    )()
    written = persist(report, tmp_path)

    expected = (
        tmp_path
        / "assessment"
        / "cex"
        / "ETH"
        / "bot"
        / "HaveARestin__53AEED5A8E4EBBB2"
        / "assessment.json"
    )
    assert str(expected) in written
    assert expected.exists()

    loaded = load_bot(tmp_path, "CEX", "ETH", "53AEED5A8E4EBBB2")
    assert loaded["khuyen_nghi"]["ket_luan"] == "NGUY HIỂM"

    index = json.loads((tmp_path / "assessment" / "index.json").read_text("utf-8"))
    assert index["bots_assessed"] == 1
    assert index["bots"][0]["unique_code"] == "53AEED5A8E4EBBB2"


def test_rows_without_a_verdict_are_not_written_as_assessments(tmp_path):
    broken = _row(rank=2, verdict=None, error="NO_LEDGER")
    report = type("Report", (), {"generated_at_ms": 1, "rows": [broken]})()
    written = persist(report, tmp_path)

    assert written == [str(tmp_path / "assessment" / "index.json")]
    assert load_bot(tmp_path, "CEX", "ETH", "53AEED5A8E4EBBB2") is None


def test_a_dex_slot_is_filed_under_the_slot_not_the_traded_instrument(tmp_path):
    """Every DEX slot is filled by an OKX trader, so the two names differ."""
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

    # Filed by slot, not by the ETH its ledger names, so the DEX side of the
    # tree is not silently empty.
    assert load_bot(tmp_path, "DEX", "WETH", "53AEED5A8E4EBBB2") is not None
    assert load_bot(tmp_path, "CEX", "ETH", "53AEED5A8E4EBBB2") is None

    document = load_bot(tmp_path, "DEX", "WETH", "53AEED5A8E4EBBB2")
    assert document["bot"]["slot"] == "DEX/WETH"
    assert document["bot"]["traded_symbol"] == "ETH"


def test_a_bot_that_loses_more_per_loss_than_it_wins_says_so_in_plain_terms():
    text = "\n\n".join(
        build_assessment(_row(payoff_ratio=0.2, win_rate=77.0), 1)["khuyen_nghi"][
            "text"
        ]
    )
    assert "payoff 0.20 → một lệnh thua xoá 5.0 lệnh thắng" in text
