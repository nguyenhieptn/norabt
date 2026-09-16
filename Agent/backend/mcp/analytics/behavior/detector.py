from __future__ import annotations

from typing import List

import numpy as np

from Agent.backend.mcp.schemas.bot_result import BehavioralObservations, TradeLedgerItem


class BehavioralPatternDetector:
    """Derive behavioral flags only from ledger evidence, never fixture names."""

    @staticmethod
    def analyze(
        trades: List[TradeLedgerItem], current_open_positions: int = 0
    ) -> BehavioralObservations:
        if len(trades) < 2:
            return BehavioralObservations(
                behavioral_risk_tier="UNKNOWN", evidence=["Insufficient trade history"]
            )

        ordered = sorted(trades, key=lambda trade: (trade.open_time, trade.close_time))
        evidence: List[str] = []
        # Doubling down is a within-instrument act: losing on BTC and then opening
        # a routine DOGE position is not an escalation, but comparing consecutive
        # ledger rows across instruments counted it as one. These bots run ten or
        # more markets at once, so the sequence has to be taken per symbol.
        size_hits = lev_hits = eligible_after_loss = 0
        # Control group: the same escalation measured after WINS. A bot that
        # simply varies its size will clear a bare post-loss threshold by chance,
        # so martingale has to mean "bigger after losses than after wins".
        size_hits_after_win = eligible_after_win = 0
        for symbol in {trade.symbol for trade in ordered}:
            leg = [trade for trade in ordered if trade.symbol == symbol]
            if len(leg) < 2:
                continue
            leg_sizes = np.asarray(
                [trade.margin or trade.notional or 0.0 for trade in leg],
                dtype=np.float64,
            )
            leg_leverages = np.asarray(
                [trade.leverage or 0.0 for trade in leg], dtype=np.float64
            )
            leg_losses = np.asarray(
                [trade.realized_pnl < 0 for trade in leg], dtype=bool
            )
            prior_loss = leg_losses[:-1]
            prior_win = ~prior_loss
            bigger = leg_sizes[1:] > np.maximum(leg_sizes[:-1] * 1.25, 0.0)
            eligible_after_loss += int(prior_loss.sum())
            eligible_after_win += int(prior_win.sum())
            size_hits_after_win += int((prior_win & bigger).sum())
            size_hits += int(
                (
                    prior_loss
                    & (leg_sizes[1:] > np.maximum(leg_sizes[:-1] * 1.25, 0.0))
                ).sum()
            )
            lev_hits += int(
                (prior_loss & (leg_leverages[1:] > leg_leverages[:-1] + 1.0)).sum()
            )

        eligible_after_loss = max(1, eligible_after_loss)
        size_score = size_hits / eligible_after_loss
        win_size_score = size_hits_after_win / max(1, eligible_after_win)
        martingale = (
            size_hits >= 3 and size_score >= 0.3 and size_score >= win_size_score * 1.5
        )
        # A single leverage bump somewhere in a 500-trade ledger is noise. The
        # pattern has to repeat, on the same footing martingale is judged.
        leverage_score = lev_hits / eligible_after_loss
        leverage_escalation = lev_hits >= 3 and leverage_score >= 0.3

        loss_chases = 0
        reentries = 0
        averaging_events = 0
        for previous, current in zip(ordered[:-1], ordered[1:]):
            gap_ms = current.open_time - previous.close_time
            if previous.realized_pnl < 0 and 0 <= gap_ms <= 60 * 60 * 1000:
                loss_chases += 1
            if (
                previous.symbol == current.symbol
                and previous.side == current.side
                and 0 <= gap_ms <= 15 * 60 * 1000
            ):
                reentries += 1
            overlaps = current.open_time < previous.close_time
            adverse_entry = (
                previous.entry_price is not None
                and current.entry_price is not None
                and (
                    (
                        current.side.value == "LONG"
                        and current.entry_price < previous.entry_price
                    )
                    or (
                        current.side.value == "SHORT"
                        and current.entry_price > previous.entry_price
                    )
                )
            )
            increasing_size = (current.margin or current.notional or 0.0) > (
                previous.margin or previous.notional or 0.0
            ) * 1.10
            if (
                overlaps
                and adverse_entry
                and increasing_size
                and previous.symbol == current.symbol
                and previous.side == current.side
            ):
                averaging_events += 1

        coverage_days = max(
            (max(t.close_time for t in ordered) - min(t.open_time for t in ordered))
            / 86_400_000.0,
            1 / 24,
        )
        trades_per_day = len(ordered) / coverage_days
        overtrading_score = min(1.0, max(0.0, (trades_per_day - 10.0) / 40.0))
        loss_chasing_score = loss_chases / eligible_after_loss

        holds = np.asarray(
            [trade.holding_time_minutes for trade in ordered], dtype=np.float64
        )
        median_hold = float(np.median(holds))
        p90_hold = float(np.percentile(holds, 90))
        hold_explosion = min(
            1.0, max(0.0, (p90_hold / max(median_hold, 1.0) - 2.0) / 5.0)
        )

        if martingale:
            evidence.append(
                f"{size_hits} lần tăng cỡ lệnh ngay sau lệnh lỗ trên cùng một mã "
                f"({size_score:.0%} số lần có cơ hội, so với {win_size_score:.0%} "
                "sau lệnh thắng)"
            )
        active_averaging = False
        suspected_averaging = current_open_positions >= 3
        if current_open_positions >= 3:
            evidence.append(
                f"{current_open_positions} concurrent open sub-positions; instrument/entry linkage is required before classifying averaging down"
            )
        if averaging_events:
            evidence.append(
                f"{averaging_events} overlapping trades need position-level linkage before classifying averaging down"
            )
        if loss_chases:
            evidence.append(f"{loss_chases} rapid re-entries after losses")
        if leverage_escalation:
            evidence.append(
                f"{lev_hits} lần nâng đòn bẩy sau lệnh lỗ trên cùng một mã "
                f"({leverage_score:.0%} số lần có cơ hội)"
            )
        if not evidence:
            evidence.append(
                "No material destructive pattern detected from available ledger"
            )

        composite = max(
            0.85 if martingale else 0.0,
            0.75 if current_open_positions >= 3 else 0.0,
            loss_chasing_score,
            overtrading_score,
            hold_explosion,
        )
        tier = (
            "CRITICAL"
            if composite >= 0.8
            else "HIGH"
            if composite >= 0.6
            else "MEDIUM"
            if composite >= 0.35
            else "LOW"
        )
        return BehavioralObservations(
            averaging_down_detected=active_averaging,
            averaging_down_suspected=suspected_averaging,
            martingale_escalation_detected=martingale,
            overtrading_score=overtrading_score,
            loss_chasing_score=min(1.0, loss_chasing_score),
            reentry_loop_detected=reentries >= 3,
            holding_time_explosion_score=hold_explosion,
            leverage_escalation_detected=leverage_escalation,
            size_escalation_score=min(1.0, size_score),
            behavioral_risk_tier=tier,
            evidence=evidence,
        )
