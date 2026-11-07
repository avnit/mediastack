#!/usr/bin/env python3
"""
Container status dashboard for the mediastack.

Reads live container state from the Docker socket and the homepage.* labels that
every service in docker-compose.yaml already carries, so there is no second place
to keep service metadata in sync.

stdlib only - no pip install, nothing extra to keep patched.
Endpoints:  /        HTML dashboard (auto-refreshes)
            /api     JSON, same data
            /healthz liveness
"""
import http.client
import http.server
import json
import os
import socket
import html
from datetime import datetime

DOCKER_SOCK = os.environ.get("DOCKER_SOCK", "/var/run/docker.sock")
PORT = int(os.environ.get("PORT", "8400"))
PROJECT = os.environ.get("COMPOSE_PROJECT", "")  # blank = show every project

GROUP_ORDER = ["Dashboard", "Media", "Arr Apps", "Downloads",
               "Monitoring", "Security", "Remote Access", "Infrastructure"]


class _UnixHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that talks to a unix domain socket."""

    def __init__(self, sock_path):
        super().__init__("localhost")
        self._sock_path = sock_path

    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(self._sock_path)
        self.sock = s


def docker_get(path):
    conn = _UnixHTTPConnection(DOCKER_SOCK)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            raise RuntimeError(f"docker API {resp.status}: {body[:200]!r}")
        return json.loads(body)
    finally:
        conn.close()


def classify(state, status):
    """Map docker state/status to one of: ok / warn / down."""
    if "(unhealthy)" in status:
        return "down", "unhealthy"
    if "health: starting" in status:
        return "warn", "starting"
    if state == "running":
        return "ok", "healthy" if "(healthy)" in status else "running"
    if state in ("restarting", "created", "paused"):
        return "warn", state
    return "down", state


def collect():
    containers = docker_get("/containers/json?all=1")
    items = []
    for c in containers:
        labels = c.get("Labels") or {}
        if PROJECT and labels.get("com.docker.compose.project") != PROJECT:
            continue
        name = (c.get("Names") or ["/unknown"])[0].lstrip("/")
        state = c.get("State", "unknown")
        status = c.get("Status", "")
        level, label = classify(state, status)
        items.append({
            "name": name,
            "display": labels.get("homepage.name") or name,
            "href": labels.get("homepage.href", ""),
            "group": labels.get("homepage.group", "Other"),
            "description": labels.get("homepage.description", ""),
            "state": state,
            "status": status,
            "level": level,
            "state_label": label,
            "image": c.get("Image", ""),
            "project": labels.get("com.docker.compose.project", ""),
        })
    items.sort(key=lambda i: i["display"].lower())
    return items


def render(items):
    totals = {"ok": 0, "warn": 0, "down": 0}
    for i in items:
        totals[i["level"]] += 1

    groups = {}
    for i in items:
        groups.setdefault(i["group"], []).append(i)
    ordered = [g for g in GROUP_ORDER if g in groups] + \
              sorted(g for g in groups if g not in GROUP_ORDER)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = [f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>mediastack status</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#fff; --fg:#1b1f24; --muted:#636c76; --line:#d8dee4;
    --ok:#1a7f37; --warn:#9a6700; --down:#cf222e;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0d1117; --card:#161b22; --fg:#e6edf3; --muted:#8b949e;
             --line:#30363d; --ok:#3fb950; --warn:#d29922; --down:#f85149; }}
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--fg);
       font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       padding:24px 16px}}
  .wrap{{max-width:1100px;margin:0 auto}}
  h1{{font-size:20px;margin:0 0 4px}}
  .sub{{color:var(--muted);font-size:13px;margin-bottom:20px}}
  .tiles{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:26px}}
  .tile{{background:var(--card);border:1px solid var(--line);border-radius:8px;
        padding:10px 16px;min-width:104px}}
  .tile b{{display:block;font-size:22px;line-height:1.2}}
  .tile span{{color:var(--muted);font-size:12px}}
  h2{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
     margin:26px 0 10px;font-weight:600}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:10px}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:8px;
        padding:12px 14px;display:block;text-decoration:none;color:inherit}}
  a.card:hover{{border-color:var(--muted)}}
  .row{{display:flex;align-items:center;gap:8px}}
  .dot{{width:9px;height:9px;border-radius:50%;flex:0 0 auto}}
  .ok .dot{{background:var(--ok)}} .warn .dot{{background:var(--warn)}} .down .dot{{background:var(--down)}}
  .nm{{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .st{{margin-left:auto;font-size:11px;font-variant:all-small-caps;letter-spacing:.04em}}
  .ok .st{{color:var(--ok)}} .warn .st{{color:var(--warn)}} .down .st{{color:var(--down)}}
  .de{{color:var(--muted);font-size:12px;margin-top:4px;overflow:hidden;
      text-overflow:ellipsis;white-space:nowrap}}
  .no{{color:var(--muted);font-size:11px;margin-top:4px}}
  footer{{margin-top:32px;color:var(--muted);font-size:12px}}
</style></head><body><div class="wrap">
<h1>mediastack status</h1>
<div class="sub">{len(items)} containers &middot; refreshed {now} &middot; auto-refresh 20s</div>
<div class="tiles">
  <div class="tile"><b style="color:var(--ok)">{totals['ok']}</b><span>running</span></div>
  <div class="tile"><b style="color:var(--warn)">{totals['warn']}</b><span>starting / warn</span></div>
  <div class="tile"><b style="color:var(--down)">{totals['down']}</b><span>stopped / unhealthy</span></div>
</div>"""]

    for g in ordered:
        out.append(f"<h2>{html.escape(g)}</h2><div class=\"grid\">")
        for i in groups[g]:
            nm = html.escape(i["display"])
            de = html.escape(i["description"] or i["image"])
            st = html.escape(i["state_label"])
            tip = html.escape(f'{i["name"]} - {i["status"]}')
            inner = (f'<div class="row"><span class="dot"></span>'
                     f'<span class="nm">{nm}</span><span class="st">{st}</span></div>'
                     f'<div class="de">{de}</div>')
            if i["href"]:
                out.append(f'<a class="card {i["level"]}" href="{html.escape(i["href"])}" '
                           f'target="_blank" rel="noopener" title="{tip}">{inner}</a>')
            else:
                out.append(f'<div class="card {i["level"]}" title="{tip}">{inner}'
                           f'<div class="no">no link configured</div></div>')
        out.append("</div>")

    out.append('<footer>Built from live Docker state and the '
               '<code>homepage.*</code> labels in docker-compose.yaml. '
               'Cards with a link open the app in a new tab.</footer>'
               "</div></body></html>")
    return "".join(out)


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "statuspage/1.0"

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if path == "/healthz":
                return self._send(200, "ok", "text/plain; charset=utf-8")
            items = collect()
            if path == "/api":
                return self._send(200, json.dumps(items, indent=2),
                                  "application/json; charset=utf-8")
            if path == "/":
                return self._send(200, render(items))
            self._send(404, "not found", "text/plain; charset=utf-8")
        except Exception as exc:  # surface the cause instead of a blank 500
            self._send(500, f"<pre>statuspage error: {html.escape(str(exc))}</pre>")

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"statuspage listening on :{PORT}", flush=True)
    srv.serve_forever()
