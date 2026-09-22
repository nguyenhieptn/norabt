"""Durable history of portfolio runs, kept apart from the per-bot history.

A separate store rather than a new record type inside
`AssessmentHistoryStore`: that file is keyed by `bot_id` and every reader of
it -- trend detection, the cohort report, `web/data.py` -- assumes one bot per
file and one bot per entry. A portfolio belongs to no single bot, so it has
nowhere to live there without breaking that assumption for everything already
reading it.

Identity is the SET of members, not the run: re-analysing the same three bots
lands in the same file, which is what makes a portfolio's own history (did its
correlation drift?) readable later.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from Agent.backend.infra.config import config
from Agent.backend.report.qc.portfolio.schemas import PortfolioRiskAssessment

SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


class PortfolioHistoryStore:
    MAX_ENTRIES = 50

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or Path(config.DATA_DIR) / "report" / "state" / "portfolios"

    def _path(self, portfolio_id: str) -> Path:
        safe = SAFE_ID.sub("_", portfolio_id).strip("_") or "unknown_portfolio"
        return self.root / f"{safe}.json"

    def history(self, portfolio_id: str) -> List[PortfolioRiskAssessment]:
        path = self._path(portfolio_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []
        restored: List[PortfolioRiskAssessment] = []
        for entry in entries:
            try:
                restored.append(PortfolioRiskAssessment.model_validate(entry))
            except Exception:
                # A single entry written by an older schema must not take the
                # whole file's history with it.
                continue
        return restored

    def latest(self, portfolio_id: str) -> Optional[PortfolioRiskAssessment]:
        entries = self.history(portfolio_id)
        return entries[-1] if entries else None

    def append(self, assessment: PortfolioRiskAssessment) -> bool:
        """Store one run. Re-analysing an unchanged snapshot is a no-op.

        `assessment_id` digests every member's snapshot time and ledger
        fingerprint (see `PortfolioQCService`), so an identical id means
        nothing about the underlying data moved.
        """
        entries = self.history(assessment.portfolio_id)
        if entries and entries[-1].assessment_id == assessment.assessment_id:
            return False
        entries.append(assessment)
        entries = entries[-self.MAX_ENTRIES :]
        path = self._path(assessment.portfolio_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "portfolio_history.v1",
            "portfolio_id": assessment.portfolio_id,
            "member_codes": list(assessment.member_codes),
            "entries": [entry.model_dump(mode="json") for entry in entries],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True

    def list_latest(self) -> List[PortfolioRiskAssessment]:
        """Most recent run of every stored portfolio, newest first.

        This is what an operator's portfolio-history table reads. Files that
        fail to parse are skipped rather than raised on: one corrupt file must
        not empty the whole list.
        """
        if not self.root.exists():
            return []
        rows: List[PortfolioRiskAssessment] = []
        for path in self.root.glob("*.json"):
            entries = self.history(path.stem)
            if entries:
                rows.append(entries[-1])
        rows.sort(key=lambda entry: entry.timestamp, reverse=True)
        return rows
