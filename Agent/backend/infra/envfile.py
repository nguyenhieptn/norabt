"""Trình nạp file .env tối giản, chỉ dùng thư viện chuẩn.

Không dùng python-dotenv (hay bất kỳ dependency ngoài nào) dù thư viện này có
sẵn trên máy dev -- dự án chủ trương không kéo thêm dependency cho một việc
chỉ vài chục dòng code.
"""

from __future__ import annotations

import os
import stat
import sys

__all__ = ["load_env_file", "apply_env_file"]


def _strip_quotes(value: str) -> str:
    """Bỏ cặp nháy bao ngoài (\" hoặc ') nếu có, giữ nguyên nội dung bên trong."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _warn_if_permissive(path: str) -> None:
    """Cảnh báo (không chặn) nếu group/other đọc được file .env.

    Chỉ cảnh báo vì người dùng có thể có lý do riêng (vd. container dùng
    chung UID khác); từ chối nạp giữa chừng còn tệ hơn một file lộ quyền.
    """
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return
    if mode & 0o077:
        print(
            f"CẢNH BÁO: {path} cho phép group/other đọc (mode "
            f"{oct(mode)}) -- file này chứa secret, nên chạy "
            f"`chmod 600 {path}`.",
            file=sys.stderr,
        )


def load_env_file(path: str) -> dict:
    """Parse một file .env đơn giản thành dict, không đụng os.environ.

    - Dòng trống hoặc bắt đầu bằng '#' bị bỏ qua.
    - Tách theo dấu '=' đầu tiên để giá trị (vd. chuỗi base64 kết thúc bằng
      '==') không bị cắt sai.
    - Dòng không có '=' là dòng sai định dạng -- bỏ qua thay vì raise, vì
      một dòng hỏng trong .env không nên làm sập cả ứng dụng khi khởi động.
    - File không tồn tại -> trả dict rỗng, không lỗi (đây là trường hợp bình
      thường trên môi trường chỉ dùng biến môi trường thật, vd. systemd/CI).
    """
    result: dict = {}
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return result

    _warn_if_permissive(path)

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            # Dòng sai định dạng: bỏ qua, không raise -- xem docstring ở trên.
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        result[key] = _strip_quotes(value.strip())
    return result


def apply_env_file(path: str) -> int:
    """Nạp file .env vào os.environ, trả về số biến thực sự được set.

    Biến môi trường thật LUÔN thắng file: chỉ set khi key đó chưa có trong
    os.environ. Đây là quy tắc bắt buộc -- systemd/CI/docker inject biến vào
    tiến trình phải đè được file .env nằm trên đĩa, không phải ngược lại.

    Không log giá trị nào ở đây hay trong load_env_file -- đây là secret.
    """
    values = load_env_file(path)
    applied = 0
    for key, value in values.items():
        if key in os.environ:
            continue
        os.environ[key] = value
        applied += 1
    return applied
