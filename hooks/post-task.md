# Post-task hook

After verified work, store concise decisions/fixes:
```bash
printf '%s
' "$MEMORY_TEXT" | scripts/memory-store --scope project --verified --source "$EVIDENCE"
```
Do not store failed experiments unless they are durable warnings.
