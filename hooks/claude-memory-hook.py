#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
kind=sys.argv[1] if len(sys.argv)>1 else "prompt"
try: event=json.load(sys.stdin)
except Exception: event={}
query=(event.get("prompt") or event.get("message") or "coding task").strip()
if kind == "stop":
    print("Memory reminder: store only concise, verified decisions/fixes with memory-store.")
    raise SystemExit(0)
env=os.environ.copy()
env.setdefault("CODING_MEMORY_AGENT", "claude-code")
cmd=[str(ROOT/"scripts/memory-context"),"--query",query]
try:
    result=subprocess.run(cmd,cwd=event.get("cwd") or os.getcwd(),env=env,text=True,capture_output=True,timeout=180)
    if result.stdout: print(result.stdout,end="")
    if result.returncode and result.stderr: print(result.stderr,file=sys.stderr,end="")
except Exception as exc:
    print(f"coding-memory hook warning: {exc}",file=sys.stderr)
