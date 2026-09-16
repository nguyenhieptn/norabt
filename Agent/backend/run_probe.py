"""CLI chẩn đoán: OKX connect được chưa, và tương tác được không.

    python3 -m Agent.backend.run_probe                       # public + private
    python3 -m Agent.backend.run_probe --copy-trading         # + dry-run copy trading
    python3 -m Agent.backend.run_probe --copy-trading --execute   # gọi thật (chỉ demo)

Chạy từ /home/ubuntu/norabt. Không gọi run_report.py (nặng, ~4 phút) -- công cụ
này chỉ gọi vài request public/private nhẹ, có nghỉ giữa các lần gọi để tôn
trọng giới hạn 5 request/2 giây của nhóm endpoint copytrading.
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

from Agent.backend.infra.config import config
from Agent.backend.okx.probe import (
    LiveTradingRefused,
    check_private_access,
    check_public_access,
    probe_copy_trading,
)

_RULE_WIDTH = 78


def _rule(char: str = "=") -> str:
    return char * _RULE_WIDTH


def _section(title: str) -> None:
    print()
    print(_rule())
    print(title)
    print(_rule())


def _mark(ok: Any) -> str:
    if ok is True:
        return "✓"  # ✓
    if ok is False:
        return "✗"  # ✗
    return "?"


def _print_public(result: Dict[str, Any]) -> None:
    _section("[1] CONNECT ĐƯỢC SÀN CHƯA? (public, không cần API key)")
    for check in result["checks"]:
        latency = (
            f"{check['latency_ms']:.0f} ms" if check["latency_ms"] is not None else "-"
        )
        print(
            f"{_mark(check['ok'])} {check['name']} -- {check['endpoint']} ({latency})"
        )
        if not check["ok"]:
            print(f"    CẦN LÀM: {check['detail']}")

    skew = result["clock_skew_ms"]
    if skew is None:
        print(f"{_mark(None)} Lệch đồng hồ so với server OKX: không đo được.")
    else:
        ok = result["clock_skew_ok"]
        print(f"{_mark(ok)} Lệch đồng hồ so với server OKX: {skew:+.1f} ms")
        if not ok:
            print(
                "    CẦN LÀM: lệch >= 30 giây (30000 ms), OKX sẽ từ chối mọi "
                "request đã ký (code 50102). Đồng bộ lại giờ hệ thống (NTP) "
                "trước khi debug bất cứ lỗi chữ ký nào."
            )

    status = result["status"]
    if status == "OK":
        print("KẾT LUẬN: connect được sàn OKX ở mức public.")
    elif status == "LOI_MOT_PHAN":
        print(
            "KẾT LUẬN: connect được một phần -- một số endpoint public đang lỗi (xem trên)."
        )
    else:
        print("KẾT LUẬN: CHƯA connect được sàn OKX (toàn bộ endpoint public đều lỗi).")


def _print_private(result: Dict[str, Any]) -> None:
    _section("[2] TƯƠNG TÁC ĐƯỢC KHÔNG? -- KEY OKX (private, chỉ đọc, không đặt lệnh)")
    status = result["status"]
    if status == "CHUA_CAU_HINH":
        print(f"{_mark(False)} Chưa cấu hình key OKX.")
        print(f"    Thiếu biến môi trường: {', '.join(result['missing_fields'])}")
        print(
            "    CẦN LÀM: điền các biến trên vào Agent/.env (xem Agent/.env.example)."
        )
        return

    env = result.get("environment", "?")
    if status == "OK":
        print(f"{_mark(True)} Key hoạt động trên môi trường {env}.")
        print(f"    {result['message_vi']}")
    elif status == "LOI_KET_NOI":
        print(f"{_mark(False)} Không kết nối được tới OKX (môi trường {env}).")
        print(f"    CẦN LÀM: {result['message_vi']}")
    else:  # LOI -- OKX answered and rejected the key
        print(f"{_mark(False)} OKX từ chối key (môi trường {env}).")
        print(f"    Mã lỗi: {result['error_code']} -- {result['message_vi']}")


def _print_copy_trading(result: Dict[str, Any], *, executed: bool) -> None:
    mode = "GỌI THẬT" if executed else "DRY-RUN (chỉ xem trước, chưa gọi mạng)"
    _section(f"[3] TƯƠNG TÁC COPY TRADING -- {mode}")
    status = result["status"]

    if status == "DRY_RUN":
        call = result["would_call"]
        print(f"Sẽ gọi: {call['method']} {call['endpoint']}")
        print(f"Body: {call['body']}")
        print(f"Header (đã che secret): {call['headers']}")
        print(f"{result['message_vi']}")
        return

    if status == "CHUA_CAU_HINH":
        print(f"{_mark(False)} Chưa cấu hình key OKX.")
        print(f"    Thiếu biến môi trường: {', '.join(result['missing_fields'])}")
        print(
            "    CẦN LÀM: điền các biến trên vào Agent/.env rồi chạy lại với --execute."
        )
        return

    if status == "LOI_KET_NOI":
        print(f"{_mark(False)} Không gọi được OKX.")
        print(f"    CẦN LÀM: {result['message_vi']}")
        return

    if status == "DEMO_KHONG_HO_TRO":
        print(f"{_mark(True)} Có câu trả lời: {result['message_vi']}")
        print(f"    Mã lỗi OKX: {result['code']} (msg gốc: {result['raw_msg']!r})")
        return

    if status == "DEMO_CO_HO_TRO":
        print(f"{_mark(True)} Có câu trả lời: {result['message_vi']}")
        print(f"    !!! {result['canh_bao']}")
        return

    if status == "MA_LOI_KHAC":
        print(f"{_mark(False)} {result['message_vi']}")
        return

    print(f"{_mark(False)} Trạng thái không xác định: {result}")


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m Agent.backend.run_probe",
        description="Chẩn đoán kết nối và khả năng tương tác với OKX.",
    )
    parser.add_argument(
        "--copy-trading",
        action="store_true",
        help="Thêm probe_copy_trading (mặc định dry-run, không gọi mạng).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Gọi copy trading thật thay vì dry-run (chỉ chạy được trên demo).",
    )
    args = parser.parse_args(argv)
    if args.execute and not args.copy_trading:
        parser.error("--execute chỉ có ý nghĩa khi đi cùng --copy-trading")

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    print(_rule())
    print("CHẨN ĐOÁN KẾT NỐI & TƯƠNG TÁC OKX")
    print(now)
    # Hiển thị đường dẫn tương đối cho gọn (vd. "Agent/.env") khi chạy từ gốc
    # repo; rơi về đường dẫn tuyệt đối nếu không tính được đường tương đối.
    try:
        env_file_display = os.path.relpath(config.ENV_FILE_PATH)
    except ValueError:
        env_file_display = config.ENV_FILE_PATH
    if config.ENV_FILE_LOADED:
        print(
            f"Nguồn cấu hình: {env_file_display} "
            f"(đã nạp {config.ENV_FILE_VARS_LOADED} biến)"
        )
    else:
        print(
            f"Nguồn cấu hình: không thấy {env_file_display}, chỉ dùng biến môi trường"
        )
    print(_rule())

    public_result = check_public_access()
    _print_public(public_result)

    time.sleep(0.5)
    private_result = check_private_access()
    _print_private(private_result)

    exit_code = 0
    if public_result["status"] == "LOI":
        exit_code = 1

    if args.copy_trading:
        time.sleep(0.5)
        try:
            copy_result = probe_copy_trading(dry_run=not args.execute)
        except LiveTradingRefused as exc:
            _section("[3] TƯƠNG TÁC COPY TRADING")
            print(f"{_mark(False)} TỪ CHỐI CHẠY: {exc}")
            return 2
        _print_copy_trading(copy_result, executed=args.execute)

    print()
    print(_rule())
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
