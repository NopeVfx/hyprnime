"""Thin client for the Party Directory server (see ../partydirectory.py)."""
import json
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass


class DirectoryError(RuntimeError):
    pass


class DirectoryNotConfigured(DirectoryError):
    pass


@dataclass
class PartyListing:
    id: str
    name: str
    anime_title: str
    episode: object
    dub: bool
    quality: str
    background_url: str
    host: str
    syncplay_server: str
    member_count: int
    created_at: float = 0.0
    last_seen: float = 0.0


def _base_url(server: str) -> str:
    server = (server or "").strip().rstrip("/")
    if not server:
        raise DirectoryNotConfigured(
            "No Party Directory server is configured. Set one in Settings > Watch Party, "
            "or self-host one with: python3 -m hyprnime.partydirectory"
        )
    if not server.startswith("http://") and not server.startswith("https://"):
        server = "http://" + server
    return server


def _request(method: str, url: str, data: dict | None = None, timeout: float = 6.0) -> dict:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", "")
        except Exception:
            detail = ""
        raise DirectoryError(detail or f"Directory server returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise DirectoryError(f"Couldn't reach the directory server: {exc.reason}") from exc


def create_party(server: str, name: str, anime_title: str, host: str,
                  episode=None, dub: bool = False, quality: str = "best",
                  background_url: str = "", syncplay_server: str = "") -> tuple[PartyListing, str]:
    """Returns (listing, host_token). Keep the token to heartbeat/close it."""
    payload = {
        "name": name, "anime_title": anime_title, "host": host,
        "episode": episode, "dub": dub, "quality": quality,
        "background_url": background_url, "syncplay_server": syncplay_server,
    }
    resp = _request("POST", f"{_base_url(server)}/parties", payload)
    token = resp.pop("token")
    return PartyListing(**resp), token


def search_parties(server: str, query: str = "") -> list[PartyListing]:
    url = f"{_base_url(server)}/parties?q={urllib.parse.quote(query)}"
    resp = _request("GET", url)
    return [PartyListing(**p) for p in resp.get("parties", [])]


def heartbeat(server: str, party_id: str, token: str, member_count: int | None = None):
    payload = {"token": token}
    if member_count is not None:
        payload["member_count"] = member_count
    _request("POST", f"{_base_url(server)}/parties/{party_id}/heartbeat", payload)


def close_party(server: str, party_id: str, token: str):
    _request("DELETE", f"{_base_url(server)}/parties/{party_id}", {"token": token})
