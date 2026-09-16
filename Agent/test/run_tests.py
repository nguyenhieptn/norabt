from __future__ import annotations

from pathlib import Path

import pytest


WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    return pytest.main(
        ["-p", "no:asyncio", str(WORKSPACE_DIR / "Agent" / "test"), "-q"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
