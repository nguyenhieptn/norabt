from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from Agent.backend.infra.config import config
from Agent.backend.report.qc.schemas.risk_assessment import BotRiskAssessment

SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


class AssessmentHistoryStore:
    """Durable per-bot assessment history so risk trend survives across runs."""

    MAX_ENTRIES = 200

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or Path(config.DATA_DIR) / "state" / "assessments"

    def _path(self, bot_id: str) -> Path:
        safe = SAFE_ID.sub("_", bot_id).strip("_") or "unknown_bot"
        return self.root / f"{safe}.json"

    def history(self, bot_id: str) -> List[BotRiskAssessment]:
        path = self._path(bot_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []
        restored: List[BotRiskAssessment] = []
        for entry in entries:
            try:
                restored.append(BotRiskAssessment.model_validate(entry))
            except Exception:
                continue
        return restored

    def latest(self, bot_id: str) -> Optional[BotRiskAssessment]:
        entries = self.history(bot_id)
        return entries[-1] if entries else None

    def append(self, assessment: BotRiskAssessment) -> bool:
        """Store one assessment. Re-running the same snapshot is a no-op."""
        entries = self.history(assessment.bot_id)
        if entries and entries[-1].assessment_id == assessment.assessment_id:
            return False
        entries.append(assessment)
        entries = entries[-self.MAX_ENTRIES :]
        path = self._path(assessment.bot_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "assessment_history.v1",
            "bot_id": assessment.bot_id,
            "entries": [entry.model_dump(mode="json") for entry in entries],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
