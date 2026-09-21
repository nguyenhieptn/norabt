"""Backward compatibility shim for Agent.backend.run_probe."""

from Agent.backend.scripts.run_probe import *  # noqa: F403
from Agent.backend.scripts.run_probe import main  # noqa: F401

if __name__ == "__main__":
    main()
