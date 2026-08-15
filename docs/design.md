# Coding Memory Kit Design (v1.1)

## Goal

Retain important project decisions across coding agents while preserving explicit global preferences across projects, with API-key authentication and hard metadata-filtered retrieval.

## Boundaries

The archive is manual-install. It does not modify agent configuration automatically or perform package updates. The remote Podman deployment is separately managed with Quadlet and an API-key secret file.

## Data model

Each write carries `scope`, `project`, `agent`, `source`, `verified`, `timestamp`, and `fingerprint` metadata.

- Project IDs derive from normalized Git roots.
- Global preferences and facts use `project=__global__`.
- Global preferences require explicit user confirmation.
- Global facts require evidence and verified status.
- No auto-learning or autonomous behavior inference.

## Isolation and deduplication

Every retrieval sends a Qdrant payload filter through `qdrant-find`. Project queries require both project scope and exact project ID. Global queries require the matching global scope and `__global__`. Writes perform both local and shared fingerprint checks before `qdrant-store`.

## Security

Qdrant REST and MCP are protected with separate API-key uses from a server-side `0600` secrets file. The included MCP launcher gates Streamable HTTP and SSE with `X-API-Key` or `Authorization: Bearer`. Client packages contain no secret.

## Flow

Retrieve global preferences and facts before project context. Retrieve task-specific context before work. Store concise decisions/fixes after completed work and at milestones. Stop hooks remind agents to store verified facts but do not store arbitrary transcripts.

## Failure behavior

Normal hooks fail open so coding is not blocked. `verify-mcp` is strict and returns nonzero for authentication, transport, initialization, or filtered-tool failures. `CODING_MEMORY_DISABLED=1` disables operations. Writes are redacted, bounded, and file-locked.

## Retraction

`memory_lib.py forget --fingerprint` deletes a record through authenticated Qdrant REST. External backups require separate cleanup.
