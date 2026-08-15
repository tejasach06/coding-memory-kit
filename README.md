# Coding Memory Kit

Portable skill and MCP configuration for shared, filtered coding-agent memory.

## Security model

The deployment uses API-key authentication for both MCP and Qdrant. The key is never included in this archive. Export it as `CODING_MEMORY_MCP_API_KEY` for agents and `CODING_MEMORY_QDRANT_API_KEY` only for the optional `forget` REST operation.

This package uses Streamable HTTP. The legacy SSE service is available for native MCP clients that require it, but the included helper scripts intentionally fail unless the Streamable HTTP endpoint is configured.

## Quick start

```bash
export CODING_MEMORY_MCP_URL=http://192.168.0.9:8000/mcp/
export CODING_MEMORY_MCP_API_KEY='retrieve-from-your-secret-manager'
./scripts/verify-mcp
./scripts/memory-context --query "authentication deployment decision"
```

Do not put the key in Git, shell history, or this archive.

## Commands

```bash
# Store project knowledge
printf '%s
' 'Chose PostgreSQL because transaction isolation is required.' |   ./scripts/memory-store --scope project --verified --source 'tests/db_test.py'

# Store an explicitly user-confirmed global preference
printf '%s
' 'Prefer concise technical responses.' |   ./scripts/memory-store --scope global-preference --source user --confirm-global

# Remove a record by fingerprint
./scripts/memory_lib.py forget --fingerprint SHA256
```

## Enforcement

Retrieval sends Qdrant payload filters; project records cannot be returned to another project, and global records use the neutral namespace `__global__`. The remote server must have `QDRANT_ALLOW_ARBITRARY_FILTER=true`.

## Native integrations

- MCP templates are in `config/` and include the API-key header.
- `config/claude-code.hooks.json` and `hooks/claude-memory-hook.py` implement automatic retrieval for Claude Code.
- Other clients require their documented hook mechanism or explicit helper invocation; the package does not claim unsupported universal hooks.

## Operational files

- `server/mcp_auth_launcher.py`: FastMCP API-key middleware launcher used by the Podman deployment.
- `docs/agent-integration.md`: client configuration and hook behavior.
- `docs/memory-policy.md`: scope, consent, and retention policy.
- `docs/troubleshooting.md`: authentication, filter, and transport checks.
