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

# A bare urllib request sends "Python-urllib/3.x" as its User-Agent, which
# a lot of APIs behind bot protection (Cloudflare etc.) silently reject or
# rate-limit. Identify ourselves properly instead.
_USER_AGENT = "Hyprnime/0.1 (+https://github.com/NopeVfx/hyprnime)"

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


class AniListError(RuntimeError):
    """Raised for anything that stops a query from returning real data --
    network failure, HTTP error, or a GraphQL-level error payload. Callers
    should catch this and show it, not treat a failure as 'zero results'."""


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
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")[:300]
        raise AniListError(f"AniList returned HTTP {exc.code}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise AniListError(f"Couldn't reach AniList: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AniListError("Timed out contacting AniList.") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AniListError("AniList returned something that wasn't valid JSON.") from exc

    if data.get("errors"):
        messages = "; ".join(e.get("message", "unknown error") for e in data["errors"])
        raise AniListError(f"AniList rejected the query: {messages}")

    return data


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
    """Raises AniListError on any failure -- callers must catch it and show
    the message, an empty return here would hide the real problem."""
    if not query.strip():
        return []
    data = _post(_SEARCH_QUERY, {"search": query, "page": page, "perPage": per_page})
    media = (((data or {}).get("data") or {}).get("Page") or {}).get("media") or []
    return [_to_result(m) for m in media]


def trending(page: int = 1, per_page: int = 20) -> list[AnimeResult]:
    """Raises AniListError on any failure -- see search()."""
    data = _post(_TRENDING_QUERY, {"page": page, "perPage": per_page})
    media = (((data or {}).get("data") or {}).get("Page") or {}).get("media") or []
    return [_to_result(m) for m in media]


def fetch_image_bytes(url: str, timeout: float = 8.0) -> bytes | None:
    """Cover/banner images are a "nice to have" -- unlike search()/trending()
    this stays silent on failure so a missing image never blocks browsing."""
    if not url:
        return None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError):
        return None
