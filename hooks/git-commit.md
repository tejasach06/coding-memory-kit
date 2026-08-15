# Commit/milestone hook

Summarize durable project decisions from commit/PR context, then run:
```bash
printf '%s
' "$DECISION" | scripts/memory-store --scope project --verified --source "git:$COMMIT"
```
