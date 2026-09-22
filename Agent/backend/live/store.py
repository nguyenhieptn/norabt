"""Dataset paths, atomic writes, and per-bot polling state for the live poller.

Step 2 and step 3 read `data/{cex,dex}/<ASSET>/bot/<bot_folder>/{overview.json,
trade_list.json}` with plain `json.load`, expecting a complete, well-formed
file every time -- they have no notion of "this file is mid-write". The only
way to poll those same files on a schedule without ever handing them a
half-written read is to never let a partial write become visible: write to a
temp file, then swap it into place with a single filesystem-level rename.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional

from Agent.backend.infra.config import config

LIVE_STATE_DIRNAME = "live"


def default_data_dir() -> Path:
    return Path(config.DATA_DIR)


def write_atomic(path: Path, payload: Any, *, indent: int = 2) -> None:
    """Write `payload` as JSON to `path` without ever exposing a partial file.

    The temp file is created in `path`'s own directory -- `os.replace` is only
    atomic within one filesystem, so a temp file under e.g. /tmp would defeat
    the whole point on any system where the data dir is a different mount.
    If anything raises before the swap (serialization error, disk full,
    process killed), the temp file is removed and `path` is left exactly as
    it was; a crash never gets to average between the old and new content.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # `os.replace` swaps the whole inode, permission bits included -- and
    # `mkstemp` creates its file mode 0600 for safety. Left alone, every
    # atomic write would quietly downgrade a normally-644 dataset file to
    # owner-only on its very first live update. Carry the old file's mode
    # forward (falling back to the umask-based default for a brand new file)
    # so a step 2/3 process running as a different user does not lose read
    # access to a file this poller never intended to touch permissions on.
    try:
        want_mode = path.stat().st_mode & 0o777
    except OSError:
        want_mode = None
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        if want_mode is not None:
            os.chmod(fd, want_mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=indent)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)  # atomic swap, same filesystem by construction
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Best-effort read; missing or corrupt files come back as None, never {}.

    None vs {} matters to every caller here: {} would read as "this bot has
    no positions and no trades", which is a claim about the bot, whereas None
    correctly reads as "we don't know" -- the caller's job, not this
    function's, to decide whether "we don't know" should block a write.
    """
    path = Path(path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


@dataclass(frozen=True)
class BotTarget:
    """One of the 30 selected lead traders, resolved to its dataset location.

    `role` (top/mid) and `symbol` come straight from bot_selection.json so the
    live poller writes into exactly the folder crawl_bots.py would have used
    -- there is no independent naming decision here to drift out of sync.

    `venue`/`symbol` are the SLOT this bot was selected to fill -- they exist
    because bot_selection.json's tree (and, deliberately, data/assessment/'s
    tree, see assessment_store._slot_index) is organized by slot, not by real
    instrument. `data_venue`/`data_symbol` are the REAL venue/asset directory
    a bot's files were actually found under (filled in by
    `with_data_location()` once `find_bot_dir()` has resolved it). The two
    pairs disagree for ~11/30 bots -- a DEX slot filled by an OKX trader who
    happens to trade a CEX pair, and so on -- and that gap has already caused
    two separate bugs: LỖI 5 (writing into a brand-new slot-derived directory
    instead of the bot's real one) and this one (asking
    CohortAssessmentService.scan() to search the slot's venue instead of the
    venue the data is actually under, so it silently found nothing). The
    rule going forward: anything that touches the filesystem to find a bot's
    data uses data_venue/data_symbol; anything that only labels the bot for
    a human (e.g. the slot shown in a report) keeps using venue/symbol.
    """

    unique_code: str
    name: str
    role: str  # "top" | "mid"
    venue: str  # slot venue, "CEX" | "DEX" -- label only, see class docstring
    symbol: str  # slot symbol, e.g. "BTC" -- label only, see class docstring
    bot_folder: str  # e.g. "bot_828556126433358780"
    # Real venue/asset the bot's data was found under -- None until
    # `with_data_location()` has run (i.e. before `find_bot_dir()` has been
    # called for this target). Deliberately never defaulted to `venue`/
    # `symbol`: a silent fallback here is exactly how the scan()-empty-venue
    # bug happened in the first place.
    data_venue: Optional[str] = None
    data_symbol: Optional[str] = None

    def bot_dir(self, data_dir: Path) -> Path:
        # Unified layout: one folder per bot_id, no venue/symbol segregation
        # -- `self.venue`/`self.symbol` (the SLOT) no longer determine this
        # path at all, see this class's own docstring for why that used to
        # be the bug (LỖI 5), not a feature, to begin with.
        return Path(data_dir) / "trade" / self.bot_folder

    def overview_path(self, data_dir: Path) -> Path:
        return self.bot_dir(data_dir) / "overview.json"

    def trade_list_path(self, data_dir: Path) -> Path:
        return self.bot_dir(data_dir) / "trade_list.json"

    def with_data_location(self, bot_dir: Path) -> "BotTarget":
        """Return a copy of this target with data_venue/data_symbol filled in.

        `bot_dir` must be whatever `find_bot_dir()` resolved for this bot's
        uniqueCode -- laid out as `<data_dir>/<venue>/<asset>/bot/<bot_folder>`
        -- so its own parent directories are the ground truth for where the
        bot's data really lives, independent of the slot it was selected
        under.

        Unified layout: `bot_dir` no longer has a `<venue>/<asset>` ancestry
        to read (`data/trade/<bot_folder>/` is flat) -- the real
        venue/asset is instead read from that bot's own `crawl_slot.json`,
        written once by the data-layout migration (see
        `Agent.backend.report.qc.reporting.assessment_store.bots_in_slot`'s
        docstring for why this is not re-derived from bot_selection.json).
        """
        bot_dir = Path(bot_dir)
        slot_path = bot_dir / "crawl_slot.json"
        slot = json.loads(slot_path.read_text(encoding="utf-8")) if slot_path.exists() else {}
        return replace(
            self,
            data_venue=(slot.get("venue") or "").upper() or None,
            data_symbol=(slot.get("asset") or "").upper() or None,
        )


def find_bot_dir(data_dir: Path, unique_code: str) -> Optional[Path]:
    """Resolve a bot's real dataset directory by uniqueCode, never by its slot.

    Unified layout: `data/trade/bot_<code>/` is the one and only location a
    bot's data can live at, so the historical multi-candidate/richness
    tie-break below (needed when the old `<venue>/<asset>/bot/<folder>`
    nesting let the same uniqueCode be crawled under more than one asset
    directory at different times -- see git history for that bug, LỖI 5)
    can no longer happen structurally. `BotTarget.bot_dir()` already points
    here directly; this function stays as the "does it actually exist"
    check every caller uses instead of assuming so.

    Returns None when no directory exists at all. Callers MUST treat that as
    "not crawled yet" and refuse to create anything.
    """
    candidate = Path(data_dir) / "trade" / f"bot_{unique_code}"
    return candidate if candidate.is_dir() else None


def load_bot_targets(
    data_dir: Optional[Path] = None, selection_path: Optional[Path] = None
) -> List[BotTarget]:
    """The 30 bots to poll, in the order bot_selection.json lists their assets.

    Reads exactly the same file the QC steps use to decide "which 30 bots",
    so the live poller can never end up watching a bot step 3 was not told
    to score, or missing one it was.
    """
    data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
    path = selection_path or (data_dir / "market" / "universe" / "bot_selection.json")
    payload = read_json(path)
    if payload is None:
        raise FileNotFoundError(
            f"Không đọc được danh sách bot theo dõi: {path}. Cần chạy bước chọn "
            "bot (bot_selection.json) trước khi bật live poller."
        )
    targets: List[BotTarget] = []
    for asset in payload.get("assets") or []:
        venue = str(asset.get("venue") or "CEX").upper()
        symbol = str(asset.get("symbol") or asset.get("underlying") or "").upper()
        if not symbol:
            continue
        for role in ("top", "mid"):
            entry = asset.get(role) or {}
            code = entry.get("code")
            if not code:
                continue
            code = str(code)
            targets.append(
                BotTarget(
                    unique_code=code,
                    name=str(entry.get("name") or code),
                    role=role,
                    venue=venue,
                    symbol=symbol,
                    bot_folder=f"bot_{code}",
                )
            )
    return targets


def fingerprint_positions(subpos_ids: Any) -> str:
    """Stable fingerprint of a set of open subPosIds.

    Sorted before hashing so the result depends only on which positions are
    open, never on the order OKX happened to list them in -- otherwise every
    poll would look "changed" even when nothing actually moved.
    """
    ids = sorted(str(item) for item in subpos_ids)
    digest = hashlib.sha256(",".join(ids).encode("utf-8"))
    return digest.hexdigest()


@dataclass
class LiveState:
    """Per-bot bookkeeping the poller needs across rounds, one JSON file each.

    Lives at data/live/state/<uniqueCode>.json -- deliberately separate from
    the bot's own overview.json/trade_list.json, because this file describes
    *our polling process*, not the bot, and must never be mistaken for
    OKX-sourced data by step 2/3 (which only ever look inside data/<venue>/).
    """

    unique_code: str
    last_polled_ms: Optional[int] = None
    last_success_ms: Optional[int] = None
    # Descriptive telemetry only -- what the open-position set looked like
    # last round. poller.py deliberately does NOT read this back to decide
    # anything (it diffs against trade_list.json's own open_positions
    # instead, see poll_bot): only a newly closed trade is allowed to trigger
    # a re-score, and this field carries no information about that.
    position_fingerprint: Optional[str] = None
    last_close_ms: Optional[int] = None
    # subPosIds we saw disappear from "current positions" but have not yet
    # found in a history page -- kept across rounds so a slow/lagging OKX
    # response does not permanently lose the append to trade_list.json.
    pending_close_subpos_ids: List[str] = field(default_factory=list)
    consecutive_errors: int = 0
    status: str = "OK"  # "OK" | "STALE"
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unique_code": self.unique_code,
            "last_polled_ms": self.last_polled_ms,
            "last_success_ms": self.last_success_ms,
            "position_fingerprint": self.position_fingerprint,
            "last_close_ms": self.last_close_ms,
            "pending_close_subpos_ids": list(self.pending_close_subpos_ids),
            "consecutive_errors": self.consecutive_errors,
            "status": self.status,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(
        cls, unique_code: str, payload: Optional[Dict[str, Any]]
    ) -> "LiveState":
        if not payload:
            return cls(unique_code=unique_code)
        return cls(
            unique_code=unique_code,
            last_polled_ms=payload.get("last_polled_ms"),
            last_success_ms=payload.get("last_success_ms"),
            position_fingerprint=payload.get("position_fingerprint"),
            last_close_ms=payload.get("last_close_ms"),
            pending_close_subpos_ids=list(
                payload.get("pending_close_subpos_ids") or []
            ),
            consecutive_errors=int(payload.get("consecutive_errors") or 0),
            status=str(payload.get("status") or "OK"),
            last_error=payload.get("last_error"),
        )


def state_path(data_dir: Path, unique_code: str) -> Path:
    return Path(data_dir) / "trade" / LIVE_STATE_DIRNAME / "state" / f"{unique_code}.json"


def load_state(data_dir: Path, unique_code: str) -> LiveState:
    payload = read_json(state_path(data_dir, unique_code))
    return LiveState.from_dict(unique_code, payload)


def save_state(data_dir: Path, state: LiveState) -> None:
    write_atomic(state_path(data_dir, state.unique_code), state.to_dict())
