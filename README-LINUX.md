# Triki AirMouse — port na Linux (Arch / Omarchy)

## English (short)

Linux port of [kub0vvik/TrikiAirMouse](https://github.com/kub0vvik/TrikiAirMouse).
The GUI, BLE protocol and motion engine are unchanged — only the mouse
injection is abstracted. `pyautogui` cannot control the pointer on Wayland,
so on Linux the app now creates a virtual mouse through `/dev/uinput`
(`python-evdev`), which works on both Wayland and X11. The backend is selected
automatically by platform (pyautogui on Windows, uinput on Linux).

```bash
# Arch Linux / Omarchy
sudo pacman -S --needed python-bleak python-evdev tk bluez
python triki_airmouse.py
```

Details and packaging (PKGBUILD, .desktop, udev rule) below.

---

To jest port oryginalnego [kub0vvik/TrikiAirMouse](https://github.com/kub0vvik/TrikiAirMouse)
z Windowsa na Linuksa. Zachowuje **identyczny interfejs, protokół BLE i silnik ruchu**;
zmienia się tylko sposób emulacji myszy.

## Dlaczego trzeba było coś zmienić

Oryginał używa `pyautogui`, które na Linuksie steruje kursorem przez X11 (XTest).
Na Waylandzie (Hyprland, GNOME, KDE Wayland…) **to nie działa** — serwer kompozycji
nie pozwala aplikacjom ustawiać kursora tą drogą.

Rozwiązanie zastosowane w porcie: wirtualna mysz przez **`/dev/uinput`** (`python-evdev`).
Zdarzenia wstrzykujemy na poziomie jądra, więc działa tak samo na Waylandzie i na X11.
Silnik ruchu, kliknięcia i scroll nie zmieniają się — podmieniony jest tylko backend.

Backend wybierany jest automatycznie po platformie:

| System  | Backend | Zależności |
|---------|---------|------------|
| Windows | `pyautogui` (bez zmian) | `bleak`, `pyautogui` |
| Linux   | `uinput` (evdev) | `python-bleak`, `python-evdev`, `tk` |

## Instalacja na Arch Linux / Omarchy

### 1. Zależności (wymaga sudo)

```bash
sudo pacman -S --needed python-bleak python-evdev tk bluez
```

> `tk` dostarcza `libtk`, którego potrzebuje `tkinter`. `bluez`/`bluez-utils` obsługują BLE.

### 2. Dostęp do `/dev/uinput`

Najprościej — dodaj się do grupy `input` i wyloguj/zaloguj:

```bash
sudo usermod -aG input "$USER"
```

Albo zainstaluj regułę udev (działa bez dodawania do grupy):

```bash
sudo install -Dm644 packaging/99-triki-airmouse.rules /etc/udev/rules.d/99-triki-airmouse.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=uinput
```

### 3. Uruchomienie

```bash
python triki_airmouse.py
```

albo skryptem instalującym do `~/.local`:

```bash
./install.sh
triki-airmouse
```

### 4. Pakiet (makepkg)

```bash
makepkg -si
```

Po scaleniu portu do upstreamu zmień `source=` w `PKGBUILD` na `git+https://…`
(instrukcja jest w komentarzu w pliku).

## Użycie

1. Włącz kontroler Triki.
2. W oknie kliknij **Skanuj BT** — najlepszy kandydat (Nordic UART Service) jest pierwszy.
3. Wybierz urządzenie i **Start**.
4. Trzymaj kontroler nieruchomo kilka sekund (kalibracja), potem ruszaj ręką.

Ustawienia zapisują się w `~/.config/triki-airmouse/config.json`.

## Uwagi

- Kursor na Waylandzie jest sterowany zdarzeniami `REL_X/REL_Y`; czułość może dodatkowo
  modyfikować akceleracja wskaźnika w kompozytorze (zmniejsz `Czułość X/Y` w oknie).
- Scroll to `REL_WHEEL` — jedna „klik-rolka” na jednostkę, jak w oryginale.
- Wylogowanie z sesji/zamknięcie okna usuwa wirtualne urządzenie (nie zostaje w systemie).

## Zawartość

```
triki_airmouse.py                     # port (cross-platform)
requirements.txt
PKGBUILD                              # Arch/AUR
install.sh                            # instalacja do ~/.local
packaging/triki-airmouse.desktop      # wpis do menu
packaging/99-triki-airmouse.rules     # reguła /dev/uinput
upstream/triki_airmouse_windows.py    # oryginał (referencja)
```
