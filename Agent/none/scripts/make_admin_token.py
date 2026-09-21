"""Hash an admin secret into the `NORABT_ADMIN_TOKEN_SHA256` .env line.

Why this exists: `Agent/backend/web/access.py`'s admin gate never stores the
admin key itself, only its SHA-256 hex digest (see that module's own "Admin
role" section) -- a `.env` file gets copy-pasted between machines, pasted
into a chat, or caught in a screenshot far more often than anyone intends,
and a hash in that file is useless to a reader, whereas a raw key would be
immediately usable against the live endpoint. This script does that one-way
hash for the operator so nobody has to open a Python REPL for it.

Usage:
    python3 Agent/none/scripts/make_admin_token.py "my-secret-string"
    echo "my-secret-string" | python3 Agent/none/scripts/make_admin_token.py
    python3 Agent/none/scripts/make_admin_token.py   # prompts interactively

See `Agent/.env.example`'s own comment on `NORABT_ADMIN_TOKEN_SHA256` for
the operator-facing trade-off around WHICH secret to hash here (a
freshly-generated random string vs. reusing the team's OKX API key).
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import sys
from typing import Optional


def _read_secret(positional: Optional[str]) -> str:
    """The secret to hash, from (in priority order) the CLI argument, a
    piped stdin line, or an interactive prompt.

    `getpass.getpass` (not `input`) for the interactive case specifically:
    it never echoes the typed characters to the terminal, so the secret
    cannot end up sitting in a terminal scrollback buffer -- the same class
    of accidental-leak this whole script exists to reduce (see the module
    docstring's ".env gets copy-pasted / screenshotted" reasoning).
    """
    if positional:
        return positional
    if not sys.stdin.isatty():
        # Piped input, e.g. `echo "..." | python3 make_admin_token.py` --
        # read exactly one line and strip the trailing newline `echo`/
        # `printf` add, so that newline never becomes part of the hashed
        # secret (it would otherwise silently produce a DIFFERENT hash than
        # hashing the same text typed interactively or passed as an arg).
        return sys.stdin.readline().rstrip("\n")
    return getpass.getpass(
        "Nhập chuỗi bí mật dùng làm khoá admin (sẽ không hiện ra màn hình): "
    )


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "In ra dòng NORABT_ADMIN_TOKEN_SHA256=<hex> để dán vào .env, "
            "từ một chuỗi bí mật truyền qua tham số dòng lệnh, stdin, hoặc "
            "nhập trực tiếp."
        )
    )
    parser.add_argument(
        "secret",
        nargs="?",
        default=None,
        help=(
            "Chuỗi bí mật cần băm. Nếu bỏ trống, script đọc từ stdin (nếu "
            "có input được pipe vào) hoặc hỏi trực tiếp."
        ),
    )
    args = parser.parse_args(argv)

    secret = _read_secret(args.secret)
    if not secret:
        print("Lỗi: chuỗi bí mật rỗng -- không tạo hash.", file=sys.stderr)
        return 1

    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    # The hash line goes to stdout alone (so it can be redirected/piped
    # cleanly into a .env file); every warning/explanation goes to stderr.
    print(f"NORABT_ADMIN_TOKEN_SHA256={digest}")
    print(
        "\nCẢNH BÁO: dòng trên chỉ chứa BẢN BĂM một chiều -- chuỗi bí mật "
        "GỐC bạn vừa nhập mới là thứ thực sự dùng để gọi endpoint (gửi qua "
        "header X-Access-Token hoặc tham số 'token'). Giữ kín chuỗi gốc đó: "
        "đừng dán vào chat, đừng commit, đừng lưu chung file .env với người "
        "không cần biết nó.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
