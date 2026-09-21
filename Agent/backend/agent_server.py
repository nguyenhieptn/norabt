"""Backward compatibility shim for Agent.backend.agent_server."""

from Agent.backend.scripts.agent_server import *  # noqa: F403
from Agent.backend.scripts.agent_server import main  # noqa: F401

if __name__ == "__main__":
    main()
