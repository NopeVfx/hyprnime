<p align="center"><img src="data/hyprnime-wordmark.svg" alt="Hyprnime" width="420"></p>

A graphical anime browser/launcher for Arch Linux and Hyprland, in the spirit
of launchers like Hayase -- poster grid, search, episode list, a Settings
tab with theming -- but instead of torrents or browser extensions, playback
is handled entirely by **[ani-cli](https://github.com/pystardust/ani-cli)**.

It's a real GTK4/libadwaita app (not a rofi script pretending to be one), so
it looks and behaves like a normal application. The rofi integration means
you never have to open a terminal: install it, and it shows up as a
launchable app in rofi's `drun` mode (or any app launcher, dock, or keybind)
just like anything else.

## Features

- **Browse & search** anime with cover art and synopses via the public
  AniList API.
- **Sub/Dub + quality controls**, non-interactive playback through
  `ani-cli` -- mpv/VLC just opens as its own window, no terminal, ever.
- **Continue Watching**, synced with ani-cli's own history file.
- **Watch Party** -- host or join synced watch-alongs with friends (see
  below).
- **Offline Mode** -- download episodes and build a local library you can
  watch with zero network (see below).
- **Settings** -- Light/Dark/System + 18 "custom theme" colour schemes.

## Please read: Sub/Dub and subtitles, honestly

I looked this up against ani-cli's own FAQ before building this, so the
Settings tab doesn't promise something the backend can't do:

- **Sub vs Dub** is fully supported and works exactly like you'd expect --
  it's a toggle per anime, and a default in Settings.
- **Subtitle language / turning subtitles off is *not* possible.** ani-cli's
  source (allanime) delivers subtitles hardcoded (burned) into the video
  itself. There's no subtitle track to restyle or swap language on, and no
  flag to disable them -- this is true of the `ani-cli` CLI tool itself, not
  a limitation of this app. The Settings > "Subtitles & Audio" section
  explains this in the UI rather than hiding a dropdown that wouldn't do
  anything.

## Watch Party

Inspired by the UX of Seanime's Nakama (name a party, pick a background,
pick an anime, others find and join it) but built on two pieces of
existing, well-established software instead of a custom relay protocol:

