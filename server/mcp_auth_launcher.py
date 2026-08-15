#!/usr/bin/env python3
"""FastMCP launcher with a required X-API-Key/Authorization: Bearer gate."""
import argparse
import hmac
import os
import uvicorn
from mcp_server_qdrant.server import mcp

class APIKeyMiddleware:
    def __init__(self, app, api_key):
        self.app, self.api_key = app, api_key.encode()
    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            headers = dict(scope.get("headers", []))
            presented = headers.get(b"x-api-key", b"")
            auth = headers.get(b"authorization", b"")
            if not presented and auth.lower().startswith(b"bearer "):
                presented = auth[7:]
            if not hmac.compare_digest(presented, self.api_key):
                body = b"Unauthorized\n"
                await send({"type":"http.response.start","status":401,"headers":[(b"content-type",b"text/plain"),(b"content-length",str(len(body)).encode())]})
                await send({"type":"http.response.body","body":body})
                return
        await self.app(scope, receive, send)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--transport", choices=["sse","streamable-http"], required=True); a=p.parse_args()
    key=os.environ.get("MCP_API_KEY")
    if not key: raise SystemExit("MCP_API_KEY is required")
    app=APIKeyMiddleware(mcp.http_app(transport=a.transport, middleware=[]), key)
    uvicorn.run(app, host=os.environ.get("FASTMCP_SERVER_HOST","192.168.0.9"), port=int(os.environ.get("FASTMCP_SERVER_PORT","8000")), log_level=os.environ.get("FASTMCP_LOG_LEVEL","info").lower())
if __name__ == "__main__": main()
