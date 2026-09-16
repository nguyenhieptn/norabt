"""Diagnostic probes answering two questions a human keeps asking, not a test suite.

    1. "Connect được sàn chưa?"      -> check_public_access()
    2. "Tương tác được trên đó không?" -> check_private_access(), probe_copy_trading()

This module deliberately does NOT call `OkxClient.get()` / `.post()` /
`.public_get()` for the actual network round trip, even though it reuses
everything else from that client (credentials, signing, the fail-closed
`headers()` guard). Two things were found by hand while building this probe
that make the production `_send()` unsuitable for a diagnostic tool:

  * OKX's edge answers a request carrying Python's default urllib
    User-Agent ("Python-urllib/x.y") with a bare HTTP 403, before any OKX
    business logic runs -- confirmed by sending the identical request with
    only the User-Agent header changed. `OkxClient` never sets one, so every
    call made through it fails this way in this environment. Fixing that
    inside client.py is out of scope for this task (it is shared with the
    live-trading agent), so this module sets its own User-Agent on the one
    request object it builds itself.
  * `OkxClient._send()` has a `try/except HTTPError/.../else` shape where the
    `else` branch (which extracts OKX's real `{code, msg}` body) only runs
    when the `try` block raised nothing at all. When OKX answers a business
    error with a non-2xx HTTP status -- observed for real: a bad API key
    returns HTTP 401 with body `{"code":"50111",...}` -- that body lands in
    the `except HTTPError` branch, is read into `raw`, and then discarded:
    the loop just retries and eventually raises a generic
    `OkxTransportError(...: None)`. That throws away exactly the information
    (`50102`/`50111`/`50038`/...) this probe exists to report, so the
    single-shot HTTP call below parses the body from *either* branch itself
    instead of inheriting that behaviour.
  * This host's IPv6 route to OKX/Cloudflare is blackholed: a SYN to either
    of the IPv6 addresses OKX's DNS returns gets no answer and no ICMP
    unreachable, while the IPv4 address answers in well under 100ms
    (verified by connecting to each address family directly). `getaddrinfo()`
    lists the IPv6 addresses first, and `socket.create_connection()` (what
    every stdlib HTTP client, including `OkxClient`, sits on top of) blocks
    for the *full* connect timeout on each dead address before moving to the
    next one -- turning every single request into a ~20s stall instead of an
    instant IPv4 connect. `_prefer_ipv4()` below scopes `getaddrinfo()` to
    AF_INET only for the duration of one call so this probe stays fast; it
    does not hardcode the `OKX_CLOUDFLARE_IPV4` address from config.py (DNS
    still resolves normally, only the address family is constrained), and it
    does not touch `OkxClient`. The same stall affects the live-trading
    agent's own OKX calls on this host and is worth fixing there too.

Both of the first two are transport-level workarounds, not changes to OKX's
signing or retry semantics, and none of the three touches
`Agent/backend/okx/client.py`.
"""

from __future__ import annotations

import contextlib
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from Agent.backend.infra.config import config
from Agent.backend.okx.client import OkxClient, OkxCredentialsMissing
from Agent.backend.okx.credentials import OkxCredentials

# Identifies this tool in OKX's access logs and -- more importantly -- is
# simply *not* the default urllib string that gets a blanket 403 (see module
# docstring). The exact value doesn't matter to OKX, only that it isn't blank
# and isn't the Python default.
PROBE_USER_AGENT = "norabt-okx-probe/1.0"

# OKX documents (and this probe has independently reproduced) that a request
# timestamp more than 30 seconds off the server's clock is rejected outright
# with code 50102. Surfacing the skew here, before any signed call is even
# attempted, turns a confusing signature failure into an obvious "fix your
# system clock" finding.
OKX_CLOCK_SKEW_LIMIT_MS = 30_000

# Pacing between requests so a full probe run never bursts past OKX's
# 5-requests-per-2-seconds limit on the copytrading endpoint group -- the
# group this probe spends most of its calls in.
_REQUEST_DELAY_SECONDS = 0.5

