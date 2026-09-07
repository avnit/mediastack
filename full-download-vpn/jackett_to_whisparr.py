#!/usr/bin/env python3
"""Sync every configured Jackett indexer into Whisparr as an indexer.

Idempotent: indexers already present in Whisparr (matched by name) are skipped.

Modes
  torznab (default)  Jackett Torznab feed -> Whisparr "Torznab" indexer.
                     RSS + automatic search + interactive search.
  rss                Jackett "Copy RSS Feed" URL -> Whisparr "Torrent RSS Feed".
                     RSS only, no search. Mirrors the manual add you did.

Environment
  JACKETT_URL              e.g. http://192.168.0.185:9117
  JACKETT_API_KEY          Jackett dashboard -> "API Key"
  WHISPARR_URL             e.g. http://192.168.0.17:6969
  WHISPARR_API_KEY         Whisparr -> Settings -> General -> Security
  JACKETT_URL_FOR_WHISPARR optional; Jackett URL as reachable *from Whisparr*
                           (docker network alias etc). Defaults to JACKETT_URL.

Usage
  python3 jackett_to_whisparr.py --dry-run
  python3 jackett_to_whisparr.py --xxx-only
  python3 jackett_to_whisparr.py --mode rss --force
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger("jackett2whisparr")

XXX_CATEGORIES: list[int] = [
    6000, 6010, 6020, 6030, 6040, 6045, 6050, 6060, 6070, 6080, 6090,
]
NAME_SUFFIX = " (Jackett)"
HTTP_TIMEOUT = 60


class SyncError(RuntimeError):
    """Fatal configuration or transport error."""


@dataclass(frozen=True)
class JackettIndexer:
    id: str
    title: str
    indexer_type: str
    categories: frozenset[int] = field(default_factory=frozenset)

    @property
    def has_xxx(self) -> bool:
        return any(6000 <= c < 7000 for c in self.categories)


@dataclass
class Config:
    jackett_url: str
    jackett_api_key: str
    whisparr_url: str
    whisparr_api_key: str
    jackett_url_for_whisparr: str

    @classmethod
    def from_env(cls) -> "Config":
        def req(name: str) -> str:
            val = os.environ.get(name, "").strip()
            if not val:
                raise SyncError(f"missing required env var {name}")
            return val.rstrip("/")

        jackett_url = req("JACKETT_URL")
        return cls(
            jackett_url=jackett_url,
            jackett_api_key=req("JACKETT_API_KEY"),
            whisparr_url=req("WHISPARR_URL"),
            whisparr_api_key=req("WHISPARR_API_KEY"),
            jackett_url_for_whisparr=os.environ.get(
                "JACKETT_URL_FOR_WHISPARR", jackett_url
            ).rstrip("/"),
        )


# --------------------------------------------------------------------------- #
# Log hygiene
# --------------------------------------------------------------------------- #
# Whisparr echoes the whole torznab URL back in its validation errors, and that
# URL carries the Jackett API key as a query parameter. Logging it verbatim
# leaks the key into terminal scrollback, log files and pasted output.
_SECRET_QS_RE = re.compile(r"((?:api_?key|apikey|passkey|token)=)[^&\s\]\"']+", re.I)

# Whisparr's wording when a test query succeeded but matched nothing in the
# requested categories. Expected for a general indexer queried for XXX, so it
# is reported separately from genuine failures.
_NO_RESULTS = "no results in the configured categories"


def redact(text: Any) -> str:
    return _SECRET_QS_RE.sub(r"\1<redacted>", str(text))


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: Any | None = None,
) -> tuple[int, bytes]:
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise SyncError(f"{method} {url} failed: {exc.reason}") from exc


# --------------------------------------------------------------------------- #
# Jackett
# --------------------------------------------------------------------------- #
def fetch_jackett_indexers(cfg: Config) -> list[JackettIndexer]:
    qs = urllib.parse.urlencode(
        {"apikey": cfg.jackett_api_key, "t": "indexers", "configured": "true"}
    )
    url = f"{cfg.jackett_url}/api/v2.0/indexers/all/results/torznab/api?{qs}"
    status, raw = _request("GET", url)
    if status != 200:
        raise SyncError(f"Jackett returned HTTP {status}: {raw[:200]!r}")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SyncError(f"Jackett response is not XML: {exc}") from exc

    out: list[JackettIndexer] = []
    for node in root.iter("indexer"):
        if node.get("configured", "true").lower() != "true":
            continue
        cats: set[int] = set()
        for cat in node.iter("category"):
            cid = cat.get("id")
            if cid and cid.isdigit():
                cats.add(int(cid))
        out.append(
            JackettIndexer(
                id=node.get("id", ""),
                title=(node.findtext("title") or node.get("id", "")).strip(),
                indexer_type=(node.findtext("type") or "").strip(),
                categories=frozenset(cats),
            )
        )
    LOG.info("Jackett: %d configured indexers", len(out))
    return out


def jackett_torznab_base(cfg: Config, idx: JackettIndexer) -> str:
    return f"{cfg.jackett_url_for_whisparr}/api/v2.0/indexers/{idx.id}/results/torznab/"


def jackett_rss_url(cfg: Config, idx: JackettIndexer) -> str:
    qs = urllib.parse.urlencode(
        {"apikey": cfg.jackett_api_key, "t": "search", "cat": "", "q": ""}
    )
    return f"{jackett_torznab_base(cfg, idx)}api?{qs}"


# --------------------------------------------------------------------------- #
# Whisparr
# --------------------------------------------------------------------------- #
class Whisparr:
    def __init__(self, cfg: Config) -> None:
        self._base = f"{cfg.whisparr_url}/api/v3"
        self._headers = {"X-Api-Key": cfg.whisparr_api_key}

    def _call(self, method: str, path: str, body: Any | None = None) -> tuple[int, Any]:
        status, raw = _request(method, f"{self._base}{path}", self._headers, body)
        if status == 401:
            raise SyncError("Whisparr rejected the API key (401)")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw.decode(errors="replace")
        return status, parsed

    def existing_indexers(self) -> list[dict[str, Any]]:
        status, data = self._call("GET", "/indexer")
        if status != 200:
            raise SyncError(f"GET /indexer -> HTTP {status}: {data}")
        return data

    def schema_for(self, implementation: str) -> dict[str, Any]:
        status, data = self._call("GET", "/indexer/schema")
        if status != 200:
            raise SyncError(f"GET /indexer/schema -> HTTP {status}: {data}")
        for entry in data:
            if entry.get("implementation") == implementation:
                return entry
        names = sorted(e.get("implementation", "?") for e in data)
        raise SyncError(f"implementation {implementation!r} not in schema: {names}")

    def add_indexer(self, payload: dict[str, Any], force: bool) -> tuple[int, Any]:
        qs = "?forceSave=true" if force else ""
        return self._call("POST", f"/indexer{qs}", payload)


def _set_field(payload: dict[str, Any], name: str, value: Any) -> None:
    for f in payload["fields"]:
        if f["name"] == name:
            f["value"] = value
            return
    LOG.debug("schema has no field %r; skipping", name)


def resolve_categories(idx: JackettIndexer, requested: list[int] | None) -> list[int]:
    """None => auto: indexer's own XXX caps, else all its caps, else defaults."""
    if requested is not None:
        return requested
    xxx = sorted(c for c in idx.categories if 6000 <= c < 7000)
    if xxx:
        return xxx
    return sorted(idx.categories) or XXX_CATEGORIES


