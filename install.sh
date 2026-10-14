#!/usr/bin/env bash
# Per-user (no root) install of Triki AirMouse on Arch/Omarchy and friends.
# Installs to ~/.local and, if needed, a udev rule via sudo for /dev/uinput.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
prefix="${PREFIX:-$HOME/.local}"
bindir="$prefix/bin"
appdir="$prefix/share/applications"

echo "==> Instalowanie zależności (wymaga sudo):"
echo "    sudo pacman -S --needed python-bleak python-evdev tk bluez"
if command -v pacman >/dev/null; then
  sudo pacman -S --needed --noconfirm python-bleak python-evdev tk bluez || true
fi

echo "==> Kopiowanie plików do $prefix"
install -d "$bindir" "$appdir"
install -Dm755 "$here/triki_airmouse.py" "$bindir/triki-airmouse"
install -Dm644 "$here/packaging/triki-airmouse.desktop" "$appdir/triki-airmouse.desktop"
sed -i "s#^Exec=.*#Exec=$bindir/triki-airmouse#" "$appdir/triki-airmouse.desktop"

if [[ ! -r /dev/uinput || ! -w /dev/uinput ]]; then
  echo "==> Brak dostępu do /dev/uinput - instaluję regułę udev (sudo)"
  sudo install -Dm644 "$here/packaging/99-triki-airmouse.rules" \
    /etc/udev/rules.d/99-triki-airmouse.rules
  sudo udevadm control --reload-rules
  sudo udevadm trigger --name-match=uinput || true
fi

echo
echo "Gotowe. Uruchom:  triki-airmouse   (lub z menu: 'Triki AirMouse')"
echo "Upewnij się, że $bindir jest w \$PATH."
