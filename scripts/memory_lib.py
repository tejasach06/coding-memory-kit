#!/usr/bin/env python3
"""Small, dependency-free MCP client for the coding-memory kit."""
import argparse
import base64
import fcntl
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_MCP_URL = "http://192.168.0.9:8000/mcp/"
DEFAULT_QDRANT_URL = "http://192.168.0.9:6333"
DEFAULT_COLLECTION = "agent-memories"
DEFAULT_MAX_BYTES = 16 * 1024


def env(name, default=None):
    value = os.environ.get(name, default)
    return os.path.expanduser(value) if isinstance(value, str) else value


def project_id():
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        root = os.getcwd()
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(root).name.lower()).strip("-") or "unknown-project"
    digest = hashlib.sha256(os.path.realpath(root).encode()).hexdigest()[:12]
    return f"{base}-{digest}"


def redact(text):
    patterns = [
        (r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]"),
        (r"(?i)(https?://)([^:/\s]+):([^@\s]+)@", r"\1[REDACTED]:[REDACTED]@"),
        (r"(?i)(?:^|[\s,;])((?:aws[_-]?(?:secret[_-]?access|access[_-]?secret)[_-]?key|(?:secret|access)[_-]?key|password|passwd|token|api[_-]?key|client[_-]?secret|private[_-]?key))\s*[:=]\s*([\"']?)[^\s,;\"']+", r" \1=\2[REDACTED]"),
        (r"\b(?:sk|ghp|github_pat|glpat)-[A-Za-z0-9_-]{12,}\b", "[REDACTED]"),
        (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED]"),
        (r"-----BEGIN [A-Z0-9 ]+-----.*?-----END [A-Z0-9 ]+-----", "[REDACTED KEY]"),
        (r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[REDACTED JWT]"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)
    return text


def max_bytes():
    try:
        value = int(env("CODING_MEMORY_MAX_BYTES", str(DEFAULT_MAX_BYTES)))
    except ValueError as exc:
        raise RuntimeError("CODING_MEMORY_MAX_BYTES must be an integer") from exc
    if value < 256:
        raise RuntimeError("CODING_MEMORY_MAX_BYTES must be at least 256")
    return value


def bounded_content(content):
    content = redact(content.strip())
    if not content:
        raise RuntimeError("empty memory refused")
    size = len(content.encode("utf-8"))
    if size > max_bytes():
        raise RuntimeError(f"memory is {size} bytes; limit is {max_bytes()} bytes")
    return content


def sse_json(body):
    events = []
    for line in body.splitlines():
        if line.startswith("data:"):
            raw = line[5:].strip()
            if raw:
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    if events:
        return events[-1]
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"MCP returned no JSON response: {body[:500]}") from exc


def post(url, payload, session=None):
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    api_key = env("CODING_MEMORY_MCP_API_KEY", "")
    if api_key:
        headers["X-API-Key"] = api_key
    if session:
        headers["Mcp-Session-Id"] = session
    req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urlopen(req, timeout=float(env("CODING_MEMORY_TIMEOUT", "180"))) as response:
            return dict(response.headers), response.read().decode(errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"MCP HTTP {exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"MCP connection failed: {exc.reason}") from exc


def call_tool(tool, arguments):
    if env("CODING_MEMORY_DISABLED", "0") == "1":
        raise RuntimeError("coding memory disabled by CODING_MEMORY_DISABLED=1")
    url = env("CODING_MEMORY_MCP_URL", DEFAULT_MCP_URL).rstrip("/") + "/"
    headers, body = post(url, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "coding-memory-kit", "version": "1.1.0"}}})
    session = headers.get("mcp-session-id") or headers.get("Mcp-Session-Id")
    init = sse_json(body)
    if "error" in init:
        raise RuntimeError(str(init["error"]))
    post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    _, body = post(url, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}, session)
    result = sse_json(body)
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    returned = result.get("result", {})
    if returned.get("isError"):
        raise RuntimeError(text_result(returned) or "MCP tool returned isError")
    return returned


def text_result(result):
    content = result.get("content", [])
    return "\n".join(item.get("text", "") for item in content if item.get("type") == "text")


def state_path():
    return Path(env("CODING_MEMORY_STATE_DIR", "~/.coding-memory")) / "fingerprints.json"


def fingerprint(scope, namespace, content):
    return hashlib.sha256(f"{scope}\0{namespace}\0{content}".encode()).hexdigest()


def load_state_locked(handle):
    handle.seek(0)
    try:
        return json.load(handle)
    except (ValueError, json.JSONDecodeError):
        return {}


def save_state_locked(handle, state):
    handle.seek(0)
    handle.truncate()
    handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def state_lock():
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    return handle


