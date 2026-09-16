"""CLI entry point for the risk-supervisor web dashboard.

    python3 -m Agent.backend.run_web                       # 127.0.0.1:8770
    python3 -m Agent.backend.run_web --port 9000
    python3 -m Agent.backend.run_web --dashboard /duong/dan/toi/dashboard.html

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
        prog="python3 -m Agent.backend.run_web",
        description=(
            "Web service giám sát rủi ro bot copy-trading OKX (dashboard HTML "
            "+ API JSON, chạy trên Starlette/uvicorn)."
        ),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=(
            f"Mặc định {DEFAULT_HOST} (chỉ máy này gọi được). Dùng 0.0.0.0 để "
            "mở ra mọi interface mạng -- chỉ làm vậy sau reverse proxy/tường "
            "lửa đáng tin cậy, vì server chưa có xác thực."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Mặc định {DEFAULT_PORT}.",
    )
    parser.add_argument(
        "--dashboard",
        default=os.environ.get(ENV_DASHBOARD_PATH),
        help=(
            "Đường dẫn tới file HTML dashboard. Mặc định lấy từ biến môi "
            f"trường {ENV_DASHBOARD_PATH} nếu có, nếu không dùng "
            f"{DEFAULT_DASHBOARD_PATH}. Nếu file không tồn tại, route GET / "
            "vẫn chạy và trả một trang báo lỗi tối giản thay vì crash."
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
            "CẢNH BÁO: server đang lắng nghe trên MỌI interface mạng (0.0.0.0) "
            "và CHƯA có cơ chế xác thực -- bất kỳ máy nào truy cập được cổng "
            f"{args.port} đều gọi được toàn bộ API, kể cả POST /api/analyze "
            "(tốn CPU + hạn mức gọi OKX mỗi lần). Chỉ dùng khi đã có reverse "
            "proxy/tường lửa/xác thực đáng tin cậy phía trước; nếu không, "
            "hãy dùng --host 127.0.0.1 (mặc định) hoặc một địa chỉ nội bộ.",
            file=sys.stderr,
        )

    print("=" * 70, file=sys.stderr)
    print(
        "[web] Risk Supervisor -- dashboard giám sát bot copy-trading OKX",
        file=sys.stderr,
    )
    dashboard_note = (
        ""
        if dashboard_path.exists()
        else " (KHÔNG TỒN TẠI -- GET / sẽ trả trang báo lỗi tối giản)"
    )
    print(f"[web] Dashboard HTML : {dashboard_path}{dashboard_note}", file=sys.stderr)
    print(f"[web] Địa chỉ        : http://{args.host}:{args.port}", file=sys.stderr)
    print(
        "[web] Route          : GET / , GET /api/bots , GET /api/markets , "
        "GET /api/leaderboard , POST /api/analyze",
        file=sys.stderr,
    )
    print(
        "[web] Giới hạn tần suất /api/analyze theo IP đã bật (bảo vệ CPU và "
        "hạn mức gọi OKX dùng chung).",
        file=sys.stderr,
    )
    print("=" * 70, file=sys.stderr)

    app = create_app(dashboard_path=dashboard_path)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
