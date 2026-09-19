"""Proof that the live-source architecture (Agent/backend/sources/*) actually
works, in two independent ways.

Kiểu A ("same-data"): take ONE payload (in practice: a live OKX fetch for a
real bot) and run it through BotObservationService via two different
BotDataSource implementations -- FileBotDataSource reading it back off a
temp file, and an in-memory fake handing back the identical dict object.
Both implementations are contractually required to feed
BotObservationService the exact same shape (see
Agent/backend/sources/bot_source.py's module docstring), so identical input
must produce an identical BotResult. Any field that differs beyond a small
time-only allowlist is a bug in the source abstraction, full stop -- it is
not explainable by "the market moved" or "the bot traded more", because
there is only one snapshot of data in play here.

Kiểu B ("live-vs-file"): run step 3 (QC risk assessment) once against
Agent/data's on-disk crawl and once against OKX right now, over the same set
of bots, and classify every difference instead of demanding equality --
real-world drift (more trades closed, market conditions changed, OKX's own
leadDays counter advancing) is expected and is not a bug. What must never
happen is an unexplained difference getting waved through as "drift": this
module's classifier only ever assigns DỮ LIỆU TRÔI when it can point at a
concrete cause (a trade-count delta or a market-state change); everything
else that isn't an exact match or a pure time artefact lands in BẤT THƯỜNG,
which is the group a human is meant to look at.

Both modes reuse Agent/backend/run_report.py's apply_live_source/
build_live_sources -- the same attribute-swap mechanism --source live relies
on -- so this module never has to know how a *Service class is wired
internally, only that swapping its market/bot attribute after construction is
how a live source gets in.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.mcp.service import BotObservationService
from Agent.backend.okx.client import OkxClient
from Agent.backend.qc.reporting.cohort import BotEvaluationRow, CohortAssessmentService
from Agent.backend.qc.reporting.render import _cell, _header, _stamp, _wrap
from Agent.backend.run_report import (
    PRODUCTION_SIMULATION_HORIZON,
    PRODUCTION_SIMULATION_ITERATIONS,
    PRODUCTION_SIMULATION_SEED,
    apply_live_source,
    build_live_sources,
    default_selection_codes,
)
from Agent.backend.sources.bot_source import (
    BotDataSource,
    BotSourceError,
    FileBotDataSource,
    LiveBotDataSource,
)
from Agent.backend.sources.market_source import MarketDataUnavailableError

# --------------------------------------------------------------------------- #
# Generic recursive diff -- shared by both comparison modes. Kiểu A diffs a
# full BotResult tree; Kiểu B diffs a much shallower BotEvaluationRow, but the
# walk is identical: dicts recurse by key, equal-length lists recurse by
# index, everything else is a leaf compared with !=.
# --------------------------------------------------------------------------- #

_MISSING = object()  # sentinel: a key present on one side only is still a diff


def _flatten_diffs(a: Any, b: Any, path: str = "") -> List[Tuple[str, Any, Any]]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: List[Tuple[str, Any, Any]] = []
        for key in sorted(set(a) | set(b), key=str):
            sub_path = f"{path}.{key}" if path else str(key)
            out.extend(
                _flatten_diffs(a.get(key, _MISSING), b.get(key, _MISSING), sub_path)
            )
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for index, (av, bv) in enumerate(zip(a, b)):
            out.extend(_flatten_diffs(av, bv, f"{path}[{index}]"))
        return out
    if a != b:
        return [(path, a, b)]
    return []


def _top_field(path: str) -> str:
    """The BotResult/BotEvaluationRow field a dotted/indexed diff path belongs
    to, e.g. "market.trend" and "market[0].x" both belong to "market"."""
    return path.split(".", 1)[0].split("[", 1)[0]


# --------------------------------------------------------------------------- #
# Kiểu A -- same data, two BotDataSource implementations.
# --------------------------------------------------------------------------- #

# Fields that legitimately depend on wall-clock time even when as_of_ms is
# pinned identically on both calls (defensive allowlist -- with as_of_ms and
# an explicit observed_at_ms present on the payload, nothing should actually
# land here; see compare_same_data's docstring).
SAME_DATA_TIME_FIELDS = {"timestamp", "as_of_ms"}


@dataclass
class SameDataComparison:
    unique_code: str
    asset: str
    venue_type: str
    file_result: BotResult
    fake_result: BotResult
    diffs: List[Tuple[str, Any, Any]] = field(default_factory=list)

    @property
    def fatal_diffs(self) -> List[Tuple[str, Any, Any]]:
        return [d for d in self.diffs if _top_field(d[0]) not in SAME_DATA_TIME_FIELDS]

    @property
    def identical(self) -> bool:
        return not self.fatal_diffs


class _StaticBotSource(BotDataSource):
    """Hands back the exact same dict objects every time -- never touches disk.

    This is the "fake" leg of Kiểu A: the point is that BotObservationService
    cannot tell this apart from FileBotDataSource as long as both are handed
    the same payload content, because both implement the same BotDataSource
    contract (see Agent/backend/sources/bot_source.py).
    """

    def __init__(self, overview: Dict[str, Any], ledger: Dict[str, Any]) -> None:
        self._overview = overview
        self._ledger = ledger

    def get_overview(self, unique_code: str, bot_dir: Optional[Path] = None):
        return self._overview

    def get_ledger(self, unique_code: str, bot_dir: Optional[Path] = None):
        return self._ledger


def compare_same_data(
    overview: Dict[str, Any],
    ledger: Dict[str, Any],
    *,
    asset: str,
    unique_code: str,
    venue_type: str = "CEX",
    seed: int = 42,
    as_of_ms: Optional[int] = None,
    simulation_iterations: int = 10_000,
    simulation_horizon: Optional[int] = None,
) -> SameDataComparison:
    """Run one (overview, ledger) payload through BotObservationService twice
    -- once via FileBotDataSource (payload written to a temp file first), once
    via an in-memory fake that returns the identical objects -- and diff the
    two BotResults.

    `as_of_ms` is pinned once and passed to both calls so the `timestamp`
    field (set from it directly, see BotObservationService.get_bot_result)
    cannot differ just because time passed between the two calls; the
    `as_of_ms` field on BotResult itself is derived from the payload's own
    observed_at_ms, so it already agrees between the two paths without any
    pinning. Nothing here talks to the network -- overview/ledger are plain
    dicts the caller already has (from a live fetch, or a synthetic fixture in
    a test).
    """
    now = as_of_ms if as_of_ms is not None else int(time.time() * 1000)
    folder = f"bot_{unique_code}"
    kwargs = dict(
        bot_folder_name=folder,
        seed=seed,
        venue_type=venue_type,
        as_of_ms=now,
        simulation_iterations=simulation_iterations,
        simulation_horizon=simulation_horizon,
    )

    with tempfile.TemporaryDirectory(prefix="run_compare_same_data_") as tmp:
        tmp_dir = Path(tmp)
        bot_dir = tmp_dir / venue_type.lower() / asset / "bot" / folder
        bot_dir.mkdir(parents=True, exist_ok=True)
        # Written once and never rewritten, so both calls below see the exact
        # same file (same mtime) -- relevant only as the freshness fallback
        # _observed_at() would use if observed_at_ms were absent from the
        # payload; a real live payload always sets it, but this keeps the two
        # paths identical either way.
        (bot_dir / "overview.json").write_text(json.dumps(overview), encoding="utf-8")
        (bot_dir / "trade_list.json").write_text(json.dumps(ledger), encoding="utf-8")

        file_service = BotObservationService(
            tmp_dir, EvaluationMode.SNAPSHOT, bot_source=FileBotDataSource(tmp_dir)
        )
        fake_service = BotObservationService(
            tmp_dir,
            EvaluationMode.SNAPSHOT,
            bot_source=_StaticBotSource(overview, ledger),
        )
        file_result = file_service.get_bot_result(asset, **kwargs)
        fake_result = fake_service.get_bot_result(asset, **kwargs)

    diffs = _flatten_diffs(
        file_result.model_dump(mode="json"), fake_result.model_dump(mode="json")
    )
    return SameDataComparison(
        unique_code=unique_code,
        asset=asset,
        venue_type=venue_type,
        file_result=file_result,
        fake_result=fake_result,
        diffs=diffs,
    )


def render_same_data(cmp: SameDataComparison) -> str:
    columns = (("FIELD", 42), ("VIA FILE", 34), ("VIA FAKE SOURCE", 34))
    lines = _header(
        columns,
        "TYPE A COMPARISON -- SAME DATA, TWO PROCESSING PATHS",
        f"Bot {cmp.unique_code} ({cmp.asset}/{cmp.venue_type}) | "
        "FileBotDataSource vs an in-memory fake BotDataSource, same payload",
    )
    width = len(lines[4])
    if not cmp.diffs:
        lines.append(
            "Exact match across the whole BotResult -- no field differs."
        )
    else:
        for path, file_value, fake_value in cmp.diffs:
            tag = (
                " (accepted: time field)"
                if _top_field(path) in SAME_DATA_TIME_FIELDS
                else " !!"
            )
            lines.append(
                " ".join(
                    [
                        _cell(path + tag, 42),
                        _cell(file_value, 34),
                        _cell(fake_value, 34),
                    ]
                )
            )
    lines.append("-" * width)
    if cmp.identical:
        tolerated = len(cmp.diffs)
        extra = f" ({tolerated} time fields ignored)" if tolerated else ""
        lines.append(
            "CONCLUSION: PASS -- the same payload produces an identical BotResult "
            f"through both paths{extra}. The data-source architecture (BotDataSource) "
            "works correctly."
        )
    else:
        lines.append(
            f"CONCLUSION: FAIL -- {len(cmp.fatal_diffs)} field(s) differ outside the "
            "time-field group. This is a BUG in the data-source architecture (the same "
            "payload must produce the same result), not data drift."
        )
    return "\n".join(lines)


def _locate_bot_folder(
    data_dir: Path, unique_code: str
) -> Tuple[Optional[str], Optional[str]]:
    """Where uniqueCode's own folder sits in the crawled tree: (venue_type, asset).

    Only used to know which asset/venue to hand get_bot_result -- the actual
    bot content compared in Kiểu A comes from the live fetch, not this folder.
    Mirrors PairedBotReportService._locate's own lookup.
    """
    for path in sorted(data_dir.rglob(f"bot_{unique_code}")):
        if (path / "trade_list.json").exists() and len(
            path.relative_to(data_dir).parts
        ) >= 2:
            parts = path.relative_to(data_dir).parts
            return parts[0].upper(), parts[1]
    return None, None


def run_same_data(args: argparse.Namespace) -> int:
    data_dir = Path(config.DATA_DIR)
    code = args.bot
    venue_type, asset = _locate_bot_folder(data_dir, code)
    if asset is None:
        print(
            f"No crawled folder found for code {code} under {data_dir} "
            "(need to know this bot's asset/venue to call get_bot_result).",
            file=sys.stderr,
        )
        return 1
    print(f"[same-data] Bot {code} belongs to {venue_type}/{asset}.", file=sys.stderr)
    print(f"[same-data] Calling OKX for {code}'s overview...", file=sys.stderr)
    client = OkxClient()
    live_source = LiveBotDataSource(client=client)
    try:
        overview = live_source.get_overview(code)
        print(f"[same-data] Calling OKX for {code}'s ledger...", file=sys.stderr)
        ledger = live_source.get_ledger(code)
    except BotSourceError as exc:
        print(f"Could not fetch live data for {code}: {exc}", file=sys.stderr)
        return 1
    if overview is None or ledger is None:
        print(f"OKX returned no data for code {code}.", file=sys.stderr)
        return 1

    now_ms = int(time.time() * 1000)
    cmp = compare_same_data(
        overview,
        ledger,
        asset=asset,
        unique_code=code,
        venue_type=venue_type,
        seed=args.seed,
        as_of_ms=now_ms,
        simulation_iterations=args.iterations,
        simulation_horizon=args.horizon,
    )
    print(render_same_data(cmp))
    return 0 if cmp.identical else 1


# --------------------------------------------------------------------------- #
# Kiểu B -- live now vs the on-disk crawl, classified rather than equated.
# --------------------------------------------------------------------------- #

GROUP_SAME = "MATCH"
GROUP_TIME = "TIME"
GROUP_DRIFT = "DATA DRIFT"
GROUP_ANOMALY = "ANOMALY"
GROUP_ORDER = (GROUP_SAME, GROUP_TIME, GROUP_DRIFT, GROUP_ANOMALY)

# Fields that drift purely with the calendar (OKX's own leadDays counter keeps
# advancing every day whether or not the bot places a single new trade) --
# NOT the same set as SAME_DATA_TIME_FIELDS above, which is about the BotResult
# schema; this one is about BotEvaluationRow.
TIME_ONLY_FIELDS = {"declared_lead_days"}

# Fields that describe the market Logic 1 observed, not the bot itself --
# expected to differ every single time live is compared to any past crawl,
# since price/orderbook/flow move continuously. A diff confined to these
# fields (plus TIME_ONLY_FIELDS) is "the market changed", not a bug.
MARKET_FIELDS = {
    "market",
    "market_available",
    "market_resolution",
    "universe_eligible",
    "eligibility_reason",
}


@dataclass
class BotComparison:
    unique_code: str
    nick_name: str
    group: str
    explanation: str
    file_tier: Optional[str]
    live_tier: Optional[str]
    tier_changed: bool
    diffs: List[Tuple[str, Any, Any]] = field(default_factory=list)


def classify_bot_comparison(
    file_row: BotEvaluationRow, live_row: BotEvaluationRow
) -> BotComparison:
    """Bucket one bot's file-scan vs live-scan BotEvaluationRow.

    Deliberately conservative: DỮ LIỆU TRÔI is only assigned when there is a
    concrete, citable cause (the trade count moved, or only market-state
    fields moved) for every differing field. Anything left over after that --
    including "trade_count is identical yet other numbers changed" -- is
    BẤT THƯỜNG, per this project's explicit instruction to never mislabel an
    unexplained difference as drift.
    """
    nick_name = live_row.nick_name or file_row.nick_name or file_row.unique_code
    tier_changed = file_row.risk_tier != live_row.risk_tier

    if (
        file_row.error
        or live_row.error
        or file_row.status == "FAILED"
        or live_row.status == "FAILED"
    ):
        return BotComparison(
            unique_code=file_row.unique_code,
            nick_name=nick_name,
            group=GROUP_ANOMALY,
            explanation=(
                "One of the two paths could not fetch data to evaluate "
                f"(file: {file_row.error or 'ok'}; live: {live_row.error or 'ok'})."
            ),
            file_tier=file_row.risk_tier,
            live_tier=live_row.risk_tier,
            tier_changed=tier_changed,
        )

    diffs = [
        d
        for d in _flatten_diffs(
            file_row.model_dump(mode="json"), live_row.model_dump(mode="json")
        )
        # `rank` is this row's position in a list sorted by tier/score across
        # the whole cohort -- it can shift from a neighbour's tiny score move
        # without this bot's own evidence changing at all, so it says nothing
        # about this bot on its own and would only add noise here.
        if _top_field(d[0]) != "rank"
    ]
    if not diffs:
        return BotComparison(
            unique_code=file_row.unique_code,
            nick_name=nick_name,
            group=GROUP_SAME,
            explanation="Exact match.",
            file_tier=file_row.risk_tier,
            live_tier=live_row.risk_tier,
            tier_changed=tier_changed,
            diffs=diffs,
        )

    top_fields = {_top_field(path) for path, _, _ in diffs}

    if top_fields <= TIME_ONLY_FIELDS:
        return BotComparison(
            unique_code=file_row.unique_code,
            nick_name=nick_name,
            group=GROUP_TIME,
            explanation=(
                f"Only {', '.join(sorted(top_fields))} differs -- due to time "
                "passing (OKX increments it every day), not the data."
            ),
            file_tier=file_row.risk_tier,
            live_tier=live_row.risk_tier,
            tier_changed=tier_changed,
            diffs=diffs,
        )

    if top_fields <= (TIME_ONLY_FIELDS | MARKET_FIELDS):
        changed_market = sorted(top_fields & MARKET_FIELDS)
        return BotComparison(
            unique_code=file_row.unique_code,
            nick_name=nick_name,
            group=GROUP_DRIFT,
            explanation=(
                f"Only the market differs ({', '.join(changed_market)}) -- the "
                "market has changed since the file was crawled, not a bug on the "
                "bot side."
            ),
            file_tier=file_row.risk_tier,
            live_tier=live_row.risk_tier,
            tier_changed=tier_changed,
            diffs=diffs,
        )

    trade_delta = (live_row.trade_count or 0) - (file_row.trade_count or 0)
    if trade_delta != 0:
        return BotComparison(
            unique_code=file_row.unique_code,
            nick_name=nick_name,
            group=GROUP_DRIFT,
            explanation=(
                f"The bot closed {trade_delta:+d} more trades since the file was "
                "crawled -- this explains the differences in the performance/risk "
                "metrics below."
            ),
            file_tier=file_row.risk_tier,
            live_tier=live_row.risk_tier,
            tier_changed=tier_changed,
            diffs=diffs,
        )

    return BotComparison(
        unique_code=file_row.unique_code,
        nick_name=nick_name,
        group=GROUP_ANOMALY,
        explanation=(
            "trade_count is identical but other metrics differ "
            f"({', '.join(sorted(top_fields))}) with no explanation from time, "
            "market or new trades -- needs a closer look."
        ),
        file_tier=file_row.risk_tier,
        live_tier=live_row.risk_tier,
        tier_changed=tier_changed,
        diffs=diffs,
    )


def compare_cohorts(
    file_rows: Sequence[BotEvaluationRow], live_rows: Sequence[BotEvaluationRow]
) -> List[BotComparison]:
    file_by_code = {row.unique_code: row for row in file_rows}
    live_by_code = {row.unique_code: row for row in live_rows}
    results: List[BotComparison] = []
    for code in sorted(set(file_by_code) | set(live_by_code)):
        file_row, live_row = file_by_code.get(code), live_by_code.get(code)
        if file_row is None or live_row is None:
            only_where = "live" if file_row is None else "file"
            row = live_row or file_row
            results.append(
                BotComparison(
                    unique_code=code,
                    nick_name=row.nick_name if row else code,
                    group=GROUP_ANOMALY,
                    explanation=f"Bot only appears on the {only_where} path, not the other one.",
                    file_tier=file_row.risk_tier if file_row else None,
                    live_tier=live_row.risk_tier if live_row else None,
                    tier_changed=True,
                )
            )
            continue
        results.append(classify_bot_comparison(file_row, live_row))
    return results


def render_live_vs_file(
    comparisons: Sequence[BotComparison], generated_at_ms: int
) -> str:
    columns = (
        ("BOT", 22),
        ("GROUP", 14),
        ("TIER FILE", 11),
        ("TIER LIVE", 11),
        ("EXPLANATION", 58),
    )
    lines = _header(
        columns,
        "TYPE B COMPARISON -- LIVE NOW vs CRAWLED FILE (STEP 3)",
        f"{_stamp(generated_at_ms)} | {len(comparisons)} bots | "
        "groups: MATCH / TIME / DATA DRIFT / ANOMALY",
    )
    width = len(lines[4])
    counts = {g: 0 for g in GROUP_ORDER}
    for cmp in comparisons:
        counts[cmp.group] = counts.get(cmp.group, 0) + 1
        mark = " ⚠ TIER CHANGED" if cmp.tier_changed else ""
        lines.append(
            " ".join(
                [
                    _cell(cmp.nick_name, 22),
                    _cell(cmp.group, 14),
                    _cell(cmp.file_tier, 11),
                    _cell(cmp.live_tier, 11),
                ]
            )
        )
        # The explanation is the point of the row, so it wraps rather than
        # truncates -- same convention render_qc_ranking uses for its own
        # per-bot narrative lines.
        lines.extend(_wrap(f"↳ {cmp.explanation}{mark}", width - 6, "     "))

    lines.append("-" * width)
    lines.append(
        "Summary: " + " · ".join(f"{g} {counts.get(g, 0)}" for g in GROUP_ORDER)
    )
    changed = [c for c in comparisons if c.tier_changed]
    if changed:
        lines.append(f"TIER CHANGED BETWEEN THE TWO PATHS ({len(changed)} bots):")
        for c in changed:
            lines.append(
                f"  - {c.nick_name} ({c.unique_code}): {c.file_tier} -> {c.live_tier}; {c.explanation}"
            )
    else:
        lines.append("No bot changed risk_tier between the two paths.")

    anomalies = counts.get(GROUP_ANOMALY, 0)
    lines.append("=" * width)
    if anomalies:
        lines.append(
            f"CONCLUSION: the live architecture is NOT yet fully equivalent to file -- "
            f"{anomalies}/{len(comparisons)} bots fall into the ANOMALY group, needing a "
            "closer look before trusting the live results."
        )
    else:
        lines.append(
            "CONCLUSION: the live architecture gives results equivalent to file across "
            f"all {len(comparisons)} bots -- every difference is explained by time or "
            "data drift; the ANOMALY group is empty."
        )
    return "\n".join(lines)


def run_live_vs_file(args: argparse.Namespace) -> int:
    data_dir = Path(config.DATA_DIR)
    mode = EvaluationMode.SNAPSHOT
    only_codes = default_selection_codes(data_dir, bot=args.bot, all_bots=False)
    # Pinned once and handed to both scans: EvaluationMode.SNAPSHOT grades
    # freshness relative to `now`, so leaving each scan to default to its own
    # time.time() would add a spurious few seconds of "drift" between two
    # runs that are supposed to be compared apples-to-apples.
    now_ms = int(time.time() * 1000)

    label = f"{len(only_codes)} selected bots" if only_codes else "all crawled bots"
    print(f"[live-vs-file] Comparing on {label}.", file=sys.stderr)

    print(
        "[live-vs-file] [FILE] Scoring with already-crawled data...", file=sys.stderr
    )
    file_cohort = CohortAssessmentService(data_dir, mode).scan(
        as_of_ms=now_ms,
        seed=args.seed,
        simulation_iterations=args.iterations,
        simulation_horizon=args.horizon,
        only_codes=only_codes,
    )

    print("[live-vs-file] [LIVE] Scoring directly against OKX...", file=sys.stderr)
    bot_source, market_source = build_live_sources()
    live_service = CohortAssessmentService(data_dir, mode)
    apply_live_source(
        live_service,
        data_dir=data_dir,
        mode=mode,
        bot_source=bot_source,
        market_source=market_source,
    )
    try:
        live_cohort = live_service.scan(
            as_of_ms=now_ms,
            seed=args.seed,
            simulation_iterations=args.iterations,
            simulation_horizon=args.horizon,
            only_codes=only_codes,
        )
    except BotSourceError as exc:
        print(f"Error scoring live via OKX: {exc}", file=sys.stderr)
        return 1
    except MarketDataUnavailableError as exc:
        # Defensive only -- CohortAssessmentService._resolve_market already
        # catches this per bot; see run_report.py's own note on the same point.
        print(f"Market error scoring live via OKX: {exc}", file=sys.stderr)
        return 1

    comparisons = compare_cohorts(file_cohort.rows, live_cohort.rows)
    print(render_live_vs_file(comparisons, now_ms))
    return 0 if not any(c.group == GROUP_ANOMALY for c in comparisons) else 1


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove the live data-source architecture (Agent/backend/sources) "
            "works correctly, via two comparisons: same-data (same data, two "
            "processing paths must match exactly) and live-vs-file (live now "
            "vs a crawled file, classifying differences instead of demanding "
            "a match)."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("same-data", "live-vs-file"),
        required=True,
    )
    parser.add_argument(
        "--bot",
        help=(
            "uniqueCode. Required with --mode same-data. With --mode "
            "live-vs-file, narrows the comparison to a single bot instead of "
            "all 30 selected bots."
        ),
    )
    # Cùng hằng số lượt chấm thật dùng, không chép lại con số: hai bản viết
    # tay bằng nhau hôm nay vẫn trôi khỏi nhau ngày mai, và khi đó bản so
    # sánh "file vs live" sẽ đo bằng thước khác thước sản xuất mà không ai
    # thấy.
    parser.add_argument("--seed", type=int, default=PRODUCTION_SIMULATION_SEED)
    parser.add_argument(
        "--iterations", type=int, default=PRODUCTION_SIMULATION_ITERATIONS
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=PRODUCTION_SIMULATION_HORIZON,
        help="trades per Monte Carlo scenario; leave blank to use the bot's own trade count",
    )
    args = parser.parse_args(argv)

    if args.mode == "same-data":
        if not args.bot:
            parser.error("--mode same-data requires --bot <uniqueCode>")
        return run_same_data(args)
    return run_live_vs_file(args)


if __name__ == "__main__":
    raise SystemExit(main())