def store(content, scope, verified, source, agent, confirm_global):
    content = bounded_content(content)
    if scope not in {"project", "global-preference", "global-fact"}:
        raise RuntimeError("scope must be project, global-preference, or global-fact")
    if scope == "global-preference" and (source not in {"user", "explicit-user", "user-confirmed"} or not confirm_global):
        raise RuntimeError("global-preference requires --confirm-global and an explicit user source")
    if scope == "global-fact" and not verified:
        raise RuntimeError("global-fact requires --verified")
    namespace = "__global__" if scope != "project" else project_id()
    fp = fingerprint(scope, namespace, content)
    now = datetime.now(timezone.utc).isoformat()
    state_handle = state_lock()
    try:
        state = load_state_locked(state_handle)
        if fp in state:
            print(json.dumps({"status": "duplicate", "fingerprint": fp, "source": "local-state"}))
            return
        # Check the shared store too, so separate agents/machines deduplicate.
        existing = text_result(call_tool("qdrant-find", {"query": content, "query_filter": {"must": [{"key": "metadata.fingerprint", "match": {"value": fp}}]}}))
        if "<entry>" in existing:
            print(json.dumps({"status": "duplicate", "fingerprint": fp, "source": "qdrant"}))
            state[fp] = {"timestamp": now, "scope": scope, "project": namespace}
            save_state_locked(state_handle, state)
            return
        metadata = {"scope": scope, "project": namespace, "agent": agent, "source": source, "verified": verified, "timestamp": now, "fingerprint": fp}
        header = f"[coding-memory scope={scope} project={namespace}]"
        result = call_tool("qdrant-store", {"information": f"{header}\n{content}", "metadata": metadata})
        state[fp] = {"timestamp": now, "scope": scope, "project": namespace}
        save_state_locked(state_handle, state)
    finally:
        fcntl.flock(state_handle.fileno(), fcntl.LOCK_UN)
        state_handle.close()
    print(text_result(result) or json.dumps(result))


def filters_for(scope, namespace):
    must = [{"key": "metadata.scope", "match": {"value": scope}}, {"key": "metadata.project", "match": {"value": namespace}}]
    return {"must": must}


def retrieve(query, agent, strict=False):
    namespace = project_id()
    queries = [
        ("global-preference", "__global__", f"global preferences user conventions {query}"),
        ("global-fact", "__global__", f"global verified facts {query}"),
        ("project", namespace, f"project {namespace} {query}"),
    ]
    parts = []
    failures = []
    for scope, target, q in queries:
        try:
            out = text_result(call_tool("qdrant-find", {"query": q, "query_filter": filters_for(scope, target)}))
            if out:
                parts.append(f"[{scope}]\n{out}")
        except Exception as exc:
            failures.append(f"{scope}: {exc}")
            if strict:
                raise
    if failures and strict:
        raise RuntimeError("; ".join(failures))
    if failures:
        print("memory retrieval warning: " + "; ".join(failures), file=sys.stderr)
    if parts:
        print("\n\n".join(parts))


def forget(fingerprint_value):
    url = env("CODING_MEMORY_QDRANT_REST_URL", DEFAULT_QDRANT_URL).rstrip("/") + "/collections/" + env("CODING_MEMORY_COLLECTION", DEFAULT_COLLECTION) + "/points/delete"
    payload = {"filter": {"must": [{"key": "metadata.fingerprint", "match": {"value": fingerprint_value}}]}}
    headers = {"Content-Type": "application/json"}
    key = env("CODING_MEMORY_QDRANT_API_KEY", "")
    if key:
        headers["api-key"] = key
    req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urlopen(req, timeout=float(env("CODING_MEMORY_TIMEOUT", "180"))) as response:
            print(response.read().decode(errors="replace"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Qdrant delete failed: {exc}") from exc


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("retrieve"); r.add_argument("--query", required=True); r.add_argument("--agent", default=env("CODING_MEMORY_AGENT", "unknown-agent")); r.add_argument("--strict", action="store_true")
    s = sub.add_parser("store"); s.add_argument("--scope", default="project"); s.add_argument("--verified", action="store_true"); s.add_argument("--source", required=True); s.add_argument("--confirm-global", action="store_true"); s.add_argument("--agent", default=env("CODING_MEMORY_AGENT", "unknown-agent")); s.add_argument("--content")
    f = sub.add_parser("forget"); f.add_argument("--fingerprint", required=True)
    args = parser.parse_args()
    if args.cmd == "retrieve": retrieve(args.query, args.agent, args.strict)
    elif args.cmd == "store": store(args.content if args.content is not None else sys.stdin.read(), args.scope, args.verified, args.source, args.agent, args.confirm_global)
    else: forget(args.fingerprint)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"coding-memory: {exc}", file=sys.stderr)
        raise SystemExit(2)
