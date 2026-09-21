"""Backward compatibility shim for Agent.backend.run_compare."""

from Agent.backend.scripts.run_compare import *  # noqa: F403
from Agent.backend.scripts.run_compare import main  # noqa: F401

if __name__ == "__main__":
    main()
