"""Read a saved assessment record as a dossier-shaped view.

A live analysis produces a full `AnalysisDossier` from typed results. Most page
views, however, are served from a saved record, which is deliberately compact:
it keeps the numbers the report shows and drops the typed objects behind them.

This module exposes that saved record through the *same* stable-id contract the
live dossier uses, and it does so without inventing anything. Whatever the
compact record does not carry is reported as `UNKNOWN` and named in
`limitations`, never defaulted to a neutral-looking number. The two views are
therefore comparable but never confusable: `source_shape` always says which one
a consumer is holding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

from Agent.backend.report.qc.reporting.market_adapter import normalize_market_payload


# Fields the live dossier computes from typed results and the saved record
# simply does not contain. Naming them keeps "absent from this record" distinct
# from "measured and found to be nothing".
_NOT_IN_COMPACT_RECORD = (
    "behavioral_dna.trait_sample_sizes",
    "risk_twin.transformations",
    "scenarios",
    "source_ledger",
)


class PersistedDossierView(BaseModel):
    """A saved record presented under the dossier contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "persisted_dossier_view.v1"
    source_shape: str = "COMPACT_ASSESSMENT_RECORD"
    status: str = "UNKNOWN"
    subject: Dict[str, Any] = Field(default_factory=dict)
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    scoring: Dict[str, Any] = Field(default_factory=dict)
    executive_essence: Dict[str, Any] = Field(default_factory=dict)
    behavioral_dna: Dict[str, Any] = Field(default_factory=dict)
    risk_twin: Dict[str, Any] = Field(default_factory=dict)
    market_compatibility: Dict[str, Any] = Field(default_factory=dict)
    premium_market: Dict[str, Any] = Field(default_factory=dict)
    uncertainty: Dict[str, Any] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    unavailable_fields: List[str] = Field(default_factory=list)


def _mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _status_of(value: Any) -> str:
    return "OBSERVED" if value is not None else "UNKNOWN"


