# Troubleshooting

```bash
# Strict authenticated MCP check
./scripts/verify-mcp

# Check service state remotely
ssh tejas@192.168.0.9 'systemctl --user status qdrant-mcp mcp-qdrant-streamable'

# Verify Qdrant requires its API key
curl -i http://192.168.0.9:6333/collections

# Confirm filters are enabled in the MCP container
ssh tejas@192.168.0.9 'podman logs --tail 100 mcp-qdrant-streamable'
```

Common failures:

- `401 Unauthorized`: export the MCP API key in the agent process.
- `MCP tool returned isError`: the server may not have `QDRANT_ALLOW_ARBITRARY_FILTER=true`.
- `Connection refused`: inspect the user Quadlet units and listen addresses.
- First request timeout: the local embedding model may still be downloading.
