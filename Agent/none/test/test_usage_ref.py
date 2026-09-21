"""Tests for `Agent/backend/web/usage_ref.py` -- Việc 2's per-lượt usage-ref
store for anonymous `/api/analyze` callers (the OKX Marketplace's own shape:
no `confirmationId`, no identifying header at all is ever forwarded to this
endpoint, see that module's own docstring). Exercises the module directly
(no HTTP layer here -- `Agent/none/test/test_web_app.py` covers the
`/{ref}_{code}` route wiring and the `report_url` shape `/api/analyze`
hands out).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from Agent.backend.web import usage_ref
from Agent.backend.web.identity import USER_REF_RE


def test_mint_usage_ref_matches_user_ref_shape(tmp_path: Path) -> None:
    """Đúng `^[a-z2-7]{10}$` (`identity.USER_REF_RE`) -- BẮT BUỘC để regex
    nginx `^/[a-z2-7]{10}_[A-Za-z0-9]{1,64}$` và route Starlette
    `/{user_ref}_{code}` hiện có nhận diện được mà không cần sửa gì."""
    ref = usage_ref.mint_usage_ref("ABC123", root=tmp_path)
    assert USER_REF_RE.match(ref), ref


def test_mint_usage_ref_returns_a_new_code_every_call(tmp_path: Path) -> None:
    """ "Mỗi lượt dùng một mã riêng" -- hai lượt đúc cho ĐÚNG cùng một code
    vẫn phải ra hai mã khác nhau, không tái dùng/khoá theo code."""
    first = usage_ref.mint_usage_ref("ABC123", root=tmp_path)
    second = usage_ref.mint_usage_ref("ABC123", root=tmp_path)
    assert first != second


def test_mint_usage_ref_persists_to_disk_across_process_restarts(
    tmp_path: Path,
) -> None:
    """ "Lưu bền để link còn giải được sau khi container khởi động lại" --
    mô phỏng bằng cách KHÔNG giữ lại state Python nào, chỉ đọc lại từ đúng
    `root` bằng một lời gọi `resolve_usage_ref` hoàn toàn độc lập."""
    ref = usage_ref.mint_usage_ref("ABC123", root=tmp_path)
    assert usage_ref.resolve_usage_ref(ref, "ABC123", root=tmp_path) is True


def test_resolve_usage_ref_true_for_the_code_it_was_minted_for(
    tmp_path: Path,
) -> None:
    ref = usage_ref.mint_usage_ref("ABC123", root=tmp_path)
    assert usage_ref.resolve_usage_ref(ref, "ABC123", root=tmp_path) is True


def test_resolve_usage_ref_false_for_a_different_code(tmp_path: Path) -> None:
    """Mã lượt-dùng cấp cho bot A không bao giờ mở được bot B -- yêu cầu bắt
    buộc của Việc 2."""
    ref = usage_ref.mint_usage_ref("BOT_A_CODE", root=tmp_path)
    assert usage_ref.resolve_usage_ref(ref, "BOT_B_CODE", root=tmp_path) is False


def test_resolve_usage_ref_false_for_unknown_ref(tmp_path: Path) -> None:
    assert usage_ref.resolve_usage_ref("zzzzzzzzzz", "ABC123", root=tmp_path) is False


@pytest.mark.parametrize(
    "bad_ref",
    [
        "",
        "short",
        "TOOLONGREF10",
        "has_under1",  # underscore not in [a-z2-7]
        "has018899",  # digits 0/1/8/9 not in base32 alphabet
        "UPPERCASE1",
    ],
)
def test_resolve_usage_ref_false_for_malformed_ref(
    bad_ref: str, tmp_path: Path
) -> None:
    assert usage_ref.resolve_usage_ref(bad_ref, "ABC123", root=tmp_path) is False


def test_resolve_usage_ref_false_once_ttl_expires(tmp_path: Path) -> None:
    minted_at = 1_000_000_000_000
    ref = usage_ref.mint_usage_ref("ABC123", root=tmp_path, now_ms=minted_at)
    just_before_expiry = minted_at + usage_ref.USAGE_REF_TTL_SECONDS * 1000
    just_after_expiry = just_before_expiry + 1
    assert (
        usage_ref.resolve_usage_ref(
            ref, "ABC123", root=tmp_path, now_ms=just_before_expiry
        )
        is True
    )
    assert (
        usage_ref.resolve_usage_ref(
            ref, "ABC123", root=tmp_path, now_ms=just_after_expiry
        )
        is False
    )


def test_prune_removes_expired_entries_by_age(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dọn theo tuổi: một entry quá hạn `USAGE_REF_TTL_SECONDS` bị xoá khỏi
    đĩa hẳn (không chỉ "không giải được" -- xoá vật lý), một entry còn hạn
    thì được giữ nguyên. Kích hoạt việc dọn qua chính `mint_usage_ref`
    (đường thật duy nhất gọi `_prune` trong sản phẩm), không gọi thẳng hàm
    private."""
    monkeypatch.setattr(usage_ref, "USAGE_REF_TTL_SECONDS", 100)
    old_ref = usage_ref.mint_usage_ref("OLD_CODE", root=tmp_path, now_ms=0)
    fresh_ref = usage_ref.mint_usage_ref("FRESH_CODE", root=tmp_path, now_ms=50_000)
    # Đúc thêm một mã mới tại thời điểm đã đủ làm OLD_CODE (tuổi 120_000ms)
    # quá hạn 100_000ms nhưng CHƯA đủ làm FRESH_CODE (tuổi chỉ 70_000ms) quá
    # hạn -- lượt đúc này tự kích hoạt `_prune`.
    usage_ref.mint_usage_ref("TRIGGER_CODE", root=tmp_path, now_ms=120_000)

    assert not (tmp_path / f"{old_ref}.json").exists()
    assert (tmp_path / f"{fresh_ref}.json").exists()


