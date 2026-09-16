"""Step 2's output is step 3's input, so it has to be readable one bot at a time."""

from __future__ import annotations

import json
from types import SimpleNamespace

from Agent.backend.qc.reporting.analysis_store import (
    folder_name,
    load_bot,
    persist,
)


def _bot(code: str, name: str, error=None):
    return SimpleNamespace(
        unique_code=code,
        nick_name=name,
        error=error,
        model_dump=lambda mode=None: {
            "role": "CHẠY NGON",
            "nick_name": name,
            "unique_code": code,
            "trade_count": 143,
            "profit_factor": 11.12,
            "marked_profit_factor": 0.16,
            "mc_iterations": 10_000,
            "mc_horizon": 143,
            "mc_profit_worst_pct": 3.3,
            "psr": 0.99,
            "deflated_sharpe": 0.95,
        },
    )


def _report(bots):
    return SimpleNamespace(
        generated_at_ms=1_789_000_000_000,
        slots=1,
        bots_evaluated=len(bots),
        bots_failed=0,
        blocks=[
            SimpleNamespace(
                venue_type="CEX",
                symbol="XRP",
                underlying="XRP",
                market_available=True,
                market_posture="RỦI RO",
                market_evidence=["xu hướng giảm"],
                market_trend="BEARISH",
                market_volatility="NORMAL",
                market_liquidity="ADEQUATE",
                market_quality=1.0,
                market_error=None,
                bots=bots,
                comparison=["so sánh"],
            )
        ],
    )


def test_an_asset_gets_a_market_folder_and_one_folder_per_bot(tmp_path):
    persist(_report([_bot("AAA", "HaveARestin"), _bot("BBB", "Milies L")]), tmp_path)
    asset = tmp_path / "analysis" / "cex" / "XRP"

    assert (asset / "market" / "market.json").exists()
    bot_dirs = sorted(p.name for p in (asset / "bot").iterdir())
    assert bot_dirs == ["HaveARestin__AAA", "Milies-L__BBB"]


def test_each_bot_folder_holds_performance_and_monte_carlo_separately(tmp_path):
    """Two questions, two files: what it did, and what could happen next."""
    persist(_report([_bot("AAA", "HaveARestin")]), tmp_path)
    bot_dir = tmp_path / "analysis" / "cex" / "XRP" / "bot" / "HaveARestin__AAA"

    performance = json.loads((bot_dir / "performance.json").read_text())
    simulation = json.loads((bot_dir / "monte_carlo.json").read_text())

    assert performance["step"] == "2.2_HIEU_SUAT"
    assert performance["profit_factor"] == 11.12
    assert "mc_iterations" not in performance

    assert simulation["step"] == "2.2_MONTE_CARLO"
    assert simulation["scope"] == "CHI_LENH_DA_CHOT"
    assert simulation["mc_iterations"] == 10_000
    assert "profit_factor" not in simulation


def test_a_bot_is_found_by_code_even_though_the_folder_carries_its_name(tmp_path):
    """Names change between crawls; the code is what step 3 looks up."""
    persist(_report([_bot("AAA", "HaveARestin")]), tmp_path)

    loaded = load_bot(tmp_path, "CEX", "XRP", "AAA")

    assert loaded is not None
    assert loaded["performance"]["unique_code"] == "AAA"
    assert loaded["monte_carlo"]["mc_horizon"] == 143


def test_a_bot_that_failed_analysis_is_not_written_as_if_it_had_data(tmp_path):
    persist(_report([_bot("AAA", "Broken", error="chưa crawl")]), tmp_path)

    assert not (tmp_path / "analysis" / "cex" / "XRP" / "bot").exists()
    assert load_bot(tmp_path, "CEX", "XRP", "AAA") is None


def test_folder_names_stay_path_safe_for_cjk_and_spaces():
    assert folder_name("AI 量化新星 - 趋势策略", "C1").endswith("__C1")
    assert "/" not in folder_name("a/b", "C1")
    assert " " not in folder_name("Milies L", "C1")
    assert folder_name("", "C1") == "C1"


def test_the_index_says_what_the_files_are_for(tmp_path):
    persist(_report([_bot("AAA", "HaveARestin")]), tmp_path)

    index = json.loads((tmp_path / "analysis" / "index.json").read_text())

    assert index["step"] == "2_PHAN_TICH_MO_PHONG"
    assert "bước 3" in index["note"]
    assert len(index["files"]) >= 3