def build_persisted_dossier_view(record: Any) -> PersistedDossierView:
    """Present one saved assessment record under the dossier contract.

    `record` is the JSON document `assessment_store` writes. Anything missing
    stays missing: this function never falls back to the live pipeline, and it
    never substitutes a default for an unmeasured value.
    """
    payload = _mapping(record)
    if not payload:
        return PersistedDossierView(
            status="NOT_FOUND",
            limitations=["No saved assessment record was supplied"],
            unavailable_fields=list(_NOT_IN_COMPACT_RECORD),
        )

    bot = _mapping(payload.get("bot"))
    evidence = _mapping(payload.get("evidence"))
    scoring = _mapping(payload.get("scoring"))
    recommendation = _mapping(payload.get("recommendation"))

    limitations: List[str] = [
        "This view is built from a saved record; per-trade and per-source "
        "detail is not part of that record"
    ]
    if scoring.get("total_weight") is None:
        limitations.append(
            "Per-dimension weights are not present in this saved record"
        )

    subject = {
        "bot_id": bot.get("bot_id") or payload.get("bot_id"),
        "unique_code": bot.get("unique_code") or payload.get("code"),
        "nick_name": bot.get("nick_name"),
        "symbol": bot.get("traded_symbol") or bot.get("symbol"),
        "venue": bot.get("venue") or "OKX",
        "venue_type": bot.get("venue_type"),
    }

    # Behavioral DNA, restricted to the traits the record actually carries.
    dna_traits = []
    for key, label, value in (
        ("directional_bias", "Directional bias", evidence.get("directional_bias")),
        ("entry_style", "Entry style", evidence.get("entry_style")),
        ("regime_dependence", "Regime dependence", evidence.get("regime_dependence_pct")),
        ("profit_factor", "Closed-book profit factor", evidence.get("profit_factor")),
        ("marked_profit_factor", "Marked profit factor", evidence.get("marked_profit_factor")),
    ):
        dna_traits.append(
            {
                "key": key,
                "label": label,
                "value": value,
                "status": _status_of(value),
                # The saved record keeps no per-trait sample size, so claiming
                # one here would be an invention.
                "sample_size": None,
                "evidence_ids": [f"record.evidence.{key}"],
            }
        )

    booked = evidence.get("profit_factor")
    marked = evidence.get("marked_profit_factor")
    risk_twin = {
        "reported": {
            "state": "REPORTED",
            "status": _status_of(booked),
            "metrics": {
                "profit_factor": booked,
                "win_rate": evidence.get("win_rate"),
                "total_pnl": evidence.get("total_pnl"),
                "trade_count": evidence.get("trade_count"),
            },
            "evidence_ids": ["record.evidence"],
        },
        "marked": {
            "state": "MARKED",
            "status": _status_of(marked),
            "metrics": {
                "profit_factor": marked,
                "open_positions": evidence.get("open_positions"),
                "open_loss": evidence.get("open_loss"),
                "open_loss_to_capital_pct": evidence.get("open_loss_to_capital_pct"),
            },
            "evidence_ids": ["record.evidence"],
            "limitations": (
                []
                if marked is not None
                else ["The saved record carries no marked profit factor"]
            ),
        },
        # Stressed states are a live-simulation product and are never written
        # into the saved record.
        "stressed": [],
        "transformations": [],
    }

    compatibility = {
        "primary_symbol": subject["symbol"],
        "observed_regimes": [],
        "untested_regimes": list(evidence.get("untested_phases") or []),
        "losing_regimes": list(evidence.get("losing_phases") or []),
        "best_phase": evidence.get("best_phase"),
        "worst_phase": evidence.get("worst_phase"),
        "phase_coverage_pct": evidence.get("phase_coverage_pct"),
        "cells": [],
        "limitations": [
            "The saved record keeps phase summaries, not the per-regime cells "
            "a live analysis produces"
        ],
    }

    essence = {
        "what_it_appears_to_do": evidence.get("strategy_profile")
        or evidence.get("observed_profile"),
        "dominant_behavior": None,
        "strongest_positive_evidence": None,
        "strongest_fragility": None,
        "evidence_reliability": "UNKNOWN",
        "most_important_unknown": (
            "Downtrend behavior is undetermined"
            if evidence.get("tested_in_downtrend") is False
            else None
        ),
    }

    uncertainty = {
        "data_completeness": None,
        "freshness": None,
        "sample_adequacy": None,
        "regime_coverage": (
            evidence["phase_coverage_pct"] / 100.0
            if isinstance(evidence.get("phase_coverage_pct"), (int, float))
            and not isinstance(evidence.get("phase_coverage_pct"), bool)
            else None
        ),
        "overall_reliability": "UNKNOWN",
        "abstention_reasons": [
            "Uncertainty components are computed during a live analysis and are "
            "not stored in the saved record"
        ],
    }

    return PersistedDossierView(
        status=str(payload.get("status") or "FULL"),
        subject=subject,
        evaluation={
            "generated_at_ms": payload.get("generated_at_ms")
            or payload.get("timestamp"),
            "methodology_versions": {},
            "reproducibility_warnings": [
                "A saved record does not carry the simulation seed, so its "
                "Monte Carlo figures cannot be reproduced from this view"
            ],
        },
        scoring={
            "risk_score": scoring.get("risk_score") or recommendation.get("risk_score"),
            "quality_score": scoring.get("quality_score")
            or recommendation.get("quality_score"),
            "confidence": recommendation.get("confidence"),
            "verdict": recommendation.get("verdict"),
            "decided_by": scoring.get("score_decided_by"),
            "total_weight": scoring.get("total_weight"),
            "applicable_dimensions": scoring.get("applicable_dimensions"),
        },
        executive_essence=essence,
        behavioral_dna={"traits": dna_traits, "dominant_patterns": [], "unknowns": []},
        risk_twin=risk_twin,
        market_compatibility=compatibility,
        premium_market=normalize_market_payload(payload.get("market")),
        uncertainty=uncertainty,
        limitations=limitations,
        unavailable_fields=list(_NOT_IN_COMPACT_RECORD),
    )
