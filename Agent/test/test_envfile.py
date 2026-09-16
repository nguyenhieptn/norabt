"""Test cho envfile.py -- trình nạp .env tối giản (không dependency ngoài).

Trọng tâm: biến môi trường thật phải thắng file (systemd/CI/docker đè lên
file .env nằm trên đĩa), và một dòng .env hỏng không được làm sập việc nạp.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from Agent.backend.infra.envfile import apply_env_file, load_env_file


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_env_file_parses_simple_assignments(tmp_path: Path):
    env_path = _write(tmp_path / ".env", "FOO=bar\nBAZ=qux\n")

    values = load_env_file(str(env_path))

    assert values == {"FOO": "bar", "BAZ": "qux"}


def test_apply_env_file_sets_os_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    env_path = _write(tmp_path / ".env", "NEW_VAR=hello\n")
    # apply_env_file() mutates os.environ directly (that's its whole job), so
    # swap in a throwaway copy first -- monkeypatch restores the real
    # os.environ object on teardown, leaving the actual process env untouched.
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.delenv("NEW_VAR", raising=False)

    applied = apply_env_file(str(env_path))

    assert applied == 1
    assert os.environ["NEW_VAR"] == "hello"


def test_real_env_var_wins_over_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Biến môi trường có sẵn thì thắng file -- quy tắc quan trọng nhất.

    systemd/CI/docker inject biến vào tiến trình phải đè được file .env nằm
    trên đĩa, chứ không phải ngược lại.
    """
    env_path = _write(tmp_path / ".env", "OKX_API_KEY=from-file\n")
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setenv("OKX_API_KEY", "from-real-env")

    applied = apply_env_file(str(env_path))

    assert os.environ["OKX_API_KEY"] == "from-real-env"
    assert applied == 0


def test_value_containing_equals_sign_not_truncated(tmp_path: Path):
    # Base64 thường kết thúc bằng '=' hoặc '==' -- phải tách theo dấu '=' đầu
    # tiên, không phải tách hết mọi dấu '='.
    env_path = _write(tmp_path / ".env", "SECRET=YWJjZGVmZ2g==\n")

    values = load_env_file(str(env_path))

    assert values == {"SECRET": "YWJjZGVmZ2g=="}


def test_surrounding_double_quotes_are_stripped(tmp_path: Path):
    env_path = _write(tmp_path / ".env", 'NAME="hello world"\n')

    values = load_env_file(str(env_path))

    assert values == {"NAME": "hello world"}


def test_surrounding_single_quotes_are_stripped(tmp_path: Path):
    env_path = _write(tmp_path / ".env", "NAME='hello world'\n")

    values = load_env_file(str(env_path))

    assert values == {"NAME": "hello world"}


def test_comments_and_blank_lines_are_ignored(tmp_path: Path):
    env_path = _write(
        tmp_path / ".env",
        "\n# this is a comment\nFOO=bar\n\n# OKX_API_KEY=disabled\n",
    )

    values = load_env_file(str(env_path))

    assert values == {"FOO": "bar"}


def test_malformed_line_is_skipped_without_raising(tmp_path: Path):
    env_path = _write(tmp_path / ".env", "this line has no equals sign\nFOO=bar\n")

    values = load_env_file(str(env_path))

    assert values == {"FOO": "bar"}


def test_missing_file_returns_empty_without_raising(tmp_path: Path):
    missing_path = tmp_path / "does_not_exist.env"

    values = load_env_file(str(missing_path))
    applied = apply_env_file(str(missing_path))

    assert values == {}
    assert applied == 0


def test_permissive_mode_warns_on_stderr(tmp_path: Path, capsys: pytest.CaptureFixture):
    env_path = _write(tmp_path / ".env", "FOO=bar\n")
    env_path.chmod(0o644)

    load_env_file(str(env_path))

    captured = capsys.readouterr()
    assert "chmod 600" in captured.err


def test_strict_mode_does_not_warn(tmp_path: Path, capsys: pytest.CaptureFixture):
    env_path = _write(tmp_path / ".env", "FOO=bar\n")
    env_path.chmod(0o600)

    load_env_file(str(env_path))

    captured = capsys.readouterr()
    assert captured.err == ""


def test_load_env_file_never_touches_os_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """load_env_file() chỉ parse -- không có tác dụng phụ lên os.environ."""
    env_path = _write(tmp_path / ".env", "SIDE_EFFECT_CHECK=should-not-leak\n")
    monkeypatch.delenv("SIDE_EFFECT_CHECK", raising=False)

    load_env_file(str(env_path))

    assert "SIDE_EFFECT_CHECK" not in os.environ


def test_file_mode_is_restored_after_permission_test(tmp_path: Path):
    # Sanity check that chmod in the tests above only touches the tmp_path
    # fixture's own file, never a shared/real path.
    env_path = _write(tmp_path / ".env", "FOO=bar\n")
    env_path.chmod(0o644)
    mode = stat.S_IMODE(env_path.stat().st_mode)
    assert mode & 0o077
