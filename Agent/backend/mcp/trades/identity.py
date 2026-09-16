from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LedgerOwnership(BaseModel):
    """Every OKX sub-position carries its owner, so a mis-filed ledger is detectable."""

    expected_code: Optional[str] = None
    owner_codes: List[str] = Field(default_factory=list)
    foreign_codes: List[str] = Field(default_factory=list)
    foreign_rows: int = Field(default=0, ge=0)
    total_rows: int = Field(default=0, ge=0)

    @property
    def belongs_to_another_bot(self) -> bool:
        return bool(self.foreign_codes) and self.foreign_rows >= max(
            1, self.total_rows // 2
        )


class LedgerIdentityGuard:
    @staticmethod
    def verify(overview: Dict[str, Any], payload: Dict[str, Any]) -> LedgerOwnership:
        expected = overview.get("uniqueCode")
        expected_code = str(expected) if expected not in (None, "") else None

        rows: List[Dict[str, Any]] = []
        for key in ("closed_trades", "open_positions"):
            value = payload.get(key)
            if isinstance(value, list):
                rows.extend(row for row in value if isinstance(row, dict))
        declared = payload.get("uniqueCode")
        if declared not in (None, ""):
            rows.append({"uniqueCode": declared})

        owners: List[str] = []
        foreign_rows = 0
        counted = 0
        for row in rows:
            owner = row.get("uniqueCode")
            if owner in (None, ""):
                continue
            owner = str(owner)
            counted += 1
            if owner not in owners:
                owners.append(owner)
            if expected_code is not None and owner != expected_code:
                foreign_rows += 1

        foreign = [code for code in owners if expected_code and code != expected_code]
        return LedgerOwnership(
            expected_code=expected_code,
            owner_codes=owners,
            foreign_codes=foreign,
            foreign_rows=foreign_rows,
            total_rows=counted,
        )
