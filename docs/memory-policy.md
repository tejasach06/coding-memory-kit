# Memory Policy

## Scopes

- Project records use the exact Git-derived project namespace.
- Global preferences and global facts use `__global__` and are filtered separately.
- Global preferences require `--confirm-global` plus an explicit user source. This is an accidental-write consent gate, not cryptographic identity proof.
- Global facts require `--verified` and an evidence source.

## Data handling

Writes are redacted, bounded to 16 KiB by default, fingerprinted, and locally deduplicated under an advisory file lock. Do not store secrets, full source files, logs, or credentials.

## Retraction

Use `memory_lib.py forget --fingerprint` with `CODING_MEMORY_QDRANT_API_KEY` to delete a record from Qdrant. Retraction does not automatically remove copies in external backups.