# Vietnamese translations of the OKX v5 error codes this probe can realistically
# hit, taken verbatim (in meaning) from OKX's own REST API error-code reference
# (https://www.okx.com/docs-v5/en/#error-code-rest-api-public and
# .../#error-code-rest-api-copy-trading, fetched 2026-09-14) -- not guessed.
# Codes not in this table are reported with their raw code/msg rather than an
# invented explanation; see explain_error_vi().
OKX_ERROR_MESSAGES_VI: Dict[str, str] = {
    "0": "Thành công.",
    "50035": (
        "Endpoint này bắt buộc API key phải được gán (bind) một IP cụ thể "
        "trước khi dùng -- vào OKX gán IP cho key."
    ),
    "50038": "Tính năng này không khả dụng ở môi trường demo trading.",
    "50100": "API key đã bị đóng băng -- cần liên hệ bộ phận hỗ trợ của OKX.",
    "50101": (
        "API key không khớp với môi trường hiện tại (ví dụ: key tạo cho demo "
        "nhưng gọi vào live, hoặc ngược lại) -- đối chiếu lại OKX_SIMULATED "
        "với loại key đã tạo trên OKX."
    ),
    "50102": (
        "Timestamp bị từ chối vì lệch quá 30 giây so với đồng hồ server OKX "
        "-- đồng bộ lại giờ hệ thống (NTP); check_public_access() báo "
        "clock_skew_ms để phát hiện việc này trước khi ký request."
    ),
    "50103": 'Header "OK-ACCESS-KEY" bị trống.',
    "50104": 'Header "OK-ACCESS-PASSPHRASE" bị trống.',
    "50105": (
        'Header "OK-ACCESS-PASSPHRASE" sai -- kiểm tra lại biến môi trường '
        "OKX_API_PASSPHRASE."
    ),
    "50106": 'Header "OK-ACCESS-SIGN" bị trống.',
    "50107": 'Header "OK-ACCESS-TIMESTAMP" bị trống hoặc sai định dạng.',
    "50110": (
        "Địa chỉ IP hiện tại không nằm trong whitelist IP của API key -- vào "
        "OKX gán IP cho key hoặc gỡ giới hạn IP."
    ),
    "50111": (
        "OK-ACCESS-KEY không hợp lệ -- kiểm tra lại biến môi trường OKX_API_KEY."
    ),
    "50112": 'Header "OK-ACCESS-TIMESTAMP" không hợp lệ.',
    "50113": (
        "Chữ ký (signature) không hợp lệ -- kiểm tra lại biến môi trường "
        "OKX_API_SECRET (hoặc lệch đồng hồ, xem 50102)."
    ),
    "50114": "Uỷ quyền (authorization) không hợp lệ.",
}


class LiveTradingRefused(Exception):
    """Raised before any network call when a real order would be at stake.

    probe_copy_trading(dry_run=False)'s only executable action is creating a
    real copy-trading position sized at the exchange minimum. That is
    harmless on a demo account (fake money, fake book) and unacceptable on a
    live one (real money, a real position this probe did not ask permission
    to open). Refusing outright -- rather than warning and proceeding -- is
    the only way a stray `dry_run=False` can never reach a live key by
    accident.
    """


@dataclass
class _CallResult:
    """One HTTP round trip, reduced to what a diagnostic needs to say about it.

    `error` is set only for calls that never got an answer from OKX at all
    (DNS/timeout/connection refused); a business rejection (code != "0")
    still has `error=None` because OKX *did* answer -- that distinction is
    exactly what tells a caller whether "not connected" or "connected but
    rejected" is the right diagnosis.
    """

    ok: bool
    http_status: Optional[int]
    code: Optional[str]
    msg: Optional[str]
    data: Any
    latency_ms: Optional[float]
    error: Optional[str]


def explain_error_vi(code: Optional[str]) -> str:
    """Vietnamese meaning of an OKX v5 error code, from OKX_ERROR_MESSAGES_VI only.

    Never invents a meaning for a code this table doesn't cover -- an
    incorrect guess about what an error means is worse for debugging than an
    honest "don't know, go look it up".
    """
    if code is None:
        return "Không có mã lỗi cụ thể (không nhận được phản hồi hợp lệ từ OKX)."
    return OKX_ERROR_MESSAGES_VI.get(
        code,
        "Mã lỗi OKX chưa có trong bảng tra cứu nội bộ của probe -- tra cứu tại "
        f"https://www.okx.com/docs-v5/en/#error-code (code={code}).",
    )


