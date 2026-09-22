"""HTTP surface for the OKX copy-trading risk-supervisor dashboard.

Separate from `Agent/backend/scripts/agent_server.py` (the MCP tool surface for AI
agents): this package serves a human-facing dashboard over plain HTTP/JSON
via Starlette + uvicorn -- both already pulled in as dependencies of the
`mcp` package this project uses elsewhere, so nothing new is added here.
"""
