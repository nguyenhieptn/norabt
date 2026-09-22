"""CLI entry point for the risk-supervisor web dashboard.

    python3 -m Agent.backend.scripts.run_web                       # 127.0.0.1:8770
    python3 -m Agent.backend.scripts.run_web --port 9000
    python3 -m Agent.backend.scripts.run_web --dashboard /duong/dan/toi/dashboard.html

Mirrors agent_server.py's own CLI shape (same --host default and the same
"binding 0.0.0.0 must never happen silently" rule -- see that module's
`main()`) since both are the same kind of thing: a small HTTP surface over
this project's risk data, with no authentication of its own yet.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

import uvicorn

from Agent.backend.web.app import DEFAULT_DASHBOARD_PATH, create_app

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8770

# Read by --dashboard's own default so an operator can set it once in the
# environment (systemd unit, docker-compose) instead of on every invocation.
ENV_DASHBOARD_PATH = "NORABT_WEB_DASHBOARD"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m Agent.backend.scripts.run_web",
        description=(
            "Web service for monitoring OKX copy-trading bot risk (HTML "
            "dashboard + JSON API, running on Starlette/uvicorn)."
        ),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=(
            f"Defaults to {DEFAULT_HOST} (reachable only from this machine). "
            "Use 0.0.0.0 to open it on every network interface -- only do "
            "this behind a trusted reverse proxy/firewall, since the server "
            "has no authentication of its own yet."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Defaults to {DEFAULT_PORT}.",
    )
    parser.add_argument(
        "--dashboard",
        default=os.environ.get(ENV_DASHBOARD_PATH),
        help=(
            "Path to the dashboard HTML file. Defaults to the "
            f"{ENV_DASHBOARD_PATH} environment variable if set, otherwise "
            f"{DEFAULT_DASHBOARD_PATH}. If the file doesn't exist, the GET / "
            "route still runs and returns a minimal error page instead of crashing."
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _build_arg_parser().parse_args(argv)
    dashboard_path = Path(args.dashboard) if args.dashboard else DEFAULT_DASHBOARD_PATH

    if args.host == "0.0.0.0":
        # A hard requirement from the plan, matching agent_server.py's own
        # rule for --transport http: binding every interface must never
        # happen silently. This server also runs a live risk-scoring
        # pipeline (POST /api/analyze) that costs real CPU and a shared OKX
        # rate-limit budget per call, on top of having no auth of its own.
        print(
            "WARNING: the server is listening on EVERY network interface "
            "(0.0.0.0) and has NO authentication mechanism -- any machine that "
            f"can reach port {args.port} can call the entire API, including "
            "POST /api/analyze (costs CPU + shared OKX call budget each time). "
            "Only use this behind a trusted reverse proxy/firewall/auth layer; "
            "otherwise use --host 127.0.0.1 (default) or an internal address.",
            file=sys.stderr,
        )

    print("=" * 70, file=sys.stderr)
    print(
        "[web] Risk Supervisor -- OKX copy-trading bot monitoring dashboard",
        file=sys.stderr,
    )
    dashboard_note = (
        ""
        if dashboard_path.exists()
        else " (DOES NOT EXIST -- GET / will return a minimal error page)"
    )
    print(f"[web] Dashboard HTML : {dashboard_path}{dashboard_note}", file=sys.stderr)
    print(f"[web] Address        : http://{args.host}:{args.port}", file=sys.stderr)
    print(
        "[web] Routes         : GET / , GET /api/bots , GET /api/markets , "
        "GET /api/leaderboard , POST /api/analyze",
        file=sys.stderr,
    )
    print(
        "[web] Per-IP rate limiting on /api/analyze is enabled (protects CPU "
        "and the shared OKX call budget).",
        file=sys.stderr,
    )
    print("=" * 70, file=sys.stderr)

    app = create_app(dashboard_path=dashboard_path)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
