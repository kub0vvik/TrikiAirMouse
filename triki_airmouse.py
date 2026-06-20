import asyncio
import csv
import json
import math
import struct
import threading
import time
from collections import deque
from io import BytesIO
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from bleak import BleakScanner, BleakClient
import pyautogui

NUS_WRITE  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_NOTIFY = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

CMD_START = bytes([0x20, 0x10, 0x00, 0xD0, 0x07, 0x68, 0x00, 0x01])
CMD_STOP  = bytes([0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

CONFIG_FILE = Path("triki_airmouse_config.json")

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

AXES = ["A", "B", "C", "D", "E", "F"]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class MotionEngine:
    def __init__(self, app):
        self.app = app
        self.bias = {a: 0.0 for a in AXES}
        self.filtered = {a: 0.0 for a in AXES}
        self.calibrating = False
        self.calib_samples = []
        self.last_button = False
        self.button_down_at = None
        self.freeze_until = 0.0
        self.scroll_accum = 0.0
        self.scroll_mode_until = 0.0
        self.last_click_at = 0.0

    def start_calibration(self):
        self.calibrating = True
        self.calib_samples = []
        self.app.set_status("Kalibracja: trzymaj Triki nieruchomo")

    def process_calibration(self, axes):
        if not self.calibrating:
            return
        self.calib_samples.append(axes.copy())
        target = int(self.app.calib_frames.get())
        if len(self.calib_samples) >= target:
            for a in AXES:
                self.bias[a] = sum(s[a] for s in self.calib_samples) / len(self.calib_samples)
                self.filtered[a] = 0.0
            self.calibrating = False
            self.app.set_status("Kalibracja gotowa")

    def corrected_filtered(self, axes):
        alpha = float(self.app.filter_alpha.get())
        out = {}
        for a in AXES:
            raw = axes[a] - self.bias[a]
            self.filtered[a] = self.filtered[a] * alpha + raw * (1.0 - alpha)
            v = self.filtered[a]
            dz = float(self.app.deadzone.get())
            if abs(v) < dz:
                v = 0.0
            out[a] = v
        return out

    def handle_button(self, pressed, now):
        # Button does not move cursor: while held, cursor is frozen.
        if pressed and not self.last_button:
            self.button_down_at = now
            self.freeze_until = now + 10.0

        if not pressed and self.last_button:
            duration = now - (self.button_down_at or now)
            self.freeze_until = now + float(self.app.click_freeze_ms.get()) / 1000.0
            self.button_down_at = None

            if self.app.click_mode.get() == "short_left_long_right":
                if duration >= float(self.app.right_click_hold.get()):
                    pyautogui.click(button="right")
                    self.app.flash_event("RIGHT CLICK")
                else:
                    pyautogui.click(button="left")
                    self.app.flash_event("LEFT CLICK")
            elif self.app.click_mode.get() == "button_left_down":
                # Classic hold-to-drag, but still freezes by default while pressing.
                pass

        if self.app.click_mode.get() == "button_left_down":
            if pressed != self.last_button:
                if pressed:
                    pyautogui.mouseDown(button="left")
                    self.app.flash_event("LEFT DOWN")
                else:
                    pyautogui.mouseUp(button="left")
                    self.app.flash_event("LEFT UP")

        self.last_button = pressed

    def maybe_scroll(self, vals, now):
        if not self.app.scroll_enabled.get():
            return False

        axis = self.app.scroll_axis.get()
        v = vals.get(axis, 0.0)
        threshold = float(self.app.scroll_threshold.get())

        # Hysteresis: once scroll starts, keep it briefly active.
        if abs(v) >= threshold:
            self.scroll_mode_until = now + 0.25

        active = now < self.scroll_mode_until
        if not active:
            self.scroll_accum *= 0.75
            return False

        self.freeze_until = now + 0.20
        speed = float(self.app.scroll_sens.get())
        if self.app.invert_scroll.get():
            speed = -speed

        self.scroll_accum += (v / threshold) * speed
        steps = int(self.scroll_accum)
        if steps:
            pyautogui.scroll(steps)
            self.scroll_accum -= steps
            self.app.flash_event(f"SCROLL {steps}")

        return True

    def move_mouse(self, vals, now):
        if not self.app.mouse_enabled.get():
            return
        if now < self.freeze_until:
            return

        x_axis = self.app.axis_x.get()
        y_axis = self.app.axis_y.get()
        mx = vals.get(x_axis, 0.0) * float(self.app.sens_x.get())
        my = vals.get(y_axis, 0.0) * float(self.app.sens_y.get())

        if self.app.invert_x.get():
            mx = -mx
        if self.app.invert_y.get():
            my = -my

        max_step = int(self.app.max_step.get())
        mx = int(clamp(mx, -max_step, max_step))
        my = int(clamp(my, -max_step, max_step))

        if mx or my:
            pyautogui.moveRel(mx, my, duration=0)

    def process(self, button, axes):
        now = time.time()
        self.process_calibration(axes)
        vals = self.corrected_filtered(axes)
        self.handle_button(button, now)
        is_scrolling = self.maybe_scroll(vals, now)
        if not is_scrolling:
            self.move_mouse(vals, now)
        return vals


class TrikiClient:
    def __init__(self, app):
        self.app = app
        self.client = None
        self.running = False
        self.stash = bytes()
        self.frame_no = 0
        self.engine = MotionEngine(app)

    @staticmethod
    def parse_axes(body):
        # 12 bytes = 6 signed little-endian int16 values.
        a, b, c, d, e, f = struct.unpack("<hhhhhh", body)
        return {"A": a, "B": b, "C": c, "D": d, "E": e, "F": f}

    def handler(self, sender, data: bytearray):
        bio = BytesIO(self.stash + data)
        self.stash = bytes()

        while True:
            buf = bio.read(2)
            if not buf or len(buf) != 2:
                self.stash = buf
                break

            h, button_raw = struct.unpack("<BB", buf)

            if h == 0x21:
                bio.read(2)
                break

            if h == 0x22:
                body = bio.read(12)
                if not body or len(body) != 12:
                    self.stash = buf + body
                    break

                raw = buf + body
                axes = self.parse_axes(body)
                button = button_raw == 1
                self.frame_no += 1
                vals = self.engine.process(button, axes)
                self.app.debug_event(self.frame_no, button, raw, axes, vals, self.engine.bias)

    async def connect_loop(self, address):
        try:
            async with BleakClient(address) as client:
                self.client = client
                self.running = True
                self.app.set_status("Połączono")
                self.engine.start_calibration()
                await client.start_notify(NUS_NOTIFY, self.handler)
                await client.write_gatt_char(NUS_WRITE, CMD_START, response=True)
                while self.running:
                    await asyncio.sleep(0.1)
                await client.write_gatt_char(NUS_WRITE, CMD_STOP, response=True)
                await client.stop_notify(NUS_NOTIFY)
        except Exception as ex:
            self.app.set_status(f"Błąd: {ex}")
        finally:
            self.running = False
            self.client = None
            self.app.set_buttons_connected(False)

    def start(self, address):
        threading.Thread(target=lambda: asyncio.run(self.connect_loop(address)), daemon=True).start()

    def stop(self):
        self.running = False


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Triki AirMouse Pro")
        self.root.geometry("1080x760")
        self.devices = {}
        self.triki = TrikiClient(self)
        self.debug_rows = deque(maxlen=8000)
        self.csv_file = None
        self.csv_writer = None
        self.event_text = tk.StringVar(value="")

        self.mouse_enabled = tk.BooleanVar(value=True)
        self.axis_x = tk.StringVar(value="C")
        self.axis_y = tk.StringVar(value="B")
        self.invert_x = tk.BooleanVar(value=False)
        self.invert_y = tk.BooleanVar(value=True)
        self.sens_x = tk.DoubleVar(value=0.035)
        self.sens_y = tk.DoubleVar(value=0.035)
        self.deadzone = tk.DoubleVar(value=35.0)
        self.filter_alpha = tk.DoubleVar(value=0.70)
        self.max_step = tk.IntVar(value=35)
        self.calib_frames = tk.IntVar(value=120)

        self.click_mode = tk.StringVar(value="short_left_long_right")
        self.right_click_hold = tk.DoubleVar(value=0.45)
        self.click_freeze_ms = tk.IntVar(value=180)

        self.scroll_enabled = tk.BooleanVar(value=True)
        self.scroll_axis = tk.StringVar(value="C")
        self.scroll_threshold = tk.DoubleVar(value=2200.0)
        self.scroll_sens = tk.DoubleVar(value=0.22)
        self.invert_scroll = tk.BooleanVar(value=False)

        self.status = tk.StringVar(value="Niepołączono")
        self.build_ui()
        self.load_config()

    def build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=8)
        ttk.Label(top, text="Triki AirMouse Pro", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, textvariable=self.event_text, font=("Segoe UI", 12, "bold")).pack(side="left", padx=30)
        ttk.Label(top, textvariable=self.status).pack(side="right")

        bt = ttk.LabelFrame(self.root, text="Bluetooth")
        bt.pack(fill="x", padx=10, pady=5)
        self.device_box = ttk.Combobox(bt, state="readonly")
        self.device_box.pack(fill="x", padx=8, pady=5)
        row = ttk.Frame(bt)
        row.pack(fill="x", padx=8, pady=5)
        self.scan_btn = ttk.Button(row, text="Skanuj BT", command=self.scan_bt)
        self.scan_btn.pack(side="left", fill="x", expand=True, padx=3)
        self.start_btn = ttk.Button(row, text="Start", command=self.start_mouse)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=3)
        self.stop_btn = ttk.Button(row, text="Stop", command=self.stop_mouse, state="disabled")
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=3)
        ttk.Button(row, text="Kalibruj teraz", command=self.recalibrate).pack(side="left", fill="x", expand=True, padx=3)
        ttk.Button(row, text="Zapisz ustawienia", command=self.save_config).pack(side="left", fill="x", expand=True, padx=3)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        main = ttk.Frame(notebook)
        debug = ttk.Frame(notebook)
        notebook.add(main, text="Sterowanie")
        notebook.add(debug, text="Debugger")

        cfg = ttk.LabelFrame(main, text="Mysz")
        cfg.pack(fill="x", padx=8, pady=8)
        ttk.Checkbutton(cfg, text="Włącz ruch myszy", variable=self.mouse_enabled).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(cfg, text="X").grid(row=1, column=0, sticky="w", padx=8)
        ttk.Combobox(cfg, textvariable=self.axis_x, values=AXES, state="readonly", width=8).grid(row=1, column=1, sticky="w")
        ttk.Label(cfg, text="Y").grid(row=1, column=2, sticky="w", padx=8)
        ttk.Combobox(cfg, textvariable=self.axis_y, values=AXES, state="readonly", width=8).grid(row=1, column=3, sticky="w")
        ttk.Checkbutton(cfg, text="Odwróć X", variable=self.invert_x).grid(row=2, column=0, sticky="w", padx=8)
        ttk.Checkbutton(cfg, text="Odwróć Y", variable=self.invert_y).grid(row=2, column=1, sticky="w", padx=8)
        self.add_slider(cfg, "Czułość X", self.sens_x, 0.001, 0.20, 3)
        self.add_slider(cfg, "Czułość Y", self.sens_y, 0.001, 0.20, 4)
        self.add_slider(cfg, "Deadzone", self.deadzone, 0, 400, 5)
        self.add_slider(cfg, "Filtr drgań / wygładzanie", self.filter_alpha, 0, 0.95, 6)
        self.add_slider(cfg, "Maks. skok kursora", self.max_step, 3, 120, 7)
        self.add_slider(cfg, "Klatek kalibracji", self.calib_frames, 30, 400, 8)
        cfg.columnconfigure(4, weight=1)

        click = ttk.LabelFrame(main, text="Klik bez przesuwania kursora")
        click.pack(fill="x", padx=8, pady=8)
        ttk.Label(click, text="Tryb").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Combobox(click, textvariable=self.click_mode, state="readonly", values=["short_left_long_right", "button_left_down"], width=24).grid(row=0, column=1, sticky="w")
        self.add_slider(click, "Przytrzymanie = prawy klik [s]", self.right_click_hold, 0.2, 1.5, 1)
        self.add_slider(click, "Zamrożenie po kliku [ms]", self.click_freeze_ms, 0, 800, 2)
        ttk.Label(click, text="Domyślnie: krótki przycisk = lewy klik, długie przytrzymanie = prawy klik. Kursor stoi w miejscu podczas kliku.").grid(row=3, column=0, columnspan=5, sticky="w", padx=8, pady=4)
        click.columnconfigure(4, weight=1)

        scroll = ttk.LabelFrame(main, text="Scroll bez przesuwania kursora")
        scroll.pack(fill="x", padx=8, pady=8)
        ttk.Checkbutton(scroll, text="Włącz scroll gestem", variable=self.scroll_enabled).grid(row=0, column=0, sticky="w", padx=8)
        ttk.Label(scroll, text="Oś scrolla").grid(row=0, column=1, sticky="e", padx=8)
        ttk.Combobox(scroll, textvariable=self.scroll_axis, values=AXES, state="readonly", width=8).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(scroll, text="Odwróć scroll", variable=self.invert_scroll).grid(row=0, column=3, sticky="w", padx=8)
        self.add_slider(scroll, "Próg wejścia w scroll", self.scroll_threshold, 200, 9000, 1)
        self.add_slider(scroll, "Czułość scrolla", self.scroll_sens, 0.02, 1.5, 2)
        ttk.Label(scroll, text="Scroll startuje dopiero przy mocnym obrocie nadgarstka, wtedy ruch kursora jest chwilowo blokowany.").grid(row=3, column=0, columnspan=5, sticky="w", padx=8, pady=4)
        scroll.columnconfigure(4, weight=1)

        self.build_debug(debug)

    def add_slider(self, parent, label, var, minv, maxv, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Scale(parent, from_=minv, to=maxv, variable=var).grid(row=row, column=1, columnspan=3, sticky="ew", padx=8)
        val = ttk.Label(parent, width=8)
        val.grid(row=row, column=4, sticky="w", padx=8)
        def refresh(*_):
            try:
                v = var.get()
                if isinstance(v, float):
                    val.config(text=f"{v:.3g}")
                else:
                    val.config(text=str(v))
            except Exception:
                pass
        var.trace_add("write", refresh)
        refresh()

    def build_debug(self, parent):
        controls = ttk.Frame(parent)
        controls.pack(fill="x", padx=8, pady=5)
        ttk.Button(controls, text="Wyczyść", command=self.clear_debug).pack(side="left", padx=3)
        ttk.Button(controls, text="Zapisz CSV", command=self.save_csv).pack(side="left", padx=3)
        ttk.Button(controls, text="Start live CSV", command=self.start_csv_live).pack(side="left", padx=3)
        ttk.Button(controls, text="Stop live CSV", command=self.stop_csv_live).pack(side="left", padx=3)
        ttk.Button(controls, text="Kopiuj próbkę", command=self.copy_sample).pack(side="left", padx=3)
        cols = ["frame", "button", "raw", "A", "B", "C", "D", "E", "F", "Ac", "Bc", "Cc", "Dc", "Ec", "Fc"]
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", height=22)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=65, stretch=False)
        self.tree.column("raw", width=310, stretch=True)
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=5)
        yscroll.pack(side="right", fill="y", pady=5)

    def set_status(self, text):
        self.root.after(0, lambda: self.status.set(text))

    def flash_event(self, text):
        def show():
            self.event_text.set(text)
            self.root.after(650, lambda: self.event_text.set(""))
        self.root.after(0, show)

    def set_buttons_connected(self, connected):
        def apply():
            self.start_btn.config(state="disabled" if connected else "normal")
            self.stop_btn.config(state="normal" if connected else "disabled")
            self.scan_btn.config(state="disabled" if connected else "normal")
        self.root.after(0, apply)

    def debug_event(self, frame, button, raw, axes, vals, bias):
        row = {"frame": frame, "time": time.time(), "button": int(button), "raw": raw.hex(" ")}
        for a in AXES:
            row[a] = axes[a]
            row[a + "c"] = round(vals[a], 2)
            row[a + "bias"] = round(bias[a], 2)
        self.debug_rows.append(row)
        if self.csv_writer:
            self.csv_writer.writerow(row)
            self.csv_file.flush()

        if frame % 2 != 0:
            return

        def insert():
            values = [row["frame"], row["button"], row["raw"], row["A"], row["B"], row["C"], row["D"], row["E"], row["F"], row["Ac"], row["Bc"], row["Cc"], row["Dc"], row["Ec"], row["Fc"]]
            self.tree.insert("", "end", values=values)
            children = self.tree.get_children()
            if len(children) > 700:
                self.tree.delete(children[0])
            self.tree.yview_moveto(1)
        self.root.after(0, insert)

    def clear_debug(self):
        self.debug_rows.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def save_csv(self):
        if not self.debug_rows:
            messagebox.showinfo("Brak danych", "Brak ramek do zapisania.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="triki_pro_debug.csv")
        if not path:
            return
        keys = list(self.debug_rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(self.debug_rows)
        messagebox.showinfo("Zapisano", path)

    def start_csv_live(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="triki_live_debug.csv")
        if not path:
            return
        keys = ["frame", "time", "button", "raw"] + AXES + [a + "c" for a in AXES] + [a + "bias" for a in AXES]
        self.csv_file = open(path, "w", newline="", encoding="utf-8")
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=keys)
        self.csv_writer.writeheader()
        self.set_status("Live CSV włączony")

    def stop_csv_live(self):
        if self.csv_file:
            self.csv_file.close()
        self.csv_file = None
        self.csv_writer = None
        self.set_status("Live CSV wyłączony")

    def copy_sample(self):
        rows = list(self.debug_rows)[-120:]
        if not rows:
            messagebox.showinfo("Brak danych", "Brak ramek.")
            return
        keys = ["frame", "button", "A", "B", "C", "D", "E", "F", "Ac", "Bc", "Cc", "Dc", "Ec", "Fc"]
        lines = [",".join(keys)]
        for r in rows:
            lines.append(",".join(str(r.get(k, "")) for k in keys))
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.set_status("Skopiowano próbkę")

    def scan_bt(self):
        self.set_status("Skanuję Bluetooth...")
        self.scan_btn.config(state="disabled")
        threading.Thread(target=lambda: asyncio.run(self.scan_bt_async()), daemon=True).start()

    async def scan_bt_async(self):
        try:
            # Bleak w nowszych wersjach nie ma już d.metadata.
            # return_adv=True daje parę: BLEDevice + AdvertisementData z service_uuids.
            try:
                found_raw = await BleakScanner.discover(timeout=6.0, return_adv=True)
                found = [(device, adv) for device, adv in found_raw.values()]
            except TypeError:
                # Fallback dla starszego Bleak.
                devices = await BleakScanner.discover(timeout=6.0)
                found = [(device, None) for device in devices]

            self.devices.clear()
            names = []

            for d, adv in found:
                name = None
                if adv is not None:
                    name = getattr(adv, "local_name", None)
                name = name or getattr(d, "name", None) or "Unknown"

                uuids_list = []
                if adv is not None:
                    uuids_list = getattr(adv, "service_uuids", None) or []
                else:
                    meta = getattr(d, "metadata", {}) or {}
                    uuids_list = meta.get("uuids", [])

                uuids = " ".join(uuids_list).lower()
                score = 0
                low = name.lower()

                if "triki" in low or "controller" in low or "game" in low or "pad" in low:
                    score += 10

                if "6e400001" in uuids or "6e400002" in uuids or "6e400003" in uuids:
                    score += 20

                label = f"{name} — {d.address}"
                self.devices[label] = d.address
                names.append((score, label))

            names.sort(reverse=True, key=lambda x: x[0])
            labels = [x[1] for x in names]

            def update():
                self.device_box["values"] = labels
                if labels:
                    self.device_box.current(0)
                    self.status.set("Wybierz urządzenie / najlepszy kandydat jest pierwszy")
                else:
                    self.status.set("Nie znaleziono urządzeń BLE")
                self.scan_btn.config(state="normal")

            self.root.after(0, update)

        except Exception as ex:
            self.root.after(0, lambda: messagebox.showerror("Błąd skanowania", str(ex)))
            self.root.after(0, lambda: self.scan_btn.config(state="normal"))

    def start_mouse(self):
        selected = self.device_box.get()
        if not selected:
            messagebox.showwarning("Brak urządzenia", "Najpierw zeskanuj i wybierz kontroler.")
            return
        self.set_buttons_connected(True)
        self.set_status("Łączenie...")
        self.triki.start(self.devices[selected])

    def stop_mouse(self):
        self.set_status("Rozłączanie...")
        self.triki.stop()

    def recalibrate(self):
        self.triki.engine.start_calibration()

    def save_config(self):
        data = {}
        for name in [
            "mouse_enabled", "axis_x", "axis_y", "invert_x", "invert_y", "sens_x", "sens_y", "deadzone", "filter_alpha", "max_step", "calib_frames",
            "click_mode", "right_click_hold", "click_freeze_ms", "scroll_enabled", "scroll_axis", "scroll_threshold", "scroll_sens", "invert_scroll"
        ]:
            data[name] = getattr(self, name).get()
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.set_status("Ustawienia zapisane")

    def load_config(self):
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in data.items():
                if hasattr(self, k):
                    getattr(self, k).set(v)
            self.set_status("Wczytano ustawienia")
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
