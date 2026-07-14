# Maintainer: NopeVfx <skidxql@gmail.com>
pkgname=hyprnime
pkgver=0.1.0
pkgrel=1
pkgdesc="Graphical anime launcher (GTK4/libadwaita) backed by ani-cli, built for Hyprland, launchable from rofi"
arch=('any')
url="https://github.com/NopeVfx/hyprnime"
license=('MIT')
depends=('python' 'python-gobject' 'gtk4' 'libadwaita' 'ani-cli' 'mpv')
optdepends=('vlc: alternative player'
            'rofi: for the optional hyprnime-rofi companion script'
            'ani-skip: for intro skipping'
            'syncplay: for the Watch Party feature')
source=("$pkgname-$pkgver.tar.gz::https://github.com/NopeVfx/hyprnime/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
  cd "$srcdir/$pkgname-$pkgver"

  install -Dm755 bin/hyprnime "$pkgdir/usr/bin/hyprnime"
  install -Dm755 scripts/hyprnime-rofi "$pkgdir/usr/bin/hyprnime-rofi"
  install -Dm755 hyprnime/partydirectory.py "$pkgdir/usr/bin/hyprnime-party-directory"

  install -d "$pkgdir/usr/lib/hyprnime"
  cp -r hyprnime "$pkgdir/usr/lib/hyprnime/"

  install -Dm644 data/hyprnime.desktop "$pkgdir/usr/share/applications/hyprnime.desktop"
  install -Dm644 data/hyprnime.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/hyprnime.svg"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