def build_payload(
    cfg: Config,
    schema: dict[str, Any],
    idx: JackettIndexer,
    mode: str,
    categories: list[int] | None,
    disabled: bool = False,
) -> dict[str, Any]:
    p = copy.deepcopy(schema)
    p.pop("id", None)
    p.pop("presets", None)
    p["name"] = f"{idx.title}{NAME_SUFFIX}"
    p.setdefault("priority", 25)
    p.setdefault("tags", [])

    # Whisparr only runs the connectivity test when at least one enable* flag
    # is set. --disabled saves the indexer untested; enable it later in the UI.
    p["enableRss"] = not disabled
    if mode == "torznab":
        p["enableAutomaticSearch"] = not disabled
        p["enableInteractiveSearch"] = not disabled
        _set_field(p, "baseUrl", jackett_torznab_base(cfg, idx))
        _set_field(p, "apiPath", "/api")
        _set_field(p, "apiKey", cfg.jackett_api_key)
        _set_field(p, "categories", resolve_categories(idx, categories))
        _set_field(p, "minimumSeeders", 1)
    else:  # rss
        p["enableAutomaticSearch"] = False
        p["enableInteractiveSearch"] = False
        _set_field(p, "baseUrl", jackett_rss_url(cfg, idx))
        _set_field(p, "allowZeroSize", True)

    # Strip UI-only keys the API ignores/rejects on POST.
    for f in p["fields"]:
        for k in ("selectOptions", "helpText", "helpLink", "label", "order",
                  "advanced", "type", "privacy", "section", "hidden", "placeholder"):
            f.pop(k, None)
    return p


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("torznab", "rss"), default="torznab")
    ap.add_argument("--xxx-only", action="store_true",
                    help="only indexers whose Jackett caps advertise a 6xxx (XXX) category")
    ap.add_argument("--force", action="store_true",
                    help="POST with forceSave=true (skip Whisparr's connectivity test)")
    ap.add_argument("--disabled", action="store_true",
                    help="save with RSS/search flags off; skips Whisparr's test entirely")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--categories", default="auto",
                    help="torznab mode: 'auto' (indexer's own XXX caps, else all its caps), "
                         "'xxx' (fixed 6000-6090 list), or comma-separated IDs")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
    )
    try:
        cfg = Config.from_env()
        categories: list[int] | None
        if args.categories == "auto":
            categories = None
        elif args.categories == "xxx":
            categories = XXX_CATEGORIES
        else:
            categories = [int(c) for c in args.categories.split(",") if c.strip()]
        jackett = fetch_jackett_indexers(cfg)
        if args.xxx_only:
            jackett = [i for i in jackett if i.has_xxx]
            LOG.info("filtered to %d indexers with XXX caps", len(jackett))

        wh = Whisparr(cfg)
        existing = {i["name"].strip().lower() for i in wh.existing_indexers()}
        impl = "Torznab" if args.mode == "torznab" else "TorrentRssIndexer"
        schema = wh.schema_for(impl)
    except SyncError as exc:
        LOG.error("%s", exc)
        return 2

    added = skipped = failed = no_content = 0
    for idx in sorted(jackett, key=lambda i: i.title.lower()):
        name = f"{idx.title}{NAME_SUFFIX}"
        if name.lower() in existing:
            LOG.debug("skip (exists): %s", name)
            skipped += 1
            continue
        payload = build_payload(cfg, schema, idx, args.mode, categories, args.disabled)
        if args.dry_run:
            LOG.info("would add: %s  [%s]", name, idx.id)
            added += 1
            continue
        try:
            status, resp = wh.add_indexer(payload, args.force)
        except SyncError as exc:
            LOG.error("add failed: %s -> %s", name, redact(exc))
            failed += 1
            continue
        if status in (200, 201):
            LOG.info("added: %s", name)
            added += 1
        else:
            msg = resp
            if isinstance(resp, list):
                msg = "; ".join(str(e.get("errorMessage", e)) for e in resp)
            msg = redact(msg)
            if _NO_RESULTS in msg:
                # The indexer answered but carries nothing in these categories.
                # Normal for a general-purpose tracker queried for XXX.
                LOG.info("no matching content: %s", name)
                no_content += 1
            else:
                LOG.warning("rejected (HTTP %s): %s -> %s", status, name, msg)
                failed += 1

    LOG.info(
        "done: added=%d skipped=%d no-matching-content=%d failed=%d",
        added, skipped, no_content, failed,
    )
    if no_content and not args.xxx_only:
        LOG.info(
            "%d indexers answered but hold nothing in categories %s. "
            "Re-run with --xxx-only to try just the indexers whose Jackett "
            "capabilities advertise a 6xxx category.",
            no_content, args.categories,
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
