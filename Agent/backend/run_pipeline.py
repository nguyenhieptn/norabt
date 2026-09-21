"""Backward compatibility shim for Agent.backend.run_pipeline."""

from Agent.backend.scripts.run_pipeline import *  # noqa: F403
from Agent.backend.scripts.run_pipeline import main  # noqa: F401

if __name__ == "__main__":
    main()