1. **[Syncplay](https://syncplay.pl)** keeps everyone's play/pause/seek
   position in lockstep. It does **not** transmit video -- every party
   member streams their **own** copy of the episode through their own
   `ani-cli`. That means everyone in a party needs to be pointed at the
   same anime/episode/sub-or-dub, which is exactly what party metadata
   carries.
2. A tiny, self-hostable **Party Directory** server (`hyprnime/partydirectory.py`,
   Python stdlib only, zero dependencies) is the missing "search by name"
   piece -- Syncplay alone has no room discovery, you'd otherwise need to
   already know the exact room name. Run it on anything (a Pi, a VPS, a
   home server):
   ```bash
   python3 -m hyprnime.partydirectory --port 8730
   ```
   Then, in every party member's Settings > Watch Party, set **Party
   Directory server** to `http://<that-machine>:8730`. Without this
   configured, Watch Party still works, but people need to already know the
   room name (share it directly) instead of finding it by search.

**Create a party:** Settings > Watch Party to set your display name, then
the Watch Party tab > Host a Party -- give it a name, search and pick the
anime (its AniList banner becomes the background by default, override with
your own image URL if you want), pick an episode, Sub/Dub, quality, and hit
Start. Your party becomes searchable by name for anyone using the same
Directory server.

**Join a party:** Watch Party tab > Find a Party, search the name, hit
Join. Your own `ani-cli` resolves the same episode and Syncplay locks your
playback to the host's.

Requires the `syncplay` package installed (see below).

## Offline Mode

Every episode row has a small download button next to Play. It shells out
to `ani-cli -d` in the background (no terminal, fire-and-forget) and saves
into a per-anime folder under your configured downloads directory (default
`~/Videos/Hyprnime`). The **Downloads** tab scans that folder and lets you
play any episode straight through mpv/VLC -- no `ani-cli`, no network, no
AniList lookup, fully offline.

## Themes

Settings > Appearance has a base **Light / Dark / System** switch, plus an
optional **Custom Theme** overlay:

| Family | Variants |
|---|---|
| Everforest | Dark, Light |
| Tokyo Night | Dark, Day (Light) |
| Catppuccin | Mocha, Macchiato, Frappé (dark), Latte (light) |
| Gruvbox | Dark, Light |
| Nord / Nordic | Dark, Light |
| Dracula | Dark |
| Solarized | Dark, Light |
| Rosé Pine | Main (Dark), Dawn (Light) |
| Kanagawa | Dark |

Each theme is a single generated CSS file
(`hyprnime/theming/themes/*.css`) that overrides libadwaita's named
colours, so it reskins the whole app -- headerbar, sidebar, cards, buttons.
The palettes live in `hyprnime/theming/build_themes.py`; edit a hex
value there and run `python3 build_themes.py` to regenerate.

## Install (Arch Linux)

Dependencies:

```bash
sudo pacman -S python-gobject gtk4 libadwaita mpv
# ani-cli is in the AUR:
yay -S ani-cli
# or install manually: https://github.com/pystardust/ani-cli#installation

# optional, only needed for Watch Party:
sudo pacman -S syncplay   # or: yay -S syncplay if it's not in your repos
```

Then either build the package:

```bash
makepkg -si
```

or install directly without packaging:

```bash
./install.sh
```

Either way this installs `hyprnime` to your `PATH` and a `.desktop` entry,
so it appears in your app launcher / rofi's `drun` mode.

## Launching from rofi / Hyprland

Once installed, `hyprnime.desktop` is picked up automatically by
`rofi -show drun`. For a direct keybind in your Hyprland config:

```
bind = $mainMod, A, exec, hyprnime
```

or for a plain rofi/sway/i3 setup:

```
bindsym $mod+a exec hyprnime
```

### Bonus: pure rofi flow (no GUI window at all)

`ani-cli` already ships its **own** rofi frontend for picking anime/episodes.
If you'd rather stay in rofi menus the whole time instead of opening the
graphical app, `scripts/hyprnime-rofi` (installed as `hyprnime-rofi`) adds
just the missing search-query prompt on top of that:

```
bind = $mainMod SHIFT, A, exec, hyprnime-rofi
```

## Project layout

```
hyprnime-app/
├── bin/hyprnime                # installed entry point
├── scripts/hyprnime-rofi       # optional pure-rofi companion
├── data/                       # .desktop file, icon, wordmark
├── PKGBUILD / install.sh
└── hyprnime/
    ├── main.py, window.py, config.py, partydirectory.py
    ├── views/          # home, search, detail, party, downloads, settings, widgets
    ├── backend/        # anicli.py, anilist.py, history.py, downloads.py,
    │                   # syncplay_backend.py, party_directory.py
    └── theming/        # manager.py, style.css, build_themes.py, themes/*.css
```

## Publishing this to GitHub

I can't push to GitHub on your behalf (no credentials), but the repo is
ready to go -- from this folder:

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create hyprnime --public --source=. --push
# or, without the gh CLI:
git remote add origin https://github.com/NopeVfx/hyprnime.git
git branch -M main
git push -u origin main
```

Before publishing, update the `url`/`source` fields in `PKGBUILD` and the
copyright name in `LICENSE` with your actual GitHub username/name.

## Publishing to the AUR

See `aur/README.md` for the full walkthrough. Short version: `aur/hyprnime-git/`
builds from your repo's latest commit (submit this one first, no release
tag needed); `aur/hyprnime/` builds from a tagged GitHub release (use it
once you've cut one).

## Status / what's not done yet

This is a working v1, not a finished polished product:

- No automated tests yet (the backend logic has been manually exercised
  against a live local Party Directory server + realistic sample data
  while building it, but there's no CI).
- Episode grid falls back to a guessed count (24) when AniList doesn't
  report an episode total for an ongoing series.
- Watch Party's directory "member count" is only what the host last
  reported -- the actual live headcount shows up inside Syncplay's own
  window once you're connected.
- Downloads have no progress bar -- you get a start toast and a finish
  toast, not a live percentage (ani-cli doesn't expose that cleanly).
- UI/branding is original work (not copied from any existing launcher's
  assets), styled in the same "poster grid + sidebar" spirit and named
  for the Hyprland ecosystem.

Contributions/issues welcome once it's on GitHub.
