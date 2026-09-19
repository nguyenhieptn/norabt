"""Where BotObservationService gets one bot's overview/ledger payload.

Historically step 2 (Agent/backend/mcp/service.py) only ever read two files a
separate crawl step (Agent/scripts/crawl_bots.py) had written to
Agent/data/<venue>/<asset>/bot/<folder>/{overview,trade_list}.json. This module
pulls that read behind an interface so step 2 can instead read straight from
OKX, in memory, with no crawl-to-disk step at all -- step 2's own parsing
(TradeLedgerManager, PositionSnapshotParser, CapitalResolver, ...) never
changes, because both implementations here hand it the exact same dict shapes
the file ever contained.

FileBotDataSource is the default and must stay behaviourally identical to the
inline file-reading code it replaces -- every one of this project's existing
tests exercises it. LiveBotDataSource is additive: nothing constructs it
unless a caller explicitly opts in.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Agent.backend.live.ratelimit import TokenBucket
from Agent.backend.mcp.inference.public_signals import SubPositionClock
from Agent.backend.okx.client import OkxApiError, OkxClient, OkxError

# OKX endpoint paths for the copytrading group, each keyed by uniqueCode. Kept
# as constants (not inlined) so a page-size or path change can't silently
# desync between get_overview and get_ledger.
HISTORY_PATH = "/api/v5/copytrading/public-subpositions-history"
POSITIONS_PATH = "/api/v5/copytrading/public-current-subpositions"
WEEKLY_PNL_PATH = "/api/v5/copytrading/public-weekly-pnl"

# Per-trader profile stats. Unlike the three paths above, confirmed against
# the real endpoint to actually respect the `uniqueCode` filter (calling it
# for two different codes returns two different bodies) -- it is
# public-lead-traders below that ignores the filter, not every endpoint in
# this group.
STATS_PATH = "/api/v5/copytrading/public-stats"

# The lead-trader ranking. NEVER call this with a `uniqueCode` filter expecting
# it to narrow the result: confirmed against the real endpoint that OKX
# ignores that parameter here and returns the top of its own ranking instead
# (ranked by whatever OKX's own default order is), i.e. a different trader's
# row. See _build_leaderboard_map's docstring for the only correct usage, and
# Agent/README.md / Agent/scripts/scan_lead_traders.py for this project's
# other run-in with the same trap.
LEAD_TRADERS_PATH = "/api/v5/copytrading/public-lead-traders"

# Must match Agent/scripts/crawl_bots.py's PAGE_SIZE exactly: service.py infers
# "the ledger might be truncated" partly from
# `len(trades) % ledger_page_size == 0` (see BotObservationService.get_bot_result),
# so a live page size that drifted from the file-based crawler's would make
# that heuristic lie about bots it has never even fetched.
PAGE_SIZE = 100

# Must match Agent/scripts/crawl_bots.py's own default exactly
# (`parser.add_argument("--max-pages", type=int, default=5)`, PAGE_SIZE=100
# above). The whole point of this source is that a live-fetched ledger and a
# freshly-crawled one for the SAME bot come out to the same depth -- not
# deeper, not shallower -- so the two are comparable and step 3's confidence
# grading (which reads ledger_truncated) means the same thing either way. A
# real measurement across the current bot universe backs 5 as the right
# number, not an arbitrary one: median crawled ledger is 124 closed trades,
# the largest ever observed is 539, and only 3 of 61 bots exceed the
# 500-trade/5-page ceiling this constant enforces -- every one of those 3
# already exhausts 5-6 pages under the crawler's own --max-pages=5 cap, i.e.
# it is *itself* truncated in the crawl, not under-served by this cap.
# Previously 100 here (10,000 trades): a full live run measured that as 20x
# the crawl's depth for no accuracy benefit and real wall-clock cost --
# e.g. one bot went from 529 crawled trades to 9,999 fetched live. Exists
# only as a ceiling (a pathological cursor that never terminates must not
# spin this source into an unbounded loop); hitting it marks the ledger
# truncated exactly like the file-based crawler's own --max-pages does. A
# caller that genuinely needs a deeper ledger than the crawl ever reached can
# still pass a larger max_pages explicitly via __init__ -- this is only the
# default.
MAX_PAGES = 5

# OKX's `copytrading` endpoint group is capped at 5 requests / 2 seconds per
# source IP (see Agent/backend/live/ratelimit.py's own docstring). Shared at
# module scope, not per-instance: the cap is per IP, so two LiveBotDataSource
# instances in the same process must draw from the same budget or they can
# jointly exceed it while each looks fine in isolation.
_DEFAULT_RATE_LIMITER = TokenBucket()

# OKX's public-stats endpoint only accepts lastDays in {1, 2, 3, 4} -- every
# other value is rejected outright. Confirmed against the real endpoint for
# uniqueCode 74F7C7A53CD18275: lastDays=5/7/30/90/365 all answer
# `{"code":"51000","msg":"Parameter lastDays error"}`, while 1/2/3/4 succeed.
# Summing each successful reply's lossDays+profitDays shows the enum is a set
# of fixed calendar windows, not an arbitrary day count:
#   lastDays=1 -> lossDays=6  + profitDays=1  = 7   days
#   lastDays=2 -> lossDays=16 + profitDays=14 = 30  days
#   lastDays=3 -> lossDays=57 + profitDays=33 = 90  days
#   lastDays=4 -> lossDays=213+ profitDays=152 = 365 days
# There is no "since inception" option. 4 (365 days) is picked as the longest
# available window: the closest analogue this endpoint offers to the
# multi-hundred-day lifetime record the rest of this project works from (the
# leaderboard's `leadDays`, the full trade ledger) -- a 7- or 30-day figure
# would describe recent form only, which is a different thing from what
# every other winRatio-shaped field in this codebase means.
STATS_LAST_DAYS = 4

# OKX's own cap for public-lead-traders: confirmed against the real endpoint
# that limit=50 answers `{"code":"51000","msg":"Parameter limit error"}` while
# limit=20 succeeds. Matches Agent/scripts/scan_lead_traders.py's own
# PAGE_SIZE, which hit the same ceiling.
LEADERBOARD_PAGE_SIZE = 20

# Generous relative to the ~259 traders this ranking has ever held (see
# Agent/data/universe/lead_traders.json) -- exists only so a pathological
# response (a page that never comes back empty) can't spin leaderboard
# building into an unbounded loop, mirroring MAX_PAGES's role for ledger
# history below.
LEADERBOARD_MAX_PAGES = 50

# OKX's own code for "this uniqueCode has no order book to show", confirmed
# against the real endpoint on a 36-lead-trader sample pulled straight off the
# ranking: 29/36 (81%) serve public-subpositions-history/public-current-
# subpositions normally, 7/36 (19%) -- roughly one in five, not a rare edge
# case -- answer both with {"code":"60004","msg":"Trader doesn't exist"}
# while still publishing their profile via public-lead-traders, their weekly
# PnL, and their public-stats row (spot-checked in full on uniqueCode
# ED2DE1A47EEF62EC, 渣哥玩币). So 60004 on THESE two endpoints specifically is
# not "this code is wrong" -- it is OKX's own choice to withhold one bot's
# order book while everything aggregate about it stays public. See
# LedgerUnavailableError below for how that distinction is surfaced.
TRADER_NOT_EXIST_CODE = "60004"

# Status vocabulary LedgerUnavailableError.status uses, exported so a caller
# (and Agent/backend/analysis/limited.py) can branch on these without
# hardcoding the literal strings in more than one place.
STATUS_FULL = "FULL"
STATUS_LIMITED = "LIMITED"
STATUS_NOT_FOUND = "NOT_FOUND"


class BotSourceError(RuntimeError):
    """A bot payload could not be produced: corrupt file content, or an OKX
    fetch that failed or came back too thin to trust.

    Deliberately NOT Agent.backend.mcp.service.BotDataUnavailableError, which
    means "this bot has no data" (a normal, expected outcome step 3 already
    knows how to report). This means "an attempt to get its data failed",
    which must never be silently reinterpreted as "it has no trades" --
    that is exactly the failure mode this source exists to avoid: a
    fetch error dressed up as an empty ledger reads to step 3 as "bot with
    no track record" instead of "we could not observe this bot right now".
    """


class LedgerUnavailableError(BotSourceError):
    """Raised by LiveBotDataSource.get_ledger specifically when OKX answered
    TRADER_NOT_EXIST_CODE (60004) on the ledger endpoints for this uniqueCode.

    This is deliberately its own type instead of a plain BotSourceError: a
    generic raise would force every caller to treat "this bot hides its
    order book" exactly like "OKX is down" or "this uniqueCode is garbage",
    which is precisely the collapse the task this exists for forbids -- see
    module-level TRADER_NOT_EXIST_CODE for the measured 19%-of-lead-traders
    rate this happens at. Catching this specific type is how the caller (a
    search-by-uniqueCode endpoint, or Agent/backend/analysis/limited.py) tells
    the three states apart and reacts differently:

      status=STATUS_LIMITED   -- 60004 on the ledger, but the code is real:
                                  it still shows up in the lead-trader ranking,
                                  in weekly-pnl, or in public-stats. A limited
                                  assessment can be built from that leftover
                                  data (see analysis/limited.py).
      status=STATUS_NOT_FOUND -- 60004 on the ledger AND none of those three
                                  supplementary endpoints has anything for
                                  this code either -- almost certainly a
                                  mistyped or fabricated uniqueCode, not a bot
                                  that is merely hiding its book.

    `profile`/`stats`/`weekly` are whatever the classification probe already
    fetched while telling LIMITED from NOT_FOUND apart (see
    LiveBotDataSource._classify_blocked_ledger) -- a caller building a limited
    assessment should use these directly rather than also calling
    get_overview(), which runs its own independent (and fail-closed) weekly
    fetch that has no reason to succeed or fail in lockstep with this one.
    """

    def __init__(
        self,
        *,
        status: str,
        code: str,
        reason: str,
        profile: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None,
        weekly: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.status = status
        self.code = code
        self.profile = profile
        self.stats = stats
        self.weekly = weekly
        super().__init__(reason)


class _TraderLedgerBlockedSignal(Exception):
    """Private, never escapes this module: raised by _get() the instant a
    ledger endpoint (POSITIONS_PATH/HISTORY_PATH) answers 60004, and caught
    immediately by get_ledger to run the LIMITED/NOT_FOUND classification.
    Kept separate from BotSourceError on purpose -- letting it accidentally
    propagate as-is would look to a caller like an ordinary, unclassified
    failure instead of the specific, already-handled case it is.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class BotDataSource(ABC):
    """Abstract source for one bot's overview.json/trade_list.json content.

    Both methods must return the exact dict shapes BotObservationService has
    always read off disk (see module docstring), or None if this bot simply
    has no data for this source. `bot_dir` is the on-disk location the
    file-based pipeline would use (data_dir/<venue>/<asset>/bot/<folder>);
    FileBotDataSource needs it because a bot's folder name is not reliably its
    OKX uniqueCode (test fixtures use names like "bot_TEST" or
    "bot_top_performer" with an unrelated uniqueCode inside the file).
    LiveBotDataSource ignores bot_dir entirely -- it has no filesystem
    involvement and only needs unique_code to query OKX. Both parameters sit
    on both methods so a caller (BotObservationService) does not need to know
    which concrete source it is talking to.
    """

    @abstractmethod
    def get_overview(
        self, unique_code: str, bot_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_ledger(
        self, unique_code: str, bot_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class FileBotDataSource(BotDataSource):
    """Read overview.json/trade_list.json off disk -- the historical behaviour.

    `unique_code` is accepted for interface parity with LiveBotDataSource but
    is not used: bot_dir alone has always been enough to find the files, and
    trusting a folder-name-derived code here (rather than bot_dir) would be a
    behaviour change, not a refactor.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)

    def get_overview(
        self, unique_code: str, bot_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        return self._read(bot_dir, "overview.json")

    def get_ledger(
        self, unique_code: str, bot_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        return self._read(bot_dir, "trade_list.json")

    @staticmethod
    def _read(bot_dir: Optional[Path], filename: str) -> Optional[Dict[str, Any]]:
        if bot_dir is None:
            # Purely a programming error (BotObservationService always passes
            # bot_dir once _find_bot_dir has resolved it) -- never reachable
            # through the public get_bot_result path, so it is not worth a
            # Vietnamese user-facing message.
            raise BotSourceError("FileBotDataSource requires bot_dir")
        path = Path(bot_dir) / filename
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BotSourceError(
                f"Invalid bot data file {path.name}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise BotSourceError(
                f"Invalid bot data file {path.name}: expected an object"
            )
        return payload


class LiveBotDataSource(BotDataSource):
    """Fetch one bot's overview/ledger straight from OKX, in memory only.

    Builds the same dict shapes Agent/scripts/crawl_bots.py writes to disk, so
    every downstream parser in service.py works unmodified. Never writes a
    file -- "no storage" is the entire point of this class.

    Fail-closed by construction: any OKX error, any non-list response where a
    list is expected, or a ledger that comes back with zero closed trades AND
    zero open positions raises BotSourceError instead of returning a payload
    that would look to step 3 like "a bot with no history". A genuinely
    dormant bot still has to have traded to be OKX-listed at all, so an
    all-empty response is far more likely a wrong uniqueCode or a transient
    OKX gap than the truth.

    Profile fields (nickName/aum/pnl/pnlRatio/leadDays/winRatio) are the one
    exception to that fail-closed rule: they come from two supplementary
    endpoints (public-lead-traders for the first group, public-stats for
    winRatio) that are best-effort by design (see get_overview). A bot that
    has simply dropped off the ranking, or a stats call that errors, degrades
    those fields to None with a reason recorded in provenance -- it must never
    raise, because "we don't have this bot's profile" is a completely
    different, much more common situation than "we could not observe this
    bot's trades at all", which is what BotSourceError is reserved for.

    One more exception to the plain-BotSourceError rule: OKX's own
    TRADER_NOT_EXIST_CODE (60004) on the ledger endpoints specifically means
    "this bot won't show its order book", not "this fetch failed" -- see
    LedgerUnavailableError. get_ledger raises that distinguished type instead
    of a bare BotSourceError so a caller can tell a bot that is merely opaque
    (status=LIMITED, a reduced assessment is still possible) apart from a
    uniqueCode that plainly does not exist (status=NOT_FOUND).
    """

    def __init__(
        self,
        client: Optional[OkxClient] = None,
        rate_limiter: Optional[TokenBucket] = None,
        page_size: int = PAGE_SIZE,
        max_pages: int = MAX_PAGES,
    ) -> None:
        self._client = client or OkxClient()
        self._rate_limiter = rate_limiter or _DEFAULT_RATE_LIMITER
        self._page_size = page_size
        self._max_pages = max_pages
        # Lazily built, then reused for every bot this instance is ever asked
        # about -- see _leaderboard_map(). None means "not built yet", as
        # opposed to {} which means "built, and either empty or the build
        # itself failed" (see _leaderboard_error).
        self._leaderboard: Optional[Dict[str, Dict[str, Any]]] = None
        self._leaderboard_error: Optional[str] = None

    def get_overview(
        self, unique_code: str, bot_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        code = self._require_code(unique_code)
        weekly = self._owned_by(
            self._get(
                WEEKLY_PNL_PATH,
                {"uniqueCode": code, "instType": "SWAP"},
                code,
                "weekly_pnl",
            ),
            code,
        )
        # Both of these are best-effort profile enrichment, never on the
        # fail-closed path the ledger/weekly calls above are on -- see the
        # class docstring and each helper's own docstring for why.
        board_row = self._leaderboard_map().get(code)
        stats_row = self._fetch_public_stats(code)

        profile_fields, profile_note = self._profile_provenance(
            code, board_row, stats_row
        )
        now = int(time.time() * 1000)
        return {
            "uniqueCode": code,
            # aum/pnl/pnlRatio/leadDays/nickName come from one paged pass over
            # public-lead-traders, matched back onto uniqueCode -- the only
            # correct way to use that endpoint (see LEAD_TRADERS_PATH). A code
            # that has dropped off the ranking, or is outside whatever OKX's
            # ranking currently covers, legitimately has none of these; that
            # is recorded in provenance rather than guessed at.
            "nickName": (board_row or {}).get("nickName") or code,
            "aum": (board_row or {}).get("aum"),
            "pnl": (board_row or {}).get("pnl"),
            "pnlRatio": (board_row or {}).get("pnlRatio"),
            "leadDays": (board_row or {}).get("leadDays"),
            "okx_rank": (board_row or {}).get("rank"),
            # winRatio comes from public-stats instead of the leaderboard row
            # (which also happens to publish a winRatio) so this field
            # reflects a fixed, known window (STATS_LAST_DAYS) rather than
            # whatever window OKX's ranking snapshot itself uses internally.
            "winRatio": (stats_row or {}).get("winRatio"),
            # Not part of the file-based overview.json schema -- additive,
            # cheap per-bot context from the same public-stats call that
            # supplies winRatio. Downstream code must keep tolerating its
            # absence (it was never there for file-sourced bots), so this is
            # deliberately not treated as required anywhere.
            "investAmt": (stats_row or {}).get("investAmt"),
            "weekly_pnl_history": weekly,
            "observed_at_ms": now,
            "provenance": {
                "crawled_at_ms": now,
                "weekly_pnl": f"{self._client.base_url}{WEEKLY_PNL_PATH}",
                "positions": f"{self._client.base_url}{POSITIONS_PATH}",
                "history": f"{self._client.base_url}{HISTORY_PATH}",
                "lead_traders": f"{self._client.base_url}{LEAD_TRADERS_PATH}",
                "public_stats": f"{self._client.base_url}{STATS_PATH}",
                "profile_fields": profile_fields,
                "profile_note": profile_note,
            },
        }

    def get_ledger(
        self, unique_code: str, bot_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        code = self._require_code(unique_code)
        try:
            positions = self._owned_by(
                self._get(
                    POSITIONS_PATH,
                    {"uniqueCode": code, "instType": "SWAP"},
                    code,
                    "current_positions",
                ),
                code,
            )
            trades, truncated = self._fetch_history(code)
        except _TraderLedgerBlockedSignal as signal:
            # 60004 on a ledger endpoint specifically -- never a generic
            # raise (see LedgerUnavailableError's docstring). Classify before
            # raising so the caller gets LIMITED vs NOT_FOUND, not just "it
            # failed".
            raise self._classify_blocked_ledger(signal.code) from signal

        if not trades and not positions:
            # See the class docstring: this is the fail-closed guard against
            # handing step 3 a fake "no trades" ledger. A real fetch failure
            # (bad code, OKX outage) and a genuinely untraded bot are
            # indistinguishable from an all-empty response alone, so both are
            # refused rather than one being silently assumed.
            raise BotSourceError(
                f"OKX returned a completely empty ledger for code {code} (0 closed "
                "trades, 0 open positions); refusing to process this, since it is "
                "more likely a wrong code or an OKX outage than a bot that has "
                "never traded"
            )

        unattributed = sum(1 for p in positions if not p.get("instId"))
        # Cheap and pure (no network call): decodes the open time embedded in
        # OKX's snowflake-style subPosId. Everything past this -- actually
        # guessing the instrument of an instId-less position from its PnL
        # ratio and leverage -- is Agent/scripts/crawl_bots.py's
        # attribute_positions(), which needs market/history-candles calls this
        # source does not make; that is a separate, heavier feature and out of
        # this migration's scope, so "determined"/"narrowed" stay honestly 0
        # rather than faked.
        decoded_time = sum(
            1
            for p in positions
            if not p.get("openTime")
            and SubPositionClock.open_time_ms(p.get("subPosId")) is not None
        )
        now = int(time.time() * 1000)
        return {
            "uniqueCode": code,
            "open_positions_count": len(positions),
            "open_positions": positions,
            "closed_trades_count": len(trades),
            "closed_trades": trades,
            "ledger_truncated": truncated,
            "ledger_page_size": self._page_size,
            "positions_without_instrument": unattributed,
            "inference": {
                "decoded_time": decoded_time,
                "determined": 0,
                "narrowed": 0,
                "outside": 0,
            },
            "provenance": {"crawled_at_ms": now},
            "observed_at_ms": now,
        }

    def _fetch_history(self, code: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Page public-subpositions-history exactly like crawl_bots.crawl_history:
        same page size, same cursor (the last row's subPosId), same stop
        condition (a short page or a page with nothing new) -- so a live
        ledger and a freshly-crawled one for the same bot come out identical.
        """
        collected: List[Dict[str, Any]] = []
        seen: set = set()
        cursor: Optional[str] = None
        truncated = False
        for page in range(1, self._max_pages + 1):
            params: Dict[str, Any] = {
                "uniqueCode": code,
                "instType": "SWAP",
                "limit": self._page_size,
            }
            if cursor:
                params["after"] = cursor
            batch = self._owned_by(
                self._get(HISTORY_PATH, params, code, f"history_page_{page}"),
                code,
            )
            fresh = [r for r in batch if str(r.get("subPosId")) not in seen]
            for record in fresh:
                seen.add(str(record.get("subPosId")))
            collected.extend(fresh)
            if len(batch) < self._page_size or not fresh:
                break
            cursor = str(batch[-1].get("subPosId"))
            if page == self._max_pages:
                truncated = True
        return collected, truncated

    @staticmethod
    def _profile_provenance(
        code: str,
        board_row: Optional[Dict[str, Any]],
        stats_row: Optional[Dict[str, Any]],
    ) -> Tuple[str, str]:
        """Decide what to write into overview.provenance.profile_fields/note.

        Kept as one place so get_overview's return statement doesn't have to
        interleave this bookkeeping with the payload fields themselves.
        Mirrors the vocabulary Agent/scripts/crawl_bots.py and
        Agent/scripts/backfill_bot_profiles.py already use
        (OKX_LEADERBOARD_SNAPSHOT_BY_UNIQUECODE / UNAVAILABLE) so a reader
        comparing a live-sourced and file-sourced overview.json side by side
        sees the same provenance vocabulary either way.
        """
        if board_row is not None:
            fields = "OKX_LEADERBOARD_SNAPSHOT_BY_UNIQUECODE"
            note = (
                "nickName/aum/pnl/pnlRatio/leadDays come from one paged pass over "
                "public-lead-traders matched on uniqueCode (querying it with a "
                "uniqueCode filter is ignored by OKX and returns another trader's "
                "row); winRatio/investAmt come from public-stats"
                if stats_row is not None
                else "nickName/aum/pnl/pnlRatio/leadDays come from one paged pass "
                "over public-lead-traders matched on uniqueCode; public-stats "
                f"had no data for {code}, so winRatio/investAmt are absent"
            )
            return fields, note

        reason = (
            "OKX did not return this bot in its current lead-trader ranking "
            "(it may have dropped rank, or the ranking simply does not cover it)"
        )
        return "UNAVAILABLE", (
            f"{reason}; nickName falls back to the uniqueCode and "
            "aum/pnl/pnlRatio/leadDays/okx_rank stay None rather than guessed"
        )

    def _leaderboard_map(self) -> Dict[str, Dict[str, Any]]:
        """Lazily build, then cache for the lifetime of this instance, a
        uniqueCode -> lead-trader-ranking-row map.

        This is the ONLY correct way to use public-lead-traders for a specific
        bot. Confirmed against the real endpoint: passing `uniqueCode=<code>`
        does not filter anything -- OKX still returns the top of its own
        ranking (a different trader's row). The single correct workaround is
        to page the WHOLE ranking once and index it by each row's own
        uniqueCode, exactly like Agent/scripts/scan_lead_traders.py already
        does. Caching here is what makes that affordable: paging the ~259-
        trader board costs ~13 requests total, however many bots this process
        goes on to ask about, because every bot after the first is served from
        this dict instead of triggering another pass. Do NOT "optimize" this
        into a per-bot filtered request -- that request would silently
        attribute a different trader's profile to the bot being looked up.
        """
        if self._leaderboard is not None:
            return self._leaderboard
        try:
            board = self._build_leaderboard_map()
        except BotSourceError as exc:
            # Leaderboard enrichment is best-effort (see class docstring), so
            # a failed build must not propagate. It IS still cached (as
            # empty), so a transient outage costs one failed pagination pass
            # per process, not one per bot -- otherwise every subsequent bot
            # would re-attempt the same doomed page 1 and re-spend rate-limit
            # budget for a result already known to fail.
            self._leaderboard = {}
            self._leaderboard_error = str(exc)
            return self._leaderboard
        self._leaderboard = board
        self._leaderboard_error = None
        return board

    def _build_leaderboard_map(self) -> Dict[str, Dict[str, Any]]:
        board: Dict[str, Dict[str, Any]] = {}
        for page in range(1, LEADERBOARD_MAX_PAGES + 1):
            rows = self._fetch_leaderboard_page(page)
            if not rows:
                break
            fresh = 0
            for row in rows:
                code = row.get("uniqueCode")
                if not code or code in board:
                    continue
                fresh += 1
                # Insertion order tracks OKX's own ranking order (pages are
                # fetched in increasing order, and each page is already rank-
                # ordered), so the row's position in `board` at insert time IS
                # its rank -- exactly how Agent/scripts/scan_lead_traders.py
                # derives the same field.
                enriched = dict(row)
                enriched["rank"] = len(board) + 1
                board[code] = enriched
            if fresh == 0:
                # A page that repeated only codes already seen means we've
                # wrapped back onto the start of the ranking (OKX has been
                # observed to do this past the last real page rather than
                # returning an empty page) -- stop rather than looping forever.
                break
        return board

    def _fetch_leaderboard_page(self, page: int) -> List[Dict[str, Any]]:
        self._rate_limiter.acquire()
        params = {
            "instType": "SWAP",
            "limit": LEADERBOARD_PAGE_SIZE,
            "page": page,
            # Deliberately no sortType. Passing one (e.g. sortType=pnl_ratio)
            # switches OKX to a different, narrower ranking -- confirmed
            # shrinking the board from 259 to 82 traders -- which would make
            # this map silently miss most bots. Agent/scripts/scan_lead_traders.py
            # carries the same warning for the same reason.
        }
        try:
            data = self._client.public_get(LEAD_TRADERS_PATH, params)
        except OkxError as exc:
            raise BotSourceError(
                f"OKX error fetching page {page} of the lead-trader ranking: {exc}"
            ) from exc
        if not isinstance(data, list) or not data:
            return []
        block = data[0]
        if not isinstance(block, dict) or not isinstance(block.get("ranks"), list):
            raise BotSourceError(
                f"OKX returned malformed data for the lead-trader ranking "
                f"(page {page}): expected an object with a 'ranks' key"
            )
        return block["ranks"]

    def _fetch_public_stats(self, code: str) -> Optional[Dict[str, Any]]:
        """Best-effort per-bot stats fetch (winRatio/investAmt).

        Unlike _get (used for weekly/positions/history), a failure here is
        swallowed rather than raised: this is profile enrichment, not ledger
        data, and the class docstring's fail-closed guarantee is specifically
        about never faking ledger content -- it does not extend to a bot
        simply lacking a supplementary stats row.
        """
        self._rate_limiter.acquire()
        try:
            data = self._client.public_get(
                STATS_PATH,
                {
                    "uniqueCode": code,
                    "instType": "SWAP",
                    "lastDays": STATS_LAST_DAYS,
                },
            )
        except OkxError:
            return None
        if not isinstance(data, list) or not data:
            return None
        row = data[0]
        return row if isinstance(row, dict) else None

    def _fetch_weekly_probe(self, code: str) -> Optional[List[Dict[str, Any]]]:
        """Best-effort weekly-pnl fetch used only to classify an already-
        60004'd ledger as LIMITED vs NOT_FOUND (see _classify_blocked_ledger).

        Deliberately separate from get_overview's own weekly fetch, which
        goes through _get() and is fail-closed by design (a bot's normal
        overview must not silently substitute "no error" for "OKX actually
        refused"). This probe runs strictly after the ledger has already been
        confirmed blocked, at a point where the only question left is "does
        ANY endpoint still know about this code" -- so, like
        _fetch_public_stats, any OKX error here just means "no evidence from
        this endpoint" rather than something to raise.
        """
        self._rate_limiter.acquire()
        try:
            data = self._client.public_get(
                WEEKLY_PNL_PATH, {"uniqueCode": code, "instType": "SWAP"}
            )
        except OkxError:
            return None
        if not isinstance(data, list) or not data:
            return None
        return self._owned_by(data, code) or None

    def _classify_blocked_ledger(self, code: str) -> LedgerUnavailableError:
        """Tell LIMITED apart from NOT_FOUND once a ledger endpoint has
        already answered 60004 for `code`.

        Measured against the real API (see TRADER_NOT_EXIST_CODE): a bot that
        hides its order book still shows up in the lead-trader ranking, in
        weekly-pnl, and/or in public-stats -- all three are independent of
        the ledger endpoints OKX is withholding. So checking those three is
        exactly the test the task specifies: any one of them having data
        means this is a real, merely-opaque bot (LIMITED); none of them
        having anything means 60004 is just OKX's answer for "no such
        uniqueCode at all" (NOT_FOUND), most likely a typo'd or made-up code
        rather than a bot that chose to hide its book.
        """
        board_row = self._leaderboard_map().get(code)
        stats_row = self._fetch_public_stats(code)
        weekly = self._fetch_weekly_probe(code)

        if board_row or stats_row or weekly:
            return LedgerUnavailableError(
                status=STATUS_LIMITED,
                code=code,
                reason=(
                    f"This bot does not expose its order book (OKX returned error "
                    f"{TRADER_NOT_EXIST_CODE} on the ledger endpoint for code {code}), "
                    "but its profile/weekly equity/stats are still available, so a "
                    "limited assessment is still possible"
                ),
                profile=board_row,
                stats=stats_row,
                weekly=weekly,
            )
        return LedgerUnavailableError(
            status=STATUS_NOT_FOUND,
            code=code,
            reason=(
                f"Code {code} was not found on any OKX endpoint (ledger returned "
                f"{TRADER_NOT_EXIST_CODE}, not in the lead-trader ranking, no "
                "weekly-pnl, no public-stats) -- most likely a wrong or nonexistent "
                "uniqueCode"
            ),
        )

    def _get(
        self, path: str, params: Dict[str, Any], code: str, label: str
    ) -> List[Dict[str, Any]]:
        # Blocks (via TokenBucket.acquire) rather than dropping the request:
        # every call here is on the critical path of producing one bot's
        # result, so there is no "skip it" option the way a background poller
        # might have.
        self._rate_limiter.acquire()
        try:
            data = self._client.public_get(path, params)
        except OkxApiError as exc:
            if exc.code == TRADER_NOT_EXIST_CODE and path in (
                POSITIONS_PATH,
                HISTORY_PATH,
            ):
                # Not a generic failure -- see LedgerUnavailableError's
                # docstring. Signalled privately so get_ledger (the only
                # caller that ever hits these two paths) can classify it into
                # LIMITED/NOT_FOUND instead of this raising a plain
                # BotSourceError that would erase the distinction.
                raise _TraderLedgerBlockedSignal(code) from exc
            raise BotSourceError(
                f"OKX error fetching {label} for code {code}: {exc}"
            ) from exc
        except OkxError as exc:
            raise BotSourceError(
                f"OKX error fetching {label} for code {code}: {exc}"
            ) from exc
        if not isinstance(data, list):
            raise BotSourceError(
                f"OKX returned malformed data for {label} (code {code}): "
                "expected a list"
            )
        return data

    @staticmethod
    def _owned_by(records: List[Dict[str, Any]], code: str) -> List[Dict[str, Any]]:
        """Drop any record carrying a different uniqueCode. Mirrors
        Agent/scripts/crawl_bots.py's own guard of the same name against OKX
        occasionally handing back a neighbouring trader's row."""
        return [r for r in records if r.get("uniqueCode") in (None, "", code)]

    @staticmethod
    def _require_code(unique_code: str) -> str:
        code = str(unique_code or "").strip()
        if not code:
            raise BotSourceError("Missing uniqueCode to call OKX")
        return code
