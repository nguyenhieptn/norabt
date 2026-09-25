"""Role-based visibility as an explicit policy over one dossier.

The design contract is blunt about this: a user and an admin read the *same*
core dossier. A role may hide a panel or a raw detail, but it must never
receive a differently computed score, a different verdict, or a quietly
shortened evidence list.

So this module never recomputes anything. It takes a serialized dossier and
returns the same object with withheld branches replaced by an explicit
`DETAIL_WITHHELD_BY_ROLE` marker, plus a limitation saying what was withheld.
A reader can therefore always tell "you are not being shown this" apart from
"this was never measured" -- the distinction that silent DOM stripping loses.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Tuple


WITHHELD_MARKER = "DETAIL_WITHHELD_BY_ROLE"


class ViewRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


# Dotted paths withheld from a USER view. Each entry is raw operational detail
# that is useless without the surrounding admin context; none of them feeds a
# score, so removing them cannot change a number the user sees.
# TEMPORARY (project owner, 2026-09-25): every role sees the full analysis --
# no withheld branch, no locked tab -- until plans/permissions are decided.
# Flip back to True to restore the USER gating defined below unchanged.
ROLE_GATING_ENABLED = False

_USER_WITHHELD_PATHS: Tuple[str, ...] = (
    "bot_result",
    "primary_market_result",
    "source_ledger",
    "risk_assessment.score_breakdown",
)

# Panels a USER view does not render. These are presentation IDs, not data:
# the dossier keeps every field, and the report simply does not open the panel.
_USER_HIDDEN_PANELS: Tuple[str, ...] = ("panel-market", "panel-trades")

USER_WITHHELD_PATHS: Tuple[str, ...] = _USER_WITHHELD_PATHS if ROLE_GATING_ENABLED else ()
USER_HIDDEN_PANELS: Tuple[str, ...] = _USER_HIDDEN_PANELS if ROLE_GATING_ENABLED else ()

ADMIN_WITHHELD_PATHS: Tuple[str, ...] = ()


def _withhold(payload: Dict[str, Any], path: str) -> bool:
    """Replace one dotted path with the marker. Returns True when it applied."""
    parts = path.split(".")
    node: Any = payload
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    leaf = parts[-1]
    if not isinstance(node, dict) or leaf not in node:
        return False
    if node[leaf] is None:
        # Nothing was measured, so there is nothing to withhold; leaving the
        # None in place keeps "absent" honest instead of relabelling it.
        return False
    node[leaf] = WITHHELD_MARKER
    return True


def apply_view_policy(
    dossier_payload: Dict[str, Any], role: ViewRole
) -> Dict[str, Any]:
    """Return a role-scoped copy of a serialized dossier.

    The scoring fields (`risk_assessment.risk_score`, `quality_score`,
    `confidence`, `verdict`) are never touched by any role, which is what makes
    the two views comparable.
    """
    import copy

    payload = copy.deepcopy(dossier_payload)
    withheld_paths = (
        USER_WITHHELD_PATHS if role is ViewRole.USER else ADMIN_WITHHELD_PATHS
    )

    applied: List[str] = []
    for path in withheld_paths:
        if _withhold(payload, path):
            applied.append(path)

    limitations = list(payload.get("limitations") or [])
    for path in applied:
        limitations.append(f"{WITHHELD_MARKER}: {path}")
    payload["limitations"] = limitations
    payload["view_role"] = role.value
    payload["withheld_paths"] = applied
    payload["hidden_panels"] = list(
        USER_HIDDEN_PANELS if role is ViewRole.USER else ()
    )
    return payload


def scoring_fingerprint(dossier_payload: Dict[str, Any]) -> Dict[str, Any]:
    """The values that must be identical across every role's view.

    Used by the acceptance tests to prove a user view is not a weaker
    calculation, only a narrower presentation.
    """
    assessment = dossier_payload.get("risk_assessment") or {}
    return {
        "risk_score": assessment.get("risk_score"),
        "quality_score": assessment.get("quality_score"),
        "confidence": assessment.get("confidence"),
        "verdict": assessment.get("verdict"),
        "risk_tier": assessment.get("risk_tier"),
        "dossier_digest": dossier_payload.get("dossier_digest"),
    }
