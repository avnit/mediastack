#!/usr/bin/env python3
"""Tailscale device collector for the Homarr "Tailscale" custom widget.

Serves GET /tailscale/devices as JSON, from `tailscale status --json` on this
host. Only name, OS, online state and last-seen time leave the machine: no
keys, addresses, routes or user IDs.

  {"collectedAt": "<ISO time>", "devices": [
      {"id": "...", "name": "...", "os": "...", "online": true|false|null,
       "isSelf": true|false, "lastSeen": "<ISO time>"|null}, ...]}

The request must carry `Authorization: Bearer <token>`. The token is read from
a file on every request, so it can be rotated without a restart.

Environment:
  TS_COLLECTOR_BIND        address to listen on   (default 192.168.0.17)
  TS_COLLECTOR_PORT        port                   (default 18082)
  TS_COLLECTOR_TOKEN_FILE  bearer token file      (default /root/.tailscale-collector-token)

Installed by tailscale-collector.service; see README.md, "Tailscale widget in Homarr".
"""
import hmac
import json
import os
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BIND = os.environ.get("TS_COLLECTOR_BIND", "192.168.0.17")
PORT = int(os.environ.get("TS_COLLECTOR_PORT", "18082"))
TOKEN_FILE = os.environ.get("TS_COLLECTOR_TOKEN_FILE", "/root/.tailscale-collector-token")
NEVER = "0001-01-01T00:00:00Z"   # Go's zero time: tailscale has no last-seen value


def device(node, is_self=False):
    name = (node.get("DNSName") or "").split(".")[0] or node.get("HostName") or "unknown"
    online = node.get("Online")
    last_seen = node.get("LastSeen")
    return {
        "id": str(node.get("ID") or name),
        "name": name,
        "os": node.get("OS") or "unknown",
        "online": online if isinstance(online, bool) else None,   # unknown stays unknown
        "isSelf": is_self,
        "lastSeen": None if not last_seen or last_seen == NEVER else last_seen,
    }


def collect():
    out = subprocess.run(["tailscale", "status", "--json"], capture_output=True,
                         text=True, timeout=8, check=True).stdout
    status = json.loads(out)
    if status.get("BackendState") != "Running":
        raise RuntimeError(f"tailscale backend is {status.get('BackendState')}")
    devices = [device(status["Self"], is_self=True)]
    devices += [device(peer) for peer in (status.get("Peer") or {}).values()]
    return {"collectedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "devices": devices}


class Handler(BaseHTTPRequestHandler):
    server_version = "tailscale-collector"

    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def authorised(self):
        try:
            token = open(TOKEN_FILE).read().strip()
        except OSError:
            return False
        sent = self.headers.get("Authorization", "")
        return bool(token) and hmac.compare_digest(sent, f"Bearer {token}")

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"ok": True})
        if self.path.split("?")[0] != "/tailscale/devices":
            return self.reply(404, {"error": "not found"})
        if not self.authorised():
            return self.reply(401, {"error": "unauthorized"})
        try:
            self.reply(200, collect())
        except Exception as exc:   # the widget shows "collector unavailable", not "offline"
            self.reply(503, {"error": f"tailscale status failed: {type(exc).__name__}"})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    print(f"tailscale-collector on http://{BIND}:{PORT}", flush=True)
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