def test_prune_enforces_the_max_count_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Trần số lượng: một khi vượt `MAX_USAGE_REFS`, những entry CŨ NHẤT bị
    xoá cho tới khi về đúng trần -- endpoint công khai không xác thực không
    được phép phình vô hạn theo lưu lượng gọi."""
    monkeypatch.setattr(usage_ref, "MAX_USAGE_REFS", 3)
    # TTL đủ lớn để không entry nào bị dọn vì tuổi trong test này -- chỉ
    # trần số lượng mới được phép loại chúng.
    monkeypatch.setattr(usage_ref, "USAGE_REF_TTL_SECONDS", 10_000)
    refs = [
        usage_ref.mint_usage_ref(f"CODE_{i}", root=tmp_path, now_ms=i * 1000)
        for i in range(5)
    ]
    remaining = {p.stem for p in tmp_path.glob("*.json")}
    assert len(remaining) == 3
    # Ba mã ĐÚC SAU CÙNG (mới nhất) phải còn, hai mã đúc đầu tiên (cũ nhất)
    # phải đã bị dọn.
    assert remaining == set(refs[-3:])
    for old_ref in refs[:2]:
        assert old_ref not in remaining


def test_mint_usage_ref_writes_atomic_json_with_expected_shape(
    tmp_path: Path,
) -> None:
    """Không kiểm tra hành vi nội bộ của `_write_json_atomic` (đã có khuôn
    y hệt `identity.py`, không phải logic mới) -- chỉ khoá đúng NỘI DUNG file
    kết quả, vì đó là thứ `resolve_usage_ref` phụ thuộc vào."""
    ref = usage_ref.mint_usage_ref("ABC123", root=tmp_path, now_ms=42)
    payload = json.loads((tmp_path / f"{ref}.json").read_text(encoding="utf-8"))
    assert payload == {"code": "ABC123", "created_at_ms": 42}
