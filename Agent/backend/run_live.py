"""Backward compatibility shim for Agent.backend.run_live."""

from Agent.backend.scripts.run_live import *  # noqa: F403
from Agent.backend.scripts.run_live import main  # noqa: F401

if __name__ == "__main__":
    main()
