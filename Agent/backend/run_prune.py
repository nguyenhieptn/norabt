"""Backward compatibility shim for Agent.backend.run_prune."""

from Agent.backend.scripts.run_prune import *  # noqa: F403
from Agent.backend.scripts.run_prune import main  # noqa: F401

if __name__ == "__main__":
    main()
