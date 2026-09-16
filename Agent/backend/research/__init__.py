"""Out-of-sample validation of the QC risk score against real bot outcomes.

This package answers one question: does the risk score computed from a bot's
PAST closed trades predict how badly it does on trades that had not
happened yet? It never scores anything on its own -- it reuses the real
product scoring path (Agent/backend/pipeline.py's RiskSupervisionPipeline)
against a deliberately truncated view of one bot's ledger, and compares the
resulting score to what that same bot actually did afterwards.

Modules:
    splitting        -- time-based (never random) train/test split of a
                         bot's closed trades.
    outcomes         -- pure functions computing realized outcome metrics
                         (PnL, drawdown, win rate, losing streaks, collapse)
                         directly from a list of closed trades.
    statistics       -- Spearman rank correlation, a bootstrap confidence
                         interval for it, and a shuffle-based null benchmark,
                         all hand-rolled on top of numpy (no scipy).
    dataset          -- discovers bot ledgers on disk and parses them with
                         the exact same TradeLedgerManager the product uses.
    shadow_scoring   -- builds a symlinked "shadow" copy of Agent/data with
                         one bot's ledger swapped for a truncated, in-sample
                         version, then runs the unmodified
                         RiskSupervisionPipeline against it.
"""
