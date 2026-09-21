"""Backward compatibility shim for Agent.backend.run_web -> Agent.backend.scripts.run_web.

The running Docker container norabt-agent-web invokes:
    python3 -m Agent.backend.run_web ...
This shim ensures it continues to work seamlessly.
"""

from Agent.backend.scripts.run_web import *  # noqa: F403
from Agent.backend.scripts.run_web import main  # noqa: F401

if __name__ == "__main__":
    main()
