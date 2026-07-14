#!/usr/bin/env python3
"""Hyprnime Party Directory -- a tiny, self-hostable "phone book" for
Watch Parties.

Syncplay itself has no room discovery: you must already know the exact
room name to join. This server is the missing piece that makes "search
a party by name" actually work -- it's a small JSON registry of open
parties (name, anime, episode, background, host) that a friend group
runs on any small box (a Pi, a VPS, a home server). It does NOT relay
video or playback sync -- that's still 100% Syncplay + everyone's own
ani-cli stream. This server only answers "what parties exist right now
and what are they watching".

Run it with:  python3 -m hyprnime.partydirectory --port 8730
Then point every client's Settings > Watch Party > Directory Server at
  http://<that-machine>:8730

Stdlib only, on purpose, so it has zero dependencies to self-host.
"""
import argparse
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PARTY_TTL_SECONDS = 6 * 60 * 60  # a party with no heartbeat this long is dropped

_lock = threading.Lock()
_parties: dict[str, dict] = {}   # party_id -> record (includes secret "token")


def _public(record: dict) -> dict:
    return {k: v for k, v in record.items() if k != "token"}


def _prune_expired():
    now = time.time()
    expired = [pid for pid, rec in _parties.items() if now - rec["last_seen"] > PARTY_TTL_SECONDS]
    for pid in expired:
        del _parties[pid]


class Handler(BaseHTTPRequestHandler):
    server_version = "HyprnimePartyDirectory/0.1"

    def _send_json(self, status: int, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def log_message(self, fmt, *args):
        pass  # keep it quiet; flip this on if you need to debug

    # ------------------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/parties":
            return self._send_json(404, {"error": "not found"})
        query = parse_qs(parsed.query)
        needle = (query.get("q", [""])[0] or "").strip().lower()

        with _lock:
            _prune_expired()
            records = [
                _public(rec) for rec in _parties.values()
                if needle in rec["name"].lower()
            ]
        records.sort(key=lambda r: r["created_at"], reverse=True)
        self._send_json(200, {"parties": records})

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/parties":
            data = self._read_json()
            if not data or not data.get("name") or not data.get("anime_title"):
                return self._send_json(400, {"error": "name and anime_title are required"})

            party_id = secrets.token_hex(4)
            token = secrets.token_hex(16)
            now = time.time()
            record = {
                "id": party_id,
                "token": token,
                "name": str(data["name"])[:80],
                "anime_title": str(data["anime_title"])[:200],
                "episode": data.get("episode"),
                "dub": bool(data.get("dub", False)),
                "quality": data.get("quality", "best"),
                "background_url": data.get("background_url", ""),
                "host": str(data.get("host", "someone"))[:60],
                "syncplay_server": data.get("syncplay_server", ""),
                "member_count": 1,
                "created_at": now,
                "last_seen": now,
            }
            with _lock:
                _prune_expired()
                _parties[party_id] = record
            return self._send_json(201, {**_public(record), "token": token})

        # /parties/<id>/heartbeat
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "parties" and parts[2] == "heartbeat":
            party_id = parts[1]
            data = self._read_json() or {}
            with _lock:
                rec = _parties.get(party_id)
                if not rec or rec["token"] != data.get("token"):
                    return self._send_json(403, {"error": "invalid party id or token"})
                rec["last_seen"] = time.time()
                if "member_count" in data:
                    rec["member_count"] = max(1, int(data["member_count"]))
            return self._send_json(200, {"ok": True})

        return self._send_json(404, {"error": "not found"})

    def do_DELETE(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "parties":
            party_id = parts[1]
            data = self._read_json() or {}
            with _lock:
                rec = _parties.get(party_id)
                if not rec or rec["token"] != data.get("token"):
                    return self._send_json(403, {"error": "invalid party id or token"})
                del _parties[party_id]
            return self._send_json(200, {"ok": True})
        return self._send_json(404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser(description="Hyprnime Party Directory server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8730)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Hyprnime Party Directory listening on {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
