"""Watch Party playback backend.

Inspired by the UX of Seanime's Nakama (name a party, pick a background,
watch together) but built on two pieces of existing, battle-tested
software instead of a custom P2P protocol:

  1. ani-cli itself already has a --syncplay flag for this exact use case
     (several people already use `ani-cli -s` to watch together). We use
     the same idea but drive Syncplay directly so we can set our own
     room name, server and username -- ani-cli's built-in -s doesn't
     expose those as flags.
  2. Syncplay (https://syncplay.pl) -- open source, has existed for over
     a decade, handles play/pause/seek sync + chat. Verified CLI flags
     used below: --host, --room, --name, --no-gui, --player-path, and
     a trailing "--" for extra player args.

Important honesty note: Syncplay does NOT transmit video. Every party
member resolves and streams their OWN copy of the episode via ani-cli/
allanime; Syncplay only keeps everyone's playback position and pause
state in lockstep. That means everyone in a party must be watching the
same anime/episode/sub-or-dub for sync to make sense -- the party
metadata (see party_directory.py) carries exactly that info so joiners
resolve the same thing the host is watching.
"""
import os
import re
import shutil
import subprocess
from dataclasses import dataclass

DEFAULT_SYNCPLAY_SERVER = "syncplay.pl:8999"  # the project's own public server


class SyncplayNotFound(RuntimeError):
    pass


class StreamResolveError(RuntimeError):
    pass


def syncplay_installed() -> bool:
    return shutil.which("syncplay") is not None


def resolve_stream_url(title: str, episode: int, dub: bool = False,
                        quality: str = "best", search_index: int = 1,
                        timeout: float = 25.0) -> str:
    """Uses ani-cli's own ANI_CLI_PLAYER=debug mode to print the resolved
    stream link instead of playing it, so we can hand that URL to
    Syncplay ourselves. Never opens a terminal or a player."""
    if shutil.which("ani-cli") is None:
        raise StreamResolveError("ani-cli was not found on PATH.")

    cmd = ["ani-cli", title, "-S", str(search_index), "-e", str(episode), "-q", quality]
    if dub:
        cmd.append("--dub")

    env = os.environ.copy()
    env["ANI_CLI_PLAYER"] = "debug"

    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise StreamResolveError("Timed out resolving the episode link.") from exc

    urls = re.findall(r"https?://\S+", proc.stdout)
    if not urls:
        raise StreamResolveError(
            "Couldn't resolve a stream link for that title/episode. "
            "Double check the title matches exactly what ani-cli would find."
        )
    return urls[-1]  # debug mode prints the chosen-quality link last


@dataclass
class PartySession:
    room: str
    username: str
    stream_url: str
    server: str = DEFAULT_SYNCPLAY_SERVER
    player: str = "mpv"


def launch_syncplay(session: PartySession):
    if not syncplay_installed():
        raise SyncplayNotFound(
            "syncplay was not found on PATH. Install it (see README) to use Watch Party."
        )
    player_path = shutil.which(session.player) or session.player
    cmd = [
        "syncplay",
        "--host", session.server,
        "--name", session.username,
        "--room", session.room,
        "--no-gui",
        "--player-path", player_path,
        session.stream_url,
    ]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
