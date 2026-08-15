# Authenticated Podman MCP deployment

This directory contains the launcher used on `192.168.0.9`.

## Server prerequisites

- Rootless Podman
- Qdrant and `mcp-server-qdrant:numpy2` images
- FastMCP with `http_app()` and uvicorn in the MCP image
- `/opt/qdrant-mcp/secrets/coding-memory.env` mode `0600`

Required secret variables:

```text
QDRANT_API_KEY=<internal Qdrant key>
MCP_API_KEY=<client-facing MCP key>
QDRANT__SERVICE__API_KEY=<same internal Qdrant key>
QDRANT__SERVICE__HOST=192.168.0.9
```

The MCP Quadlets also set `QDRANT_ALLOW_ARBITRARY_FILTER=true`, which is required for hard scope filters.

## Deployment

Copy `mcp_auth_launcher.py` to `/opt/qdrant-mcp/server/`, mount it read-only into the MCP containers, use the Quadlet templates from the remote deployment, then run:

```bash
systemctl --user daemon-reload
systemctl --user restart qdrant-mcp.service
systemctl --user restart mcp-qdrant-streamable.service
systemctl --user restart mcp-qdrant-sse.service
```

Do not print or commit the secret file. Keep Qdrant REST bound to `192.168.0.9` and use the MCP endpoint for agents.
