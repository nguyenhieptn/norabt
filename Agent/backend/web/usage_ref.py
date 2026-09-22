"""Mã lượt-dùng (usage ref) cho link chi tiết ẩn danh của `POST /api/analyze`.

BỐI CẢNH BẮT BUỘC PHẢI CÓ MODULE NÀY -- xem `Agent/backend/web/identity.py`'s
module docstring cho phần đối xứng (đã đo được từ phía token: OKX không
chuyển bất kỳ định danh buyer nào xuống endpoint khi `fee = 0`). Đo thêm
được từ phía CLI `onchainos` thật: khi OKX thực sự gọi endpoint này, payload
`typedParams` nó gửi xuống CHỈ có `{"code": "..."}` -- KHÔNG có
`confirmationId`, KHÔNG có bất kỳ header định danh nào (header định danh chỉ
tồn tại ở nhánh trả phí x402, xem `access.py`). Vì vậy `/api/analyze` không
có cách nào biết ai đang gọi mình khi caller không đăng nhập qua
`POST /api/session` (luồng OKX chưa từng, và sẽ không bao giờ, đăng nhập).

Yêu cầu của chủ dự án: link chi tiết trả về cho một caller ẩn danh (chính là
OKX) không được mang định danh đoán-được là "mã bot" trần trụi
(`/bot/<code>`, ai cũng gõ được nếu biết code) -- phải có một phần định danh
là "mã lượt-dùng", tách biệt với `user_ref` thật của người dùng đã đăng nhập
(`Agent/backend/web/identity.py`) VÀ tách biệt với hồ sơ của họ
(`Agent/data/users/`). Vì không có gì từ OKX để suy ra mã này, hệ thống tự
ĐÚC một mã lượt-dùng MỚI cho MỖI lần `/api/analyze` phân tích thành công cho
một caller ẩn danh -- xem `mint_usage_ref` bên dưới.

THIẾT KẾ:
  * Hình dạng mã: ĐÚNG `identity.USER_REF_RE` (`^[a-z2-7]{10}$`, base32
    thường, 10 ký tự) -- KHÔNG được đổi hình dạng này, vì:
      - regex nginx `^/[a-z2-7]{10}_[A-Za-z0-9]{1,64}$`
        (`Agent/nginx/nginx-agent.conf.template`) và route Starlette
        `/{user_ref}_{code}` (app.py) đã tồn tại sẵn cho ĐÚNG hình dạng
        này -- dùng lại nguyên xi nghĩa là KHÔNG phải sửa nginx template
        (cần sudo, ta không có) hay thêm route mới.
      - `app.py`'s `user_report` route đã tách `<phần trước dấu _>` ra làm
        `user_ref` và validate bằng đúng `identity.USER_REF_RE` -- một mã
        lượt-dùng đúng hình dạng này đi thẳng qua route đó mà không cần
        đổi một dòng nào ở đó ngoài phần "thử usage_ref khi không phải
        user_ref thật" được thêm trong module này.
  * Sinh NGẪU NHIÊN bằng `secrets` (50 bit: 10 ký tự × 5 bit/ký tự base32),
    KHÔNG suy ra được từ `code` (khác hẳn `identity.user_ref`, vốn là HMAC
    xác định của địa chỉ ví -- ở đây không có "địa chỉ ví" nào để làm khoá,
    và bản thân yêu cầu là mỗi lượt phải là một mã riêng, không lặp lại).
  * Lưu bền dưới `Agent/data/usage_refs/<ref>.json` -- MỘT FILE RIÊNG cho
    MỖI mã, không phải một file chỉ-mục dùng chung. Lý do: hai lượt phân
    tích cho hai `code` khác nhau xảy ra đồng thời (nhiều request `/api/
    analyze` chạy song song, nhiều worker) sẽ ĐÚC hai file khác nhau, ghi
    atomic (`_write_json_atomic`, giống hệt khuôn `identity.py`'s
    `_write_json_atomic` -- tempfile cùng thư mục rồi `os.replace`) độc
    lập với nhau, không có cửa sổ nào để một lượt ghi đè mất lượt kia --
    khác hẳn một file chỉ-mục dùng chung, nơi hai request cùng đọc-sửa-ghi
    sẽ luôn có nguy cơ lượt ghi sau xoá mất lượt ghi trước (chính xác vấn
    đề `identity.py`'s `_write_json_atomic` docstring mô tả cho MỘT
    profile, ở đây sẽ tệ hơn vì mọi lượt phân tích ẩn danh đều chia sẻ
    CÙNG một file chỉ-mục).
  * TRẦN SỐ LƯỢNG (`MAX_USAGE_REFS`) VÀ DỌN THEO TUỔI
    (`USAGE_REF_TTL_SECONDS`) -- BẮT BUỘC vì đây là tác dụng phụ của một
    endpoint CÔNG KHAI, không có xác thực bắt buộc (xem access.py): mỗi
    lượt `/api/analyze` thành công của một caller ẩn danh đúc thêm một
    file, nên không có hai chốt chặn này thì `Agent/data/usage_refs/` phình
    vô hạn theo lưu lượng gọi thật của OKX Marketplace. `_prune` (chạy sau
    mỗi lần đúc mã) xoá trước những mã đã quá `USAGE_REF_TTL_SECONDS`
    tuổi, rồi nếu vẫn còn vượt `MAX_USAGE_REFS` thì xoá bớt những mã CŨ
    NHẤT (theo `created_at_ms`) cho tới khi về đúng trần -- cùng nguyên
    tắc "TTL trước, trần sau" `access.py`'s `RecentCodeRegistry` đã dùng.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Agent.backend.infra.config import config
from Agent.backend.web.identity import USER_REF_LENGTH, USER_REF_RE

# Kho riêng, KHÔNG trộn vào `Agent/data/users/<ref>/profile.json` của người
# dùng thật (identity.py) -- xem module docstring ở trên cho lý do tách
# biệt. Cùng khuôn injectable-default `users_root` của identity.py: mỗi
# hàm public bên dưới nhận `root=` riêng để test không bao giờ đụng vào kho
# thật của dự án.
DEFAULT_USAGE_REFS_ROOT = Path(config.DATA_DIR) / "report" / "single" / "usage_refs"

# Bảng chữ base32 thường -- CHÍNH XÁC alphabet `identity.USER_REF_RE` chấp
# nhận (`[a-z2-7]`), không phải để encode gì cả, chỉ để rút ngẫu nhiên từng
# ký tự một bằng `secrets.choice` (xem `_generate_ref`).
_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"

# 20,000 file × dăm chục byte JSON mỗi file là vài MB trên đĩa -- rẻ, và xa
# lưu lượng thực tế dự án này quan sát được (endpoint này bị giới hạn 5
# request/phút/IP ở tầng rate-limit, xem app.py's ANALYZE_RATE_LIMIT_MAX_
# REQUESTS) trong khi vẫn đủ rộng để không bao giờ cắt cụt lịch sử trong
# một ngày vận hành bình thường.
MAX_USAGE_REFS = 20_000

# 30 ngày: một mã lượt-dùng phải sống đủ lâu để người mua trên OKX (hay
# agent thay họ) còn quay lại mở link chi tiết vài ngày sau khi mua, nhưng
# vẫn phải hết hạn -- đây là link CÔNG KHAI không xác thực, sống mãi mãi là
# một rò rỉ không có lý do chính đáng.
USAGE_REF_TTL_SECONDS = 30 * 24 * 3600

# Số lần thử lại khi mã ngẫu nhiên vừa sinh ra đã trùng một file đang có
# sẵn -- với 50 bit ngẫu nhiên, việc trùng ở lần thử ĐẦU TIÊN đã cực hiếm
# (cỡ 1/2^50 cho một cặp cụ thể); 5 lần thử chỉ để không bao giờ có một
# request công khai bị lỗi 500 vì một sự trùng hợp thống kê gần như không
# thể xảy ra trong thực tế.
_MAX_MINT_ATTEMPTS = 5


def _now_ms() -> int:
    return int(time.time() * 1000)


def _entry_path(root: Path, ref: str) -> Path:
    return Path(root) / f"{ref}.json"


def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    """Ghi `data` xuống `path` dạng JSON, atomic -- cùng khuôn
    `identity.py`'s `_write_json_atomic` (tempfile CÙNG thư mục rồi
    `os.replace`, dọn tempfile trong `finally` nếu có lỗi giữa chừng) --
    xem module đó để biết đầy đủ lý do (yêu cầu `os.replace` atomic là
    cùng filesystem, và một lượt ghi lỗi giữa chừng không bao giờ được để
    lại một file `.json` dở dang). Không import thẳng hàm private của
    `identity.py` (tên có gạch dưới đầu, không phải API công khai của
    module đó) -- lặp lại ~15 dòng này rẻ hơn nhiều so với việc hai module
    độc lập chia sẻ một hàm private xuyên module.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=".usage_ref-", suffix=".json.tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _generate_ref() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(USER_REF_LENGTH))


