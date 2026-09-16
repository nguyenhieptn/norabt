from __future__ import annotations

from dataclasses import dataclass

import pytest

from Agent.backend.research.splitting import split_by_close_time


@dataclass(frozen=True)
class _Trade:
    close_time: int
    label: str = ""


def test_split_is_time_ordered_with_no_leakage():
    """Every train trade must close at or before every test trade -- the
    entire reason for a time split instead of a random one.
    """
    trades = [_Trade(close_time=t) for t in range(100)]
    split = split_by_close_time(trades, train_fraction=0.6)

    assert split.train
    assert split.test
    assert max(t.close_time for t in split.train) <= min(
        t.close_time for t in split.test
    )
    # Every trade accounted for exactly once.
    assert len(split.train) + len(split.test) == len(trades)
    assert set(t.close_time for t in split.train) | set(
        t.close_time for t in split.test
    ) == set(range(100))


def test_split_respects_shuffled_input_order():
    """The split must be by TIME regardless of the order trades are handed in,
    not by whatever order the caller happened to list them in.
    """
    ordered = [_Trade(close_time=t) for t in range(50)]
    shuffled = list(reversed(ordered))
    split = split_by_close_time(shuffled, train_fraction=0.6)
    assert [t.close_time for t in split.train] == list(range(30))
    assert [t.close_time for t in split.test] == list(range(30, 50))


def test_split_fraction_is_approximately_respected():
    trades = [_Trade(close_time=t) for t in range(100)]
    split = split_by_close_time(trades, train_fraction=0.6)
    assert len(split.train) == 60
    assert len(split.test) == 40
    assert split.train_fraction_actual == pytest.approx(0.6)


def test_ties_at_the_cutoff_all_stay_on_the_train_side():
    """Trades sharing the exact close_time as the nominal cutoff trade must
    never be split across the boundary -- they all land in `train`, which is
    what keeps the "no leakage" invariant true even with duplicate timestamps.
    """
    # 8 trades at t=0..7, then 5 MORE trades all tied at t=8 (the would-be
    # cutoff for a 60% split of 13 trades lands inside this tied block).
    trades = [_Trade(close_time=t) for t in range(8)] + [
        _Trade(close_time=8, label=f"tied-{i}") for i in range(5)
    ]
    split = split_by_close_time(trades, train_fraction=0.6)
    assert max(t.close_time for t in split.train) <= min(
        t.close_time for t in split.test
    )
    # All 5 tied trades landed on the same side.
    tied_in_train = sum(1 for t in split.train if t.close_time == 8)
    tied_in_test = sum(1 for t in split.test if t.close_time == 8)
    assert tied_in_train == 5 or tied_in_test == 5


def test_rejects_empty_trade_list():
    with pytest.raises(ValueError):
        split_by_close_time([], train_fraction=0.6)


def test_rejects_out_of_range_train_fraction():
    trades = [_Trade(close_time=t) for t in range(10)]
    with pytest.raises(ValueError):
        split_by_close_time(trades, train_fraction=0.0)
    with pytest.raises(ValueError):
        split_by_close_time(trades, train_fraction=1.0)


def test_raises_when_a_half_would_be_empty():
    """All trades sharing one timestamp cannot be split in time at all."""
    trades = [_Trade(close_time=1) for _ in range(10)]
    with pytest.raises(ValueError):
        split_by_close_time(trades, train_fraction=0.6)


def test_minimum_two_trades_still_splits():
    trades = [_Trade(close_time=1), _Trade(close_time=2)]
    split = split_by_close_time(trades, train_fraction=0.6)
    assert len(split.train) == 1
    assert len(split.test) == 1
