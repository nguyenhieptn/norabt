"""Việc 1's own required regression sweep: no file under
`Agent/frontend/src/` may reference the retired Vietnamese-keyed raw
`assessment.json` fields (`khuyen_nghi`, its own `ket_luan` sub-field) --
the whole point of the fix being that `GET /api/bots` now serves the ONE
already-normalized row shape (see `Agent/backend/web/data.py`'s
`bot_listing_row`), so the SPA never again has a reason to read, mention, or
re-derive from those raw keys, not even in a comment.

A plain substring sweep (not an AST/string-literal-only one, unlike
test_verdict_relabel.py's retired-verdict-label sweep): JSX/JS has no
comment-vs-code ambiguity worth being lenient about here, and the task's own
wording ("không còn chuỗi ... nào") asks for the string to be gone from the
tree entirely, including from prose explaining the historical bug.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_ROOT / "Agent" / "frontend" / "src"

# English names after the VN->EN string conversion: `khuyen_nghi` (the raw
# top-level object) -> `recommendation`; its `ket_luan` sub-field ->
# `verdict`. A bare "verdict" is no longer safe to forbid on its own: the
# normalized `/api/bots` row (see `bot_listing_row` in
# `Agent/backend/web/data.py`) now legitimately exposes a flat `verdict`
# field that the SPA is SUPPOSED to read (`row.verdict`, `botMeta.verdict`,
# etc.) -- that is the whole point of Việc 1's fix. What must stay banned is
# a reference to the raw nested field, which cannot be written in JS/CSS
# without the raw parent key `recommendation` appearing in the source too.
_FORBIDDEN_SUBSTRINGS = ("recommendation",)

_SOURCE_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".css")


def test_frontend_src_exists_for_this_sweep_to_mean_anything() -> None:
    assert FRONTEND_SRC.is_dir(), f"expected {FRONTEND_SRC} to exist"
    files = list(FRONTEND_SRC.rglob("*"))
    assert any(f.is_file() and f.suffix in _SOURCE_SUFFIXES for f in files)


def test_no_retired_raw_assessment_field_name_anywhere_in_frontend_src() -> None:
    hits: List[str] = []
    for path in FRONTEND_SRC.rglob("*"):
        if not path.is_file() or path.suffix not in _SOURCE_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for needle in _FORBIDDEN_SUBSTRINGS:
            if needle in text:
                hits.append(f"{path.relative_to(REPO_ROOT)}: {needle!r}")
    assert not hits, (
        "retired raw assessment.json field name(s) still referenced in "
        "Agent/frontend/src/:\n" + "\n".join(hits)
    )