def _prune(root: Path, *, now_ms: Optional[int] = None) -> None:
    """Dọn `root`: xoá trước mọi entry đã quá `USAGE_REF_TTL_SECONDS` tuổi,
    rồi nếu số còn lại vẫn vượt `MAX_USAGE_REFS` thì xoá bớt những entry CŨ
    NHẤT cho tới khi về đúng trần.

    Best-effort trên từng file: một file đọc lỗi (JSON hỏng, tiến trình
    khác vừa xoá nó) chỉ bị BỎ QUA (không tính là "còn sống", không được
    tính vào trần) thay vì làm hỏng cả lượt dọn -- nhiều worker có thể cùng
    chạy hàm này đồng thời (xem `mint_usage_ref`, gọi sau mỗi lần đúc mã
    mới), nên một `unlink()` "lỡ tay" trên file người khác vừa xoá rồi là
    tình huống BÌNH THƯỜNG, không phải lỗi.
    """
    try:
        paths = list(Path(root).glob("*.json"))
    except OSError:
        return
    now = now_ms if now_ms is not None else _now_ms()
    alive: List[Tuple[int, Path]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        created = payload.get("created_at_ms") if isinstance(payload, dict) else None
        if not isinstance(created, (int, float)):
            created = 0
        if now - created > USAGE_REF_TTL_SECONDS * 1000:
            try:
                path.unlink()
            except OSError:
                pass
            continue
        alive.append((int(created), path))
    if len(alive) > MAX_USAGE_REFS:
        alive.sort(key=lambda item: item[0])  # cũ nhất đứng trước
        overflow = len(alive) - MAX_USAGE_REFS
        for _, path in alive[:overflow]:
            try:
                path.unlink()
            except OSError:
                pass


def mint_usage_ref(
    code: str, *, root: Path = DEFAULT_USAGE_REFS_ROOT, now_ms: Optional[int] = None
) -> str:
    """Đúc một mã lượt-dùng MỚI ràng buộc vào đúng `code` này, lưu bền, dọn
    kho theo trần/tuổi (xem `_prune`), rồi trả về mã đó.

    LUÔN đúc mã MỚI, không bao giờ tái dùng mã cũ cho cùng một `code` --
    đúng yêu cầu "mỗi lượt dùng một mã riêng": hai lần `/api/analyze` cho
    cùng một `code` (kể cả khi cả hai đều trả lời từ cache) mỗi lần đều
    nhận một `report_url` khác nhau.

    `code` được tin là đã qua `validate_unique_code` bởi caller (app.py's
    `api_analyze`) -- module này không tự validate lại, vì nó không bao
    giờ dùng `code` để dựng đường dẫn file (khoá file là `ref`, do chính
    module này sinh ra), nên không có rủi ro path-traversal từ `code` ở
    đây.
    """
    root = Path(root)
    now = now_ms if now_ms is not None else _now_ms()
    ref = _generate_ref()
    path = _entry_path(root, ref)
    for _ in range(_MAX_MINT_ATTEMPTS):
        if not path.exists():
            break
        ref = _generate_ref()
        path = _entry_path(root, ref)
    _write_json_atomic(path, {"code": code, "created_at_ms": now})
    _prune(root, now_ms=now)
    return ref


def resolve_usage_ref(
    ref: str,
    code: str,
    *,
    root: Path = DEFAULT_USAGE_REFS_ROOT,
    now_ms: Optional[int] = None,
) -> bool:
    """True khi và chỉ khi `ref` là một mã lượt-dùng CÒN HIỆU LỰC (chưa quá
    `USAGE_REF_TTL_SECONDS` tuổi) VÀ nó được đúc cho ĐÚNG `code` này -- mã
    lượt-dùng cấp cho bot A không bao giờ mở được bot B, dù đúng định dạng.

    False cho MỌI trường hợp khác (sai định dạng, không tồn tại, hết hạn,
    cấp cho code khác) mà KHÔNG phân biệt lý do nào trong số đó với nhau --
    cùng nguyên tắc 404 chung `app.py`'s `_generic_report_404` đã áp dụng
    cho `user_ref` thật, vì cùng lý do: một thông báo lỗi khác biệt theo lý
    do sẽ tự nó là một tín hiệu cho kẻ dò quét biết họ đang "gần đúng".
    """
    if not USER_REF_RE.match(ref):
        return False
    path = _entry_path(Path(root), ref)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(payload, dict) or payload.get("code") != code:
        return False
    created = payload.get("created_at_ms")
    if not isinstance(created, (int, float)):
        return False
    now = now_ms if now_ms is not None else _now_ms()
    return (now - created) <= USAGE_REF_TTL_SECONDS * 1000
