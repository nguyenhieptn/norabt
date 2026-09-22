"""Stable report contracts layered on top of the deterministic dossier.

These models are presentation contracts. They intentionally do not expose
internal scoring objects as a frontend API and they never compute a verdict or
risk value. Missing values remain explicit.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from Agent.backend.report.qc.reporting.dossier import (
    DossierStatus,
    EvidenceItem,
    EvidenceProvenance,
    EvaluationContext,
    DossierSubject,
)


class ReportProduct(str, Enum):
    ANALYST = "analyst"
    PREMIUM_MARKET = "premium_market"
    OTHER_POSITION = "other_position"


class ReportMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    label: str
    value: Optional[Union[float, int, str, bool, Dict[str, Any], List[Any]]] = None
    unit: Optional[str] = None
    display_value: Optional[str] = None
    status: EvidenceProvenance = EvidenceProvenance.UNKNOWN
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class ReportFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    text: str
    severity: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    status: EvidenceProvenance = EvidenceProvenance.UNKNOWN


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    title: str
    status: EvidenceProvenance = EvidenceProvenance.UNKNOWN
    metrics: List[ReportMetric] = Field(default_factory=list)
    findings: List[ReportFinding] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class ReportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "report_document.v1"
    report_id: str
    report_product: ReportProduct
    dossier_id: str
    dossier_digest: str
    subject: DossierSubject
    status: DossierStatus
    snapshot: EvaluationContext
    sections: List[ReportSection] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    narrative: Optional[Dict[str, Any]] = None
    access_context: Dict[str, Any] = Field(default_factory=dict)
