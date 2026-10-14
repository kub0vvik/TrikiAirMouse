# Maintainer: naprawiamwsrodku <naprawiamwsrodku@users.noreply.github.com>
# Linux port of https://github.com/kub0vvik/TrikiAirMouse
pkgname=triki-airmouse
pkgver=1.0.0
pkgrel=1
pkgdesc="Air mouse for the Triki (Żabka) motion controller over Bluetooth LE (Linux port)"
arch=('any')
url="https://github.com/kub0vvik/TrikiAirMouse"
license=('unknown')
depends=('python' 'python-bleak' 'python-evdev' 'tk' 'bluez')
optdepends=(
  'bluez-utils: bluetoothctl for pairing/debugging'
  'python-pyautogui: only needed on Windows'
)
source=(
  'triki_airmouse.py'
  'triki-airmouse.desktop'
  '99-triki-airmouse.rules'
)
sha256sums=(
  'SKIP'
  'SKIP'
  'SKIP'
)

# When this port is merged upstream, replace the local sources with:
#   source=("$pkgname::git+https://github.com/kub0vvik/TrikiAirMouse.git")
#   sha256sums=('SKIP')

package() {
  install -Dm755 "$srcdir/triki_airmouse.py" \
    "$pkgdir/usr/bin/triki-airmouse"
  install -Dm644 "$srcdir/triki-airmouse.desktop" \
    "$pkgdir/usr/share/applications/triki-airmouse.desktop"
  install -Dm644 "$srcdir/99-triki-airmouse.rules" \
    "$pkgdir/usr/lib/udev/rules.d/99-triki-airmouse.rules"
}
