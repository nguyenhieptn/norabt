from __future__ import annotations

from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.report.qc.evaluator.common import available, unknown


class PerformanceQualityLens:
    @staticmethod
    def evaluate(bot: BotResult):
        perf = bot.performance
        if perf.trade_count == 0 or perf.expectancy is None:
            return unknown(
                "Performance quality", 1.0, "No valid closed trades"
            )
        score = 20.0
        findings = []
        deferred = bot.deferred_loss
        distorted = deferred.distorts_headline_metrics
        if distorted:
            # Win rate and profit factor only describe the trades the bot chose to close.
            score += 40.0
            if deferred.never_realized_a_loss:
                findings.append(
                    f"No loss has ever been booked across {perf.trade_count} closed "
                    f"trades, while {deferred.losing_open_positions} open positions are "
                    f"carrying {deferred.open_loss:,.0f} USDT of unrealised loss"
                )
            elif (
                deferred.booked_profit_factor is not None
                and deferred.marked_profit_factor is not None
            ):
                findings.append(
                    f"Profit factor {deferred.booked_profit_factor:.2f} → "
                    f"{deferred.marked_profit_factor:.2f} once "
                    f"{deferred.open_loss:,.0f} USDT of open loss is closed"
                )
            else:
                findings.append(
                    f"Unrealised loss of {deferred.open_loss:,.0f} USDT is not "
                    f"reflected in the closed-trade metrics"
                )
            if deferred.turns_unprofitable_when_marked:
                score += 20.0
                findings.append(
                    "Closing the whole open book turns an apparent profit into a loss"
                )
            if deferred.open_loss_to_capital_pct:
                score += min(25.0, deferred.open_loss_to_capital_pct)
                findings.append(
                    f"Unrealised loss equals {deferred.open_loss_to_capital_pct:.1f}% "
                    f"of reference capital"
                )
            findings.append(
                "Win rate, profit factor and drawdown measured on closed trades are "
                "not representative of reality, and have been discounted accordingly"
            )
        if perf.trade_count < 20:
            score += 35.0
            findings.append(f"Small sample: {perf.trade_count} trades")
        elif perf.trade_count < 50:
            score += 15.0
            findings.append(f"Moderate sample: {perf.trade_count} trades")
        else:
            score -= 5.0
            findings.append(f"Sample size is large enough: {perf.trade_count} trades")

        if distorted:
            findings.append(
                f"For reference only: win rate {perf.win_rate:.0f}%, profit factor "
                + (f"{perf.profit_factor:.2f}" if perf.profit_factor else "meaningless")
            )
        elif perf.profit_factor is None:
            findings.append("Profit factor is meaningless because the sample has no gross loss")
        elif distorted:
            pass
        elif perf.profit_factor < 1.0:
            score += 40.0
            findings.append(f"Profit factor below 1 ({perf.profit_factor:.2f})")
        elif perf.profit_factor < 1.3:
            score += 15.0
            findings.append(f"Fragile profit factor ({perf.profit_factor:.2f})")
        else:
            score -= 5.0
            findings.append(f"Positive profit factor ({perf.profit_factor:.2f})")

        if distorted:
            pass
        elif perf.expectancy <= 0:
            score += 25.0
            findings.append(f"Expectancy is not positive ({perf.expectancy:.2f})")
        else:
            score -= 5.0
            findings.append(f"Positive expectancy ({perf.expectancy:.2f} per trade)")
        if (
            perf.win_rate > 85.0
            and perf.payoff_ratio is not None
            and perf.payoff_ratio < 0.2
        ):
            score += 30.0
            findings.append("High win rate paired with a heavily skewed payoff ratio")
        confidence = min(1.0, perf.trade_count / 50.0)
        if deferred.representativeness == "UNKNOWN":
            confidence *= 0.7
        return available("Performance quality", score, 1.0, findings, confidence)
