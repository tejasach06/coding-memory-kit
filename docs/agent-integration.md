# Agent Integration

## Environment

Export `CODING_MEMORY_MCP_API_KEY` from a secret manager or protected shell environment. Do not place it in repository files. Use the matching config template in `config/` and restart the agent.

## Hook behavior

- Claude Code: merge `config/claude-code.hooks.json`; session start and prompt submission retrieve filtered context. Stop emits a reminder and never stores arbitrary transcript data.
- Hermes/Codex/OpenCode/Cursor/VS Code: configure MCP using the matching template, then use the client’s native lifecycle mechanism to run `scripts/memory-context`. Templates are MCP-only unless a client-specific hook file is provided.
- Generic clients: run `scripts/memory-context --query '<task>'` before work and `scripts/memory-store` after verified work.

All hooks are fail-open for normal coding work, but `scripts/verify-mcp` is fail-closed and strict.
