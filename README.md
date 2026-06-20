# Triki AirMouse

🇬🇧 **English**

Turn the **Triki motion controller** (Żabka gadget) into a fully configurable wireless **Air Mouse for Windows**.

The application connects to the controller over Bluetooth Low Energy (BLE), reads motion sensor data in real time, and converts hand movements into mouse movement, scrolling, and click actions.

---

## Features

### Motion Control

* Air Mouse based on Triki motion sensors
* Adjustable sensitivity
* Adjustable deadzone
* Axis remapping
* Axis inversion
* Motion smoothing filter
* Automatic drift compensation

### Auto Calibration

* Automatic sensor calibration on startup
* Manual recalibration
* Sensor offset compensation
* Drift reduction

### Smart Clicks

* Left click
* Right click (long press)
* Click mode prevents unwanted cursor movement
* Button debouncing

### Gesture Scrolling

* Motion-based scrolling
* Cursor lock while scrolling
* Adjustable scroll sensitivity
* Smooth wheel emulation

### Bluetooth

* Automatic BLE device scanning
* Triki auto-detection
* Manual device selection
* Reconnect support

### Debugger

* Real-time sensor monitoring
* Raw packet viewer
* Frame analysis
* CSV export
* Motion profiling

---

## Requirements

* Windows 10 / Windows 11
* Python 3.10+

### Dependencies

```bash
pip install bleak pyautogui
```

---

## Installation

```bash
git clone https://github.com/USERNAME/triki-airmouse.git
cd triki-airmouse
pip install -r requirements.txt
```

Run:

```bash
python triki_airmouse_pro.py
```

---

## First Setup

1. Enable Bluetooth on Windows.
2. Launch the application.
3. Click **Scan Bluetooth**.
4. Select your Triki controller.
5. Click **Connect**.
6. Keep the controller still for a few seconds during calibration.

After calibration the cursor should start responding to movement.

---

## Controls

### Cursor

Move the controller in the air.

### Left Click

Short button press.

### Right Click

Long button press.

### Scroll

Rotate the controller using the configured gesture axis.

During scrolling the cursor is automatically locked to prevent accidental movement.

---

## Debug Mode

The debugger allows you to inspect:

* Raw BLE packets
* Parsed sensor values
* Motion data
* Button states
* Axis activity

Logs can be exported to CSV for reverse engineering and protocol analysis.

---

## Reverse Engineering Notes

The controller communicates through Nordic UART Service (NUS):

```text
WRITE:
6e400002-b5a3-f393-e0a9-e50e24dcca9e

NOTIFY:
6e400003-b5a3-f393-e0a9-e50e24dcca9e
```

This project reverse-engineers motion packets and translates them into mouse actions.

---

## Roadmap

* Gesture customization
* Multiple button mappings
* Gaming mode
* Presentation mode
* Media control gestures
* User profiles
* Automatic firmware detection
* Native HID emulation

---

## Disclaimer

This project is an unofficial reverse-engineering effort and is not affiliated with Żabka or the original Triki manufacturer.

Use at your own risk.

---

# Triki AirMouse

🇵🇱 **Polski**

Zmień kontroler ruchowy **Triki** (gadżet z Żabki) w w pełni konfigurowalną bezprzewodową **Air Mouse dla systemu Windows**.

Aplikacja łączy się z kontrolerem przez Bluetooth Low Energy (BLE), odczytuje dane z czujników ruchu w czasie rzeczywistym i zamienia ruch dłoni na ruch kursora, przewijanie oraz kliknięcia myszy.

---

## Funkcje

### Sterowanie Ruchem

* Air Mouse oparta na czujnikach Triki
* Regulowana czułość
* Regulowana martwa strefa (deadzone)
* Dowolne mapowanie osi
* Odwracanie osi
* Filtr wygładzający ruch
* Automatyczna kompensacja dryfu

### Automatyczna Kalibracja

* Kalibracja przy uruchomieniu
* Ręczna rekalkibracja
* Kompensacja przesunięcia czujników
* Redukcja dryfu

### Inteligentne Kliknięcia

* Lewy przycisk myszy
* Prawy przycisk myszy (długie przytrzymanie)
* Blokada ruchu kursora podczas klikania
* Eliminacja przypadkowych kliknięć

### Przewijanie Gestami

* Przewijanie ruchem kontrolera
* Blokada kursora podczas scrollowania
* Regulowana czułość przewijania
* Płynna emulacja kółka myszy

### Bluetooth

* Automatyczne skanowanie BLE
* Automatyczne wykrywanie Triki
* Ręczny wybór urządzenia
* Obsługa ponownego połączenia

### Debugger

* Monitorowanie czujników w czasie rzeczywistym
* Podgląd surowych pakietów
* Analiza ramek danych
* Eksport CSV
* Profilowanie ruchu

---

## Wymagania

* Windows 10 / Windows 11
* Python 3.10+

### Biblioteki

```bash
pip install bleak pyautogui
```

---

## Instalacja

```bash
git clone https://github.com/USERNAME/triki-airmouse.git
cd triki-airmouse
pip install -r requirements.txt
```

Uruchomienie:

```bash
python triki_airmouse_pro.py
```

---

## Pierwsze Uruchomienie

1. Włącz Bluetooth w systemie Windows.
2. Uruchom aplikację.
3. Kliknij **Skanuj Bluetooth**.
4. Wybierz kontroler Triki.
5. Kliknij **Połącz**.
6. Pozostaw urządzenie nieruchomo przez kilka sekund podczas kalibracji.

Po zakończeniu kalibracji kursor powinien zacząć reagować na ruch.

---

## Sterowanie

### Kursor

Poruszaj kontrolerem w powietrzu.

### Lewy Klik

Krótkie naciśnięcie przycisku.

### Prawy Klik

Długie przytrzymanie przycisku.

### Scroll

Obracaj kontroler zgodnie z wybraną osią gestu.

Podczas przewijania ruch kursora jest automatycznie blokowany.

---

## Tryb Debugowania

Debugger umożliwia podgląd:

* Surowych pakietów BLE
* Odczytanych wartości czujników
* Danych ruchu
* Stanów przycisku
* Aktywności poszczególnych osi

Logi można eksportować do plików CSV w celu dalszej analizy protokołu.

---

## Informacje Techniczne

Kontroler komunikuje się przez Nordic UART Service (NUS):

```text
WRITE:
6e400002-b5a3-f393-e0a9-e50e24dcca9e

NOTIFY:
6e400003-b5a3-f393-e0a9-e50e24dcca9e
```

Projekt wykorzystuje reverse engineering protokołu ruchu i tłumaczy dane z czujników na akcje myszy.

---

## Plan Rozwoju

* Konfigurowalne gesty
* Obsługa wielu przycisków
* Tryb gamingowy
* Tryb prezentacji
* Sterowanie multimediami
* Profile użytkownika
* Automatyczne wykrywanie firmware
* Natywna emulacja HID

---

## Zastrzeżenie

Projekt jest nieoficjalnym projektem reverse engineering i nie jest powiązany z Żabką ani producentem urządzenia Triki.

Używasz go na własną odpowiedzialność.
