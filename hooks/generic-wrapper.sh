#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${CODING_MEMORY_DISABLED:-0}" != 1 ]]; then
  "$ROOT/scripts/memory-context" --query "${1:-current coding task}" || true
fi
# Invoke your coding agent here, or source this wrapper from its launcher.