def _sample_lead_trader() -> Optional[Dict[str, str]]:
    """One lead-trader uniqueCode to probe with, read from the curated universe.

    Deliberately not hardcoded: the roster of active leads changes with every
    crawl, and a hardcoded code would eventually point at someone who stopped
    leading, turning every future probe run into a false "connection broken"
    report instead of an honest "OKX rejected an unrelated stale code".
    """
    path = Path(config.DATA_DIR) / "universe" / "bot_selection.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for asset in payload.get("assets", []):
        top = asset.get("top") or {}
        code = top.get("code")
        if code:
            return {
                "code": str(code),
                "name": str(top.get("name", "")),
                "asset": str(asset.get("underlying", "")),
            }
    return None


def _mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact anything that could leak credential material from a header dict.

    This feeds probe_copy_trading's dry-run preview, which is meant to be
    pasted into a chat or a ticket verbatim -- it must be safe to share as-is,
    the same bar OkxCredentials.__repr__ holds itself to.
    """
    masked: Dict[str, str] = {}
    for key, value in headers.items():
        upper = key.upper()
        if upper in ("OK-ACCESS-SIGN", "OK-ACCESS-PASSPHRASE"):
            masked[key] = "***"
        elif upper == "OK-ACCESS-KEY":
            masked[key] = f"***{value[-4:]}" if len(value) > 4 else "***"
        else:
            masked[key] = value
    return masked


def _build_path(request_path: str, params: Optional[Dict[str, Any]]) -> str:
    if not params:
        return request_path
    return f"{request_path}?{urllib.parse.urlencode(params)}"


@contextlib.contextmanager
def _prefer_ipv4() -> Iterator[None]:
    """Scope one connection attempt to IPv4 only (see module docstring).

    Restores the original `socket.getaddrinfo` in `finally` no matter what
    happens inside, so a probe run can never leave process-wide socket
    behaviour altered.
    """
    original_getaddrinfo = socket.getaddrinfo

    def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = _ipv4_only
    try:
        yield
    finally:
        socket.getaddrinfo = original_getaddrinfo


def _call(
    client: OkxClient,
    method: str,
    request_path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    private: bool = False,
) -> _CallResult:
    """Single-shot HTTP call: no retries, real latency, real OKX error body.

    A diagnostic probe wants exactly one measured round trip per check and the
    unfiltered answer OKX gave -- not `OkxClient`'s production retry/backoff
    loop (built for order-safety, and see the module docstring for why it
    would also swallow the very error bodies this probe needs to report).
    """
    path = _build_path(request_path, params)
    method = method.upper()
    body_str = ""
    data: Optional[bytes] = None
    if method == "POST":
        body_str = json.dumps(body) if body else "{}"
        data = body_str.encode("utf-8")

    if private:
        # Reuses OkxClient's own signing + fail-closed guard verbatim; this
        # raises OkxCredentialsMissing if credentials are incomplete, which
        # every caller here has already checked before setting private=True.
        headers = dict(client.headers(method, path, body_str))
    else:
        headers = {}
    headers["User-Agent"] = PROBE_USER_AGENT

    url = f"{client.base_url}{path}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    started = time.monotonic()
    http_status: Optional[int] = None
    try:
        with _prefer_ipv4():
            with urllib.request.urlopen(request, timeout=client.timeout) as response:
                raw = response.read()
                http_status = response.status
    except urllib.error.HTTPError as exc:
        # OKX puts its real {code, msg} body here even on a non-2xx status
        # (a bad API key answers HTTP 401 + {"code":"50111",...}) -- read and
        # parsed below like any other response, not discarded.
        raw = exc.read()
        http_status = exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return _CallResult(
            ok=False,
            http_status=None,
            code=None,
            msg=None,
            data=None,
            latency_ms=(time.monotonic() - started) * 1000,
            error=str(exc),
        )

    latency_ms = (time.monotonic() - started) * 1000
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return _CallResult(
            ok=False,
            http_status=http_status,
            code=None,
            msg=None,
            data=None,
            latency_ms=latency_ms,
            error=f"Phản hồi không phải JSON hợp lệ: {exc}",
        )

    code = payload.get("code")
    return _CallResult(
        ok=code == "0",
        http_status=http_status,
        code=code,
        msg=payload.get("msg"),
        data=payload.get("data"),
        latency_ms=latency_ms,
        error=None,
    )


def _check_entry(name: str, endpoint: str, result: _CallResult) -> Dict[str, Any]:
    if result.error is not None:
        detail = f"Không gọi được: {result.error}"
    elif not result.ok:
        detail = (
            f"OKX trả lỗi code={result.code} (msg gốc: {result.msg!r}): "
            f"{explain_error_vi(result.code)}"
        )
    else:
        detail = "OK."
    return {
        "name": name,
        "endpoint": endpoint,
        "ok": result.ok,
        "latency_ms": round(result.latency_ms, 1)
        if result.latency_ms is not None
        else None,
        "detail": detail,
    }


def check_public_access() -> dict:
    """ "Connect được sàn chưa?" at the public level -- no API key required.

    Calls three real public endpoints, reports per-call latency, and computes
    the clock skew against OKX's server time. The skew matters on its own: OKX
    rejects any signed request timestamped more than 30s off (code 50102), so
    a bad system clock shows up here as a clean number instead of a confusing
    signature failure three checks later in check_private_access().
    """
    client = OkxClient(credentials=OkxCredentials())  # never signs anything
    checks: List[Dict[str, Any]] = []

    t_before = time.time()
    time_result = _call(client, "GET", "/api/v5/public/time")
    t_after = time.time()
    checks.append(
        _check_entry("Đồng hồ server OKX", "GET /api/v5/public/time", time_result)
    )

    clock_skew_ms: Optional[float] = None
    clock_skew_ok: Optional[bool] = None
    if time_result.ok and isinstance(time_result.data, list) and time_result.data:
        try:
            server_ms = float(time_result.data[0]["ts"])
        except (KeyError, TypeError, ValueError):
            server_ms = None
        if server_ms is not None:
            # Midpoint of the round trip is the best local reference point
            # available without a dedicated clock-sync protocol.
            local_ms = (t_before + t_after) / 2 * 1000
            clock_skew_ms = server_ms - local_ms
            clock_skew_ok = abs(clock_skew_ms) < OKX_CLOCK_SKEW_LIMIT_MS

    time.sleep(_REQUEST_DELAY_SECONDS)
    config_result = _call(client, "GET", "/api/v5/copytrading/public-config")
    checks.append(
        _check_entry(
            "Cấu hình copy trading công khai",
            "GET /api/v5/copytrading/public-config",
            config_result,
        )
    )

    time.sleep(_REQUEST_DELAY_SECONDS)
    sample = _sample_lead_trader()
    if sample is None:
        checks.append(
            {
                "name": "Vị thế công khai của một lead trader mẫu",
                "endpoint": "GET /api/v5/copytrading/public-current-subpositions",
                "ok": False,
                "latency_ms": None,
                "detail": (
                    "Không tìm thấy uniqueCode mẫu nào trong "
                    "Agent/data/universe/bot_selection.json."
                ),
            }
        )
    else:
        sub_result = _call(
            client,
            "GET",
            "/api/v5/copytrading/public-current-subpositions",
            params={"uniqueCode": sample["code"], "instType": "SWAP"},
        )
        checks.append(
            _check_entry(
                f"Vị thế công khai của lead trader mẫu ({sample['name'] or sample['code']})",
                "GET /api/v5/copytrading/public-current-subpositions",
                sub_result,
            )
        )

    ok_count = sum(1 for c in checks if c["ok"])
    if ok_count == len(checks):
        status = "OK"
    elif ok_count == 0:
        status = "LOI"
    else:
        status = "LOI_MOT_PHAN"

    return {
        "status": status,
        "checks": checks,
        "clock_skew_ms": round(clock_skew_ms, 1) if clock_skew_ms is not None else None,
        "clock_skew_ok": clock_skew_ok,
    }


def check_private_access() -> dict:
    """ "Key đã dùng được chưa?" -- read-only, never places or touches an order.

    Never raises: a caller running this specifically to find out what is
    missing must get a message back, not a traceback. That is also why the
    missing-credentials path is checked and returned *before* an OkxClient
    with those credentials is even built.
    """
    credentials = OkxCredentials.from_config()
    if not credentials.is_complete:
        missing = credentials.missing_fields
        return {
            "status": "CHUA_CAU_HINH",
            "missing_fields": missing,
            "message_vi": (
                "Chưa cấu hình đủ thông tin xác thực OKX, cần khai báo các biến "
                "môi trường: " + ", ".join(missing) + ". Xem hướng dẫn tại "
                "Agent/.env.example."
            ),
        }

    environment = "DEMO" if credentials.simulated else "LIVE"
    client = OkxClient(credentials=credentials)
    result = _call(client, "GET", "/api/v5/account/balance", private=True)

    if result.error is not None:
        return {
            "status": "LOI_KET_NOI",
            "environment": environment,
            "message_vi": f"Không kết nối được tới OKX để kiểm tra key: {result.error}",
        }

    if result.ok:
        balance_rows = len(result.data) if isinstance(result.data, list) else None
        detail = f"Key hoạt động bình thường trên môi trường {environment}."
        if balance_rows is not None:
            detail += f" Đọc được {balance_rows} dòng số dư."
        return {
            "status": "OK",
            "environment": environment,
            "latency_ms": round(result.latency_ms, 1)
            if result.latency_ms is not None
            else None,
            "message_vi": detail,
        }

    return {
        "status": "LOI",
        "environment": environment,
        "error_code": result.code,
        "error_message_raw": result.msg,
        "message_vi": (
            f"OKX từ chối yêu cầu (code={result.code}, msg gốc: {result.msg!r}): "
            f"{explain_error_vi(result.code)}"
        ),
    }


def probe_copy_trading(dry_run: bool = True) -> dict:
    """ "Tương tác được không?" -- the one question nobody has an answer to yet.

    OKX's own docs never say whether demo trading supports copy trading at
    all. The only way to find out is to send the real request and read the
    real error code: `50038` ("This feature is unavailable in demo trading")
    means no, `code == "0"` means yes -- and yes also means a real copy
    setting now exists and must be torn down.

    dry_run=True (the default) builds the exact request and returns it for
    inspection without making a single network call -- callers must opt in
    to dry_run=False to actually send it, and even then only against a demo
    key (see LiveTradingRefused).
    """
    credentials = OkxCredentials.from_config()
    sample = _sample_lead_trader()
    body_template: Dict[str, Any] = {
        "instType": "SWAP",
        "uniqueCode": sample["code"] if sample else "<không có uniqueCode mẫu>",
        # "copy" keeps the copied contracts identical to the lead trader's,
        # so this never needs an explicit instId list to stay in sync with.
        "copyInstIdType": "copy",
        "copyMgnMode": "cross",
        # Fixed amount (rather than ratio_copy) is what lets the probe size
        # the position by a single USDT number -- OKX's own minCopyAmt.
        "copyMode": "fixed_amount",
        "subPosCloseType": "copy_close",
    }

    if dry_run:
        preview_body = dict(body_template)
        preview_body["copyAmt"] = (
            "<minCopyAmt, đọc từ GET /api/v5/copytrading/public-config khi chạy thật>"
        )
        preview_body["copyTotalAmt"] = preview_body["copyAmt"]
        try:
            client = OkxClient(credentials=credentials)
            headers = client.headers(
                "POST",
                "/api/v5/copytrading/first-copy-settings",
                json.dumps(preview_body),
            )
            headers_preview = _mask_headers(headers)
        except OkxCredentialsMissing as exc:
            headers_preview = {"_chua_the_ky": str(exc)}
        return {
            "status": "DRY_RUN",
            "would_call": {
                "method": "POST",
                "endpoint": "/api/v5/copytrading/first-copy-settings",
                "body": preview_body,
                "headers": headers_preview,
            },
            "message_vi": (
                "Đây là bản xem trước (dry-run) -- CHƯA gọi mạng, chưa gửi gì tới "
                "OKX. Truyền dry_run=False để thực sự gửi request này (chỉ chạy "
                "được trên môi trường demo)."
            ),
        }

    # Everything below this line can place a real order on a real account.
    if not credentials.simulated:
        raise LiveTradingRefused(
            "Từ chối chạy probe_copy_trading(dry_run=False) với key LIVE "
            "(OKX_SIMULATED=false). Probe này tạo một copy-trading position "
            "thật trên tài khoản đang cấu hình -- chỉ được phép chạy trên "
            "demo. Đặt OKX_SIMULATED=true hoặc dùng bộ key demo để chạy."
        )

    if not credentials.is_complete:
        missing = credentials.missing_fields
        return {
            "status": "CHUA_CAU_HINH",
            "missing_fields": missing,
            "message_vi": (
                "Chưa cấu hình đủ thông tin xác thực OKX, cần khai báo các biến "
                "môi trường: " + ", ".join(missing) + "."
            ),
        }

    if sample is None:
        return {
            "status": "LOI",
            "message_vi": (
                "Không tìm thấy uniqueCode mẫu nào trong "
                "Agent/data/universe/bot_selection.json để thử copy."
            ),
        }

    client = OkxClient(credentials=credentials)
    config_result = _call(client, "GET", "/api/v5/copytrading/public-config")
    if not config_result.ok:
        detail = config_result.error or explain_error_vi(config_result.code)
        return {
            "status": "LOI",
            "message_vi": f"Không đọc được minCopyAmt từ public-config: {detail}",
        }
    try:
        min_copy_amt = config_result.data[0]["minCopyAmt"]
    except (KeyError, IndexError, TypeError):
        return {
            "status": "LOI",
            "message_vi": "public-config không trả về trường minCopyAmt như mong đợi.",
        }

    time.sleep(_REQUEST_DELAY_SECONDS)

    body = dict(body_template)
    body["copyAmt"] = min_copy_amt
    body["copyTotalAmt"] = min_copy_amt
    request_sent = {
        "method": "POST",
        "endpoint": "/api/v5/copytrading/first-copy-settings",
        "body": body,
    }

    result = _call(
        client,
        "POST",
        "/api/v5/copytrading/first-copy-settings",
        body=body,
        private=True,
    )

    if result.error is not None:
        return {
            "status": "LOI_KET_NOI",
            "message_vi": f"Không gọi được first-copy-settings: {result.error}",
            "request_sent": request_sent,
        }

    if result.code == "50038":
        return {
            "status": "DEMO_KHONG_HO_TRO",
            "code": result.code,
            "raw_msg": result.msg,
            "message_vi": (
                "Demo KHÔNG hỗ trợ copy trading (OKX trả mã lỗi 50038: tính năng "
                "không khả dụng ở demo trading). Đây là câu trả lời có giá trị, "
                "không phải một lần chạy thất bại."
            ),
            "request_sent": request_sent,
        }

    if result.code == "0":
        unique_code = body["uniqueCode"]
        return {
            "status": "DEMO_CO_HO_TRO",
            "code": result.code,
            "message_vi": "Demo CÓ hỗ trợ copy trading -- OKX đã chấp nhận yêu cầu.",
            "canh_bao": (
                f"ĐÃ THỰC SỰ TẠO COPY SETTING trên demo với lead trader "
                f"{unique_code}. Phải gỡ ngay bằng POST "
                "/api/v5/copytrading/stop-copy-trading với body "
                f'{{"instType": "SWAP", "uniqueCode": "{unique_code}", '
                '"subPosCloseType": "manual_close"}.'
            ),
            "request_sent": request_sent,
        }

    return {
        "status": "MA_LOI_KHAC",
        "code": result.code,
        "raw_msg": result.msg,
        "message_vi": (
            f"OKX trả về mã lỗi khác (code={result.code}, msg gốc: {result.msg!r}) "
            "-- không đoán ý nghĩa, tra cứu tại "
            "https://www.okx.com/docs-v5/en/#error-code-rest-api-copy-trading."
        ),
        "request_sent": request_sent,
    }
