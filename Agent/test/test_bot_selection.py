"""The paired sample must never overstate what the leaderboard actually offers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from Agent.scripts.select_bots import (
    ACTIVE_WITHIN_DAYS,
    ASSET_UNIVERSE,
    EVIDENCE_LADDER,
    NO_SECOND_BOT,
    WEAKER_PERFORMER,
    select,
)

NOW_MS = 1_789_300_000_000
DAY_MS = 86_400_000


def _universe(tmp_path: Path, records: List[Dict[str, Any]]):
    """Each record: rank, plus {asset: closed_trade_count} and optional staleness."""
    traders, activity = [], {}
    for record in records:
        code = f"C{record['rank']}"
        traders.append(
            {
                "uniqueCode": code,
                "rank": record["rank"],
                "nickName": code,
                # ROI decides the pair, so default it to mirror rank unless overridden.
                "pnlRatio": record.get("roi", (300 - record["rank"]) / 100.0),
            }
        )
        closed = record.get("last_close_days_ago", 0)
        activity[code] = {
            "uniqueCode": code,
            "rank": record["rank"],
            "nickName": code,
            "per_asset": {
                asset: {"trades": n, "notional": n * 1000.0}
                for asset, n in (record.get("assets") or {}).items()
            },
            "open_assets": record.get("open_assets") or {},
            "open_positions": record.get("open_positions", 0),
            # A bot needs a real ledger before anything is measurable; cases that
            # do not care about ledger size get one comfortably over the bar.
            "history_sample": record.get("total_trades", 100),
            "last_close_ms": None if closed is None else NOW_MS - closed * DAY_MS,
        }
    board = tmp_path / "lead_traders.json"
    act = tmp_path / "trader_activity.json"
    board.write_text(json.dumps(traders), encoding="utf-8")
    act.write_text(json.dumps(activity), encoding="utf-8")
    return board, act


def _select(tmp_path, records, universe, **kwargs):
    board, act = _universe(tmp_path, records)
    return select(universe, board, act, now_ms=NOW_MS, **kwargs)


def test_the_leader_is_the_better_performer_not_the_better_rank(tmp_path):
    """Board rank reshuffles daily and does not say a bot is doing well."""
    result = _select(
        tmp_path,
        [
            {"rank": 1, "assets": {"BTC": 5}, "roi": 0.065},
            {"rank": 40, "assets": {"BTC": 5}, "roi": 1.05},
            {"rank": 60, "assets": {"BTC": 5}, "roi": 0.02},
            {"rank": 80, "assets": {"BTC": 5}, "roi": 0.01},
        ],
        [("CEX", "BTC", "BTC")],
    )
    btc = result["assets"][0]

    assert btc["top"]["okx_rank"] == 40, "bot lãi nhất phải làm bot dẫn"
    assert btc["mid"]["roi_pct"] < btc["top"]["roi_pct"]
    assert btc["mid_basis"] == WEAKER_PERFORMER


def test_every_pair_puts_the_stronger_bot_first(tmp_path):
    result = _select(
        tmp_path,
        [{"rank": r, "assets": {"BTC": 5, "ETH": 5}} for r in (1, 20, 45, 90)],
        [("CEX", "BTC", "BTC"), ("CEX", "ETH", "ETH")],
    )

    for record in result["assets"]:
        assert record["top"]["roi_pct"] > record["mid"]["roi_pct"]


def test_a_losing_bot_never_leads_an_asset(tmp_path):
    result = _select(
        tmp_path,
        [
            {"rank": 1, "assets": {"BTC": 5}, "roi": -0.4},
            {"rank": 70, "assets": {"BTC": 5}, "roi": 0.12},
        ],
        [("CEX", "BTC", "BTC")],
    )

    assert result["assets"][0]["top"]["okx_rank"] == 70


def test_the_draw_is_reproducible_and_seed_dependent(tmp_path):
    records = [{"rank": 1, "assets": {"BTC": 9}}] + [
        {"rank": r, "assets": {"BTC": 5}} for r in range(20, 51)
    ]
    slot = [("CEX", "BTC", "BTC")]

    first = _select(tmp_path, records, slot, seed=7)["assets"][0]["mid"]["code"]
    assert _select(tmp_path, records, slot, seed=7)["assets"][0]["mid"]["code"] == first

    spread = {
        _select(tmp_path, records, slot, seed=s)["assets"][0]["mid"]["code"]
        for s in range(12)
    }
    assert len(spread) > 1, "mid slot is meant to be a random draw, not a fixed pick"


def test_a_bot_only_holding_an_open_position_is_not_a_candidate(tmp_path):
    """No closed trades on the asset means no PnL, no win rate, nothing to assess."""
    result = _select(
        tmp_path,
        [
            {"rank": 1, "assets": {"BTC": 10}},
            {"rank": 28, "assets": {}, "open_assets": {"BTC": 8}, "open_positions": 8},
            {"rank": 45, "assets": {"BTC": 3}},
        ],
        [("CEX", "BTC", "BTC")],
    )

    assert result["assets"][0]["mid"]["okx_rank"] == 45
    assert "C28" not in result["unique_codes"]


def test_a_bot_that_stopped_trading_is_not_a_candidate(tmp_path):
    stale_days = ACTIVE_WITHIN_DAYS + 5
    result = _select(
        tmp_path,
        [
            {"rank": 1, "assets": {"BTC": 10}, "last_close_days_ago": stale_days},
            {"rank": 3, "assets": {"BTC": 10}},
            {"rank": 30, "assets": {"BTC": 4}},
        ],
        [("CEX", "BTC", "BTC")],
    )

    assert result["assets"][0]["top"]["okx_rank"] == 3, "bot ngủ không được làm top"


def test_a_bot_with_an_open_book_counts_as_active_even_without_a_recent_close(tmp_path):
    result = _select(
        tmp_path,
        [
            {
                "rank": 1,
                "assets": {"BTC": 10},
                "last_close_days_ago": ACTIVE_WITHIN_DAYS + 30,
                "open_positions": 4,
            },
            {"rank": 30, "assets": {"BTC": 4}},
        ],
        [("CEX", "BTC", "BTC")],
    )

    assert result["assets"][0]["top"]["okx_rank"] == 1


def test_single_candidate_asset_yields_no_second_bot(tmp_path):
    result = _select(
        tmp_path, [{"rank": 65, "assets": {"AVAX": 2}}], [("CEX", "AVAX", "AVAX")]
    )
    avax = result["assets"][0]

    assert avax["top"]["okx_rank"] == 65
    assert avax["mid"] is None
    assert avax["mid_basis"] == NO_SECOND_BOT


def test_asset_nobody_trades_is_reported_empty_not_filled_in(tmp_path):
    result = _select(
        tmp_path,
        [{"rank": 1, "assets": {"BTC": 10}}, {"rank": 25, "assets": {"BTC": 5}}],
        [("CEX", "BTC", "BTC"), ("CEX", "LINK", "LINK")],
    )
    link = result["assets"][1]

    assert link["candidates"] == 0
    assert link["top"] is None and link["mid"] is None


def test_two_slots_on_one_underlying_get_four_different_bots(tmp_path):
    """The pair exists to be compared, so a reused bot would compare a bot to itself."""
    result = _select(
        tmp_path,
        [{"rank": r, "assets": {"BTC": 5}} for r in (3, 6, 34, 86)],
        [("CEX", "BTC", "BTC"), ("DEX", "WBTC", "BTC")],
    )

    assert len(result["unique_codes"]) == 4
    for record in result["assets"]:
        assert record["top"]["code"] != record["mid"]["code"]


def test_a_thin_asset_keeps_its_bots_against_a_deep_one(tmp_path):
    # C46 and C66 are the only bots trading AVAX and both also trade BTC, which has
    # plenty of alternatives. Allocating BTC first would leave AVAX unpairable.
    result = _select(
        tmp_path,
        [
            {"rank": 46, "assets": {"AVAX": 2, "BTC": 9}},
            {"rank": 66, "assets": {"AVAX": 1, "BTC": 9}},
            {"rank": 80, "assets": {"BTC": 9}},
            {"rank": 90, "assets": {"BTC": 9}},
        ],
        [("CEX", "BTC", "BTC"), ("CEX", "AVAX", "AVAX")],
    )
    btc, avax = result["assets"]

    assert {avax["top"]["okx_rank"], avax["mid"]["okx_rank"]} == {46, 66}
    assert {btc["top"]["okx_rank"], btc["mid"]["okx_rank"]} == {80, 90}


def test_every_bot_in_the_selection_is_used_once():
    import json as _json
    from pathlib import Path as _Path

    path = _Path("Agent/data/universe/bot_selection.json")
    if not path.exists():
        return
    selection = _json.loads(path.read_text(encoding="utf-8"))
    picks = [
        record[slot]["code"]
        for record in selection["assets"]
        for slot in ("top", "mid")
        if record[slot]
    ]

    assert len(picks) == len(set(picks)), "một bot bị dùng cho nhiều slot"
    assert len(picks) == 2 * len(selection["assets"])


def test_the_working_universe_is_ten_cex_plus_five_dex():
    venues = [venue for venue, _, _ in ASSET_UNIVERSE]

    assert venues.count("CEX") == 10
    assert venues.count("DEX") == 5
    assert {s for v, s, _ in ASSET_UNIVERSE if v == "DEX"} == {
        "WBTC",
        "WETH",
        "SOL",
        "UNI",
        "PEPE",
    }


def test_a_bot_with_too_thin_a_ledger_is_not_a_candidate(tmp_path):
    """Market history runs from 2023; a dozen fills cannot carry a risk verdict."""
    floor_total = EVIDENCE_LADDER[-1][0]
    result = _select(
        tmp_path,
        [
            {"rank": 1, "assets": {"BTC": 9}, "total_trades": floor_total - 1},
            {"rank": 5, "assets": {"BTC": 9}, "total_trades": floor_total},
            {"rank": 40, "assets": {"BTC": 9}, "total_trades": 100},
        ],
        [("CEX", "BTC", "BTC")],
    )

    assert result["assets"][0]["top"]["okx_rank"] == 5
    assert "C1" not in result["unique_codes"]


def test_the_evidence_bar_steps_down_only_for_an_asset_that_cannot_meet_it(tmp_path):
    best_total, best_on_asset = EVIDENCE_LADDER[0]
    result = _select(
        tmp_path,
        [
            # BTC can satisfy the top bar; AVAX has only one-fill traders.
            {"rank": 1, "assets": {"BTC": best_on_asset, "AVAX": 1}},
            {"rank": 2, "assets": {"BTC": best_on_asset}},
            {"rank": 3, "assets": {"BTC": best_on_asset}},
            {"rank": 4, "assets": {"BTC": best_on_asset}},
            {"rank": 5, "assets": {"AVAX": 1}},
            {"rank": 6, "assets": {"AVAX": 1}},
        ],
        [("CEX", "BTC", "BTC"), ("CEX", "AVAX", "AVAX")],
    )
    btc, avax = result["assets"]

    assert btc["evidence_bar"]["min_total_trades"] == best_total
    assert btc["evidence_bar"]["min_trades_on_asset"] == best_on_asset
    assert avax["evidence_bar"]["min_trades_on_asset"] == EVIDENCE_LADDER[-1][1]
    assert avax["top"] and avax["mid"]
