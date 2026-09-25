"""The book as ONE account: portfolio-level headline numbers from N PnL series.

A single-bot report computes its headline numbers from one bot's trades. A
portfolio of N bots is N PnL series running side by side, and its headline
numbers have to come from those N series COMBINED on the shared clock -- not
from a pooled list of everyone's trades run through the single-bot formulas:

    portfolio PnL per period    P_t   = sum_i p_{i,t}
    portfolio capital           C     = sum_i c_i
    portfolio equity            E_t   = C + sum_{s<=t} P_s
    portfolio return per period r_t   = P_t / C = sum_i w_i r_{i,t},  w_i = c_i / C
    max drawdown                max_t (peak_t - E_t) / peak_t
    volatility                  sigma_p = sqrt(w' Cov(r) w)            (annualised)
    risk contribution           RC_i = w_i (Cov(r) w)_i / sigma_p^2     (sums to 100%)

Pooling trades instead answers "what did the average trade do", which is a
different question: measured on a live 4-bot book (2026-09-24) the pooled
per-trade Sharpe read 5.97 against the book's daily Sharpe of 2.06, and the
pooled profit factor 2.47 against 1.41.

Periods in which no member's PnL moved are dropped from the aligned matrix
(they say nothing about co-movement), but they are real periods of zero
return for the ACCOUNT, so they are restored as zeros here before any mean,
deviation or annualisation -- leaving them out would overstate every
per-period average and every Sharpe built on it.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

from Agent.backend.report.qc.portfolio.schemas import (
    MemberRiskShare,
    PortfolioBookMetrics,
    PortfolioMember,
)
from Agent.backend.report.qc.portfolio.timeseries import AlignedSeries

_DAY_MS = 86_400_000


def _round(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None or not np.isfinite(value):
        return None
    return round(float(value), digits)


def compute_book_metrics(
    series: AlignedSeries, members: Sequence[PortfolioMember]
) -> Optional[PortfolioBookMetrics]:
    """Portfolio-level metrics over the aligned members, or None if unaligned."""
    if not series.is_valid or series.matrix.size == 0:
        return None
    diagnostics = series.diagnostics
    by_label: Dict[str, PortfolioMember] = {m.label: m for m in members}
    labels = list(series.labels)
    capitals = [by_label[label].capital_at_risk if label in by_label else None for label in labels]
    codes = [by_label[label].unique_code if label in by_label else label for label in labels]
    warnings: List[str] = []

    moved = series.matrix  # N x T_moved, time order
    n_moved = int(moved.shape[1])
    n_all = max(int(diagnostics.span_buckets or 0), n_moved)
    idle = n_all - n_moved
    periods_per_year = 365.0 * _DAY_MS / float(series.bucket_ms)

    book_pnl = moved.sum(axis=0)
    total_pnl = float(book_pnl.sum())
    member_pnl = moved.sum(axis=1)

    have_capital = all(value is not None and value > 0 for value in capitals)
    if not have_capital:
        warnings.append(
            "At least one member has no capital, so every percentage below is "
            "withheld rather than computed against a partial total"
        )
        return PortfolioBookMetrics(
            pnl_basis=diagnostics.pnl_basis,
            bucket_label=diagnostics.bucket_label,
            periods=n_all,
            periods_per_year=round(periods_per_year, 4),
            total_pnl=round(total_pnl, 2),
            members=[
                MemberRiskShare(label=label, unique_code=code, pnl=round(float(pnl), 2))
                for label, code, pnl in zip(labels, codes, member_pnl)
            ],
            warnings=warnings,
        )

    caps = np.array(capitals, dtype=np.float64)
    capital = float(caps.sum())
    weights = caps / capital

    # Equity path: idle periods do not move equity, so the moved columns in
    # time order give the exact path.
    equity = capital + np.cumsum(book_pnl)
    peaks = np.maximum.accumulate(np.concatenate([[capital], equity]))[1:]
    drawdown = (peaks - equity) / peaks
    max_dd_index = int(np.argmax(drawdown))
    max_dd_abs = float(peaks[max_dd_index] - equity[max_dd_index])

    # Per-period returns over ALL periods (idle ones restored as zeros).
    padded = np.concatenate([moved, np.zeros((moved.shape[0], idle))], axis=1)
    member_returns = padded / caps[:, None]
    book_returns = padded.sum(axis=0) / capital

    mean = float(book_returns.mean())
    std = float(book_returns.std(ddof=1)) if n_all > 1 else 0.0
    downside = float(np.sqrt(np.mean(np.minimum(book_returns, 0.0) ** 2)))
    scale = np.sqrt(periods_per_year)

    gains = float(book_pnl[book_pnl > 0].sum())
    losses = float(-book_pnl[book_pnl < 0].sum())

    shares: List[MemberRiskShare] = []
    diversification = None
    if len(labels) >= 2 and n_all > 1:
        covariance = np.cov(member_returns, ddof=1)
        portfolio_var = float(weights @ covariance @ weights)
        standalone = np.sqrt(np.clip(np.diag(covariance), 0.0, None))
        if portfolio_var > 0:
            contribution = weights * (covariance @ weights) / portfolio_var
            weighted_standalone = float(weights @ standalone)
            if weighted_standalone > 0:
                diversification = 1.0 - np.sqrt(portfolio_var) / weighted_standalone
        else:
            contribution = np.full(len(labels), np.nan)
        for index, (label, code) in enumerate(zip(labels, codes)):
            shares.append(
                MemberRiskShare(
                    label=label,
                    unique_code=code,
                    capital_weight_pct=_round(weights[index] * 100.0, 2),
                    standalone_volatility_pct=_round(standalone[index] * scale * 100.0, 2),
                    risk_contribution_pct=_round(contribution[index] * 100.0, 2),
                    pnl=_round(member_pnl[index], 2),
                )
            )

    return PortfolioBookMetrics(
        pnl_basis=diagnostics.pnl_basis,
        bucket_label=diagnostics.bucket_label,
        periods=n_all,
        periods_per_year=round(periods_per_year, 4),
        capital=round(capital, 2),
        total_pnl=round(total_pnl, 2),
        return_pct=_round(total_pnl / capital * 100.0, 3),
        max_drawdown_pct=_round(float(drawdown.max()) * 100.0, 3),
        max_drawdown_abs=_round(max_dd_abs, 2),
        current_drawdown_pct=_round(float(drawdown[-1]) * 100.0, 3),
        profitable_period_pct=_round(float((book_pnl > 0).sum()) / n_all * 100.0, 2),
        profit_factor=_round(gains / losses, 3) if losses > 0 else None,
        volatility_annual_pct=_round(std * scale * 100.0, 3),
        sharpe_annual=_round(mean / std * scale, 3) if std > 0 else None,
        sortino_annual=_round(mean / downside * scale, 3) if downside > 0 else None,
        volatility_diversification_pct=(
            _round(diversification * 100.0, 2) if diversification is not None else None
        ),
        members=shares,
        warnings=warnings,
    )
