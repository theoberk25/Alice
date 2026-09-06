"""Decision-Brief MCP server package.

Standalone MCP server (Streamable HTTP) that reads ALICE's held decisions and
publishes plain-language, technician-facing briefs into the review dashboard.
It is a presentation/explanation layer only — it never recomputes or overrides
the authoritative decision, and it never decides a HOLD. See
docs/agent-build/04-brief-mcp.md.
"""
