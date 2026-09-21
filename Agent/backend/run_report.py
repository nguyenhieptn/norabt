"""Backward compatibility shim for Agent.backend.run_report."""

from Agent.backend.scripts.run_report import *  # noqa: F403
from Agent.backend.scripts.run_report import main  # noqa: F401

if __name__ == "__main__":
    main()
