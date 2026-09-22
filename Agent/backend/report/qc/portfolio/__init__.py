"""Multi-bot portfolio analysis: co-movement, concentration and joint loss tail.

Strictly additive to the per-bot path. Nothing in this package is reachable
from `QCCoreService.assess_bot`, and no existing scoring changes because it
exists.
"""

from Agent.backend.report.qc.portfolio.correlation import CorrelationAnalyzer
from Agent.backend.report.qc.portfolio.joint_monte_carlo import JointMonteCarloEngine
from Agent.backend.report.qc.portfolio.schemas import (
    PortfolioRiskAssessment,
    PortfolioVerdict,
)
from Agent.backend.report.qc.portfolio.service import (
    PortfolioCandidate,
    PortfolioQCService,
)
from Agent.backend.report.qc.portfolio.timeseries import TimeSeriesMerger

__all__ = [
    "CorrelationAnalyzer",
    "JointMonteCarloEngine",
    "PortfolioCandidate",
    "PortfolioQCService",
    "PortfolioRiskAssessment",
    "PortfolioVerdict",
    "TimeSeriesMerger",
]
