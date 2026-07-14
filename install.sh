#!/usr/bin/env bash
# Manual installer, for when you don't want to go through makepkg.
# Usage: ./install.sh            (installs for current user, ~/.local)
#        sudo ./install.sh       (installs system-wide, /usr/local)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -eq 0 ]; then
    PREFIX=/usr/local
    APP_DIR=/usr/local/lib/hyprnime
    DESKTOP_DIR=/usr/local/share/applications
    ICON_DIR=/usr/local/share/icons/hicolor/scalable/apps
else
    PREFIX="$HOME/.local"
    APP_DIR="$HOME/.local/lib/hyprnime"
    DESKTOP_DIR="$HOME/.local/share/applications"
    ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
fi

echo "==> Checking dependencies"
missing=()
for dep in ani-cli mpv python3; do
    command -v "$dep" >/dev/null 2>&1 || missing+=("$dep")
done
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null \
    || missing+=("python-gobject/gtk4/libadwaita")

if [ "${#missing[@]}" -ne 0 ]; then
    echo "Missing dependencies: ${missing[*]}"
    echo "On Arch: sudo pacman -S python-gobject gtk4 libadwaita ani-cli mpv"
    echo "(ani-cli is in the AUR: yay -S ani-cli, or install manually from"
    echo " https://github.com/pystardust/ani-cli)"
    exit 1
fi

if ! command -v syncplay >/dev/null 2>&1; then
    echo "Note: 'syncplay' isn't on PATH -- Watch Party won't work until you"
    echo "      install it (sudo pacman -S syncplay, or yay -S syncplay)."
fi

echo "==> Installing to $PREFIX"
mkdir -p "$APP_DIR" "$PREFIX/bin" "$DESKTOP_DIR" "$ICON_DIR"

cp -r "$SCRIPT_DIR/hyprnime" "$APP_DIR/"
install -m755 "$SCRIPT_DIR/bin/hyprnime" "$PREFIX/bin/hyprnime"
install -m755 "$SCRIPT_DIR/scripts/hyprnime-rofi" "$PREFIX/bin/hyprnime-rofi"
install -m644 "$SCRIPT_DIR/data/hyprnime.desktop" "$DESKTOP_DIR/hyprnime.desktop"
install -m644 "$SCRIPT_DIR/data/hyprnime.svg" "$ICON_DIR/hyprnime.svg"

# Small wrapper so `hyprnime-party-directory` is on PATH too, for anyone
# self-hosting the Watch Party discovery server.
PARTY_BIN="$PREFIX/bin/hyprnime-party-directory"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    "export PYTHONPATH=\"$APP_DIR:\${PYTHONPATH:-}\"" \
    'exec python3 -m hyprnime.partydirectory "$@"' \
    > "$PARTY_BIN"
chmod 755 "$PARTY_BIN"

# Point the installed launcher script at the copied package.
sed -i "s#/usr/lib/hyprnime#$APP_DIR#" "$PREFIX/bin/hyprnime"

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache 2>/dev/null || true

echo "==> Done. Launch it with 'hyprnime', your app menu, or rofi -show drun"
