"""Minimal AniList GraphQL client.

Used purely for browsing metadata (titles, cover art, synopsis, episode
counts) so the launcher can show a Hayase-style poster grid. Playback
never touches AniList -- it always goes through ani-cli/allanime.

AniList's public API needs no API key for read-only queries like this.
"""
import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field

API_URL = "https://graphql.anilist.co"

_SEARCH_QUERY = """
query ($search: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      title { romaji english }
      coverImage { large medium }
      bannerImage
      description(asHtml: false)
      episodes
      averageScore
      format
      genres
      status
    }
  }
}
"""

_TRENDING_QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(type: ANIME, sort: TRENDING_DESC, status_in: [RELEASING, FINISHED]) {
      id
      title { romaji english }
      coverImage { large medium }
      bannerImage
      description(asHtml: false)
      episodes
      averageScore
      format
      genres
      status
    }
  }
}
"""


@dataclass
class AnimeResult:
    id: int
    title: str
    cover_url: str
    description: str
    episodes: int | None
    score: int | None
    format: str | None
    genres: list = field(default_factory=list)
    status: str | None = None
    banner_url: str | None = None


def _post(query: str, variables: dict, timeout: float = 8.0) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _to_result(node: dict) -> AnimeResult:
    title = node["title"].get("english") or node["title"].get("romaji") or "Untitled"
    cover = (node.get("coverImage") or {}).get("large") or (node.get("coverImage") or {}).get("medium") or ""
    desc = (node.get("description") or "").replace("<br>", "\n").replace("<i>", "").replace("</i>", "")
    return AnimeResult(
        id=node["id"],
        title=title,
        cover_url=cover,
        description=desc.strip(),
        episodes=node.get("episodes"),
        score=node.get("averageScore"),
        format=node.get("format"),
        genres=node.get("genres") or [],
        status=node.get("status"),
        banner_url=node.get("bannerImage"),
    )


def search(query: str, page: int = 1, per_page: int = 20) -> list[AnimeResult]:
    if not query.strip():
        return []
    try:
        data = _post(_SEARCH_QUERY, {"search": query, "page": page, "perPage": per_page})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []
    media = (((data or {}).get("data") or {}).get("Page") or {}).get("media") or []
    return [_to_result(m) for m in media]


def trending(page: int = 1, per_page: int = 20) -> list[AnimeResult]:
    try:
        data = _post(_TRENDING_QUERY, {"page": page, "perPage": per_page})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []
    media = (((data or {}).get("data") or {}).get("Page") or {}).get("media") or []
    return [_to_result(m) for m in media]


def fetch_image_bytes(url: str, timeout: float = 8.0) -> bytes | None:
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError):
        return None
