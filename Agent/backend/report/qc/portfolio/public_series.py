"""OKX's public daily PnL, turned into a series the portfolio layer can align.

WHY THIS EXISTS. OKX answers 60004 ("Trader doesn't exist") on exactly two
endpoints for a bot that hides its order book -- `public-subpositions-history`
and `public-current-subpositions`. Everything aggregate stays public:
`public-pnl` (up to 365 daily points), `public-preference-currency` (what it
trades, as shares), `public-stats` (capital, win ratio, profit/loss days).
Measured live on three concealed bots (2026-09-24): 285, 366 and 349 daily
points respectively. Treating such a bot as "unmeasurable" threw away a year
of daily PnL that was sitting in plain view.

WHAT THE NUMBERS ARE. `public-pnl` returns, newest first, the CUMULATIVE PnL
since the start of the requested window, one row per day; the oldest row is
always 0. Day boundaries are Hong Kong days (every `beginTs` is 16:00 UTC).
So the PnL of day k is `cum[k] - cum[k-1]`, attributed to day k's `beginTs`.

It is MARK-TO-MARKET PnL: open positions are revalued daily. Checked against
14 bots whose order books ARE public, over the same window: the totals agree
(e.g. -23,518 vs -23,906 USDT; 1,019 vs 1,046), and the cumulative curves
correlate at a median r of 0.85 -- the same money, booked when it is marked
rather than when a position closes. Daily values correlate less (median 0.33)
precisely because of that timing difference, which is why the portfolio
layer never mixes the two bases in one matrix (see
`AlignmentDiagnostics.pnl_basis`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

PNL_BASIS_LEDGER = "REALIZED_LEDGER"
PNL_BASIS_MARK_TO_MARKET = "MARK_TO_MARKET_DAILY"


@dataclass(frozen=True)
class PublicPnlProfile:
    """One bot as OKX's public aggregate endpoints describe it."""

    unique_code: str
    # (day start in ms, PnL over that day in quote currency), ascending.
    daily: Tuple[Tuple[int, float], ...]
    nick_name: Optional[str] = None
    # `public-stats.investAmt`: the capital the bot trades with.
    capital: Optional[float] = None
    # `public-preference-currency`: base symbol -> share of activity, 0-1.
    exposure: Dict[str, float] = field(default_factory=dict)

    @property
    def days(self) -> int:
        return len(self.daily)

    @property
    def last_day_ms(self) -> Optional[int]:
        return self.daily[-1][0] if self.daily else None


def _number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # NaN guard


def parse_public_profile(
    unique_code: str, raw: Optional[Mapping[str, Any]]
) -> Optional[PublicPnlProfile]:
    """The raw bundle a `BotDataSource.get_public_profile` returns, parsed.

    `raw` is `{"pnl": [...public-pnl rows...], "preference": [...],
    "stats": {...} | None, "nickName": str | None}` -- the endpoints' own row
    shapes, unmodified, so a snapshot written by the crawler and a live read
    parse through the same code.

    Returns None when there is no usable daily series (fewer than two
    cumulative points gives zero daily deltas): no PnL series means nothing
    for the correlation layer to use, and an empty profile would read as a
    bot that simply never moved.
    """
    if not raw:
        return None
    cumulative: Dict[int, float] = {}
    for row in raw.get("pnl") or []:
        if not isinstance(row, Mapping):
            continue
        begin = _number(row.get("beginTs"))
        value = _number(row.get("pnl"))
        if begin is None or value is None:
            continue
        cumulative[int(begin)] = value
    points = sorted(cumulative.items())
    if len(points) < 2:
        return None
    daily = tuple(
        (later_ts, later - earlier)
        for (_, earlier), (later_ts, later) in zip(points, points[1:])
    )

    stats = raw.get("stats") if isinstance(raw.get("stats"), Mapping) else {}
    capital = _number(stats.get("investAmt"))
    exposure: Dict[str, float] = {}
    for row in raw.get("preference") or []:
        if not isinstance(row, Mapping):
            continue
        ccy = str(row.get("ccy") or "").strip().upper()
        ratio = _number(row.get("ratio"))
        if ccy and ratio is not None and ratio > 0:
            exposure[ccy] = exposure.get(ccy, 0.0) + ratio
    nick = raw.get("nickName")
    return PublicPnlProfile(
        unique_code=str(unique_code),
        daily=daily,
        nick_name=str(nick) if nick not in (None, "") else None,
        capital=capital if capital is not None and capital > 0 else None,
        exposure=exposure,
    )
