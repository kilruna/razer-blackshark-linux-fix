#!/usr/bin/env python3

import os
import pwd
import re
import shutil
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

APP_ID = "com.github.kilruna.razer-blackshark-linux-fix"
HELPER_PATHS = (
    "/usr/local/libexec/razer-blackshark-fix",
    "/usr/local/sbin/razer-blackshark-fix",
)
VENDOR = "1532"
PRODUCT = "0555"
STEP_RE = re.compile(r"^@@STEP (\d+)/(\d+): (.*)$")

STEPS_DE = {
    1: "PipeWire und WirePlumber stoppen",
    2: "Dongle jetzt abziehen",
    3: "snd_usb_audio entladen",
    4: "Dongle wieder einstecken (1532:0555)",
    5: "Lautstärke-Rocker am Headset drücken",
    6: "snd_usb_audio laden und Interfaces prüfen",
    7: "PipeWire und WirePlumber neu starten",
}


def dongle_present():
    base = "/sys/bus/usb/devices"
    try:
        entries = os.listdir(base)
    except OSError:
        return False
    for entry in entries:
        try:
            with open(f"{base}/{entry}/idVendor") as handle:
                vendor = handle.read().strip()
            with open(f"{base}/{entry}/idProduct") as handle:
                product = handle.read().strip()
        except OSError:
            continue
        if vendor == VENDOR and product == PRODUCT:
            return True
    return False


def host_app_dir():
    try:
        with open("/proc/self/mountinfo") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) < 7 or parts[4] != "/app":
                    continue
                try:
                    sep = parts.index("-")
                except ValueError:
                    continue
                root = parts[3]
                source = parts[sep + 2]
                if root == "/":
                    return source
                return source.rstrip("/") + root
    except OSError:
        pass
    return None


class FixWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Razer BlackShark Linux Fix")
        self.set_default_size(680, 560)
        self.helper_path = None
        self.running = False

        self.username = pwd.getpwuid(os.getuid()).pw_name

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        self.set_content(toolbar_view)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        toolbar_view.set_content(box)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.append(Gtk.Image.new_from_icon_name(APP_ID))
        self.status_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True)
        status_box.append(self.status_label)
        box.append(status_box)

        self.step_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True)
        self.step_label.add_css_class("heading")
        self.step_label.set_text("Bereit. Dongle anschließen und „Fix starten“ klicken.")
        box.append(self.step_label)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_text("0/7")
        box.append(self.progress)

        scrolled = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled.set_min_content_height(220)
        self.log_view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
        )
        self.log_buffer = self.log_view.get_buffer()
        scrolled.set_child(self.log_view)
        box.append(scrolled)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        self.setup_button = Gtk.Button(label="Hilfsprogramm einrichten (einmalig)")
        self.setup_button.connect("clicked", self.on_setup_clicked)
        button_box.append(self.setup_button)
        self.start_button = Gtk.Button(label="Fix starten")
        self.start_button.add_css_class("suggested-action")
        self.start_button.connect("clicked", self.on_start_clicked)
        button_box.append(self.start_button)
        box.append(button_box)

        self.refresh_state()

    def append_log(self, text):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text)
        self.log_view.scroll_to_iter(end, 0.0, False, 0.0, 0.0)

    def set_status(self, text):
        self.status_label.set_text(text)

    def set_step(self, number, total, text):
        label = STEPS_DE.get(number, text)
        self.step_label.set_text(f"Schritt {number}/{total}: {label}")
        self.progress.set_fraction(number / total)
        self.progress.set_text(f"{number}/{total}")

    def set_busy(self, busy):
        self.running = busy
        self.start_button.set_sensitive(not busy and self.helper_path is not None)
        self.setup_button.set_sensitive(not busy)

    def update_helper_state(self):
        self.helper_path = self.find_helper()
        self.setup_button.set_visible(self.helper_path is None)
        self.start_button.set_sensitive(not self.running and self.helper_path is not None)

    def refresh_state(self):
        if not shutil.which("flatpak-spawn"):
            self.set_status("flatpak-spawn ist in dieser Sandbox nicht verfügbar.")
            self.start_button.set_sensitive(False)
            return
        self.update_helper_state()
        if dongle_present():
            dongle_text = f"Dongle erkannt ({VENDOR}:{PRODUCT})."
        else:
            dongle_text = f"Kein Dongle ({VENDOR}:{PRODUCT}) angeschlossen."
        if self.helper_path is None:
            self.set_status(
                dongle_text + " Einmalige Einrichtung nötig: „Hilfsprogramm einrichten“ klicken."
            )
        else:
            self.set_status(dongle_text + f" Hilfsprogramm: {self.helper_path}")

    def find_helper(self):
        probe = (
            "for p in " + " ".join(HELPER_PATHS) + '; do '
            '[ -x "$p" ] && { echo "$p"; exit 0; }; done; exit 1'
        )
        try:
            result = subprocess.run(
                ["flatpak-spawn", "--host", "sh", "-c", probe],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode == 0:
            return result.stdout.strip().splitlines()[0]
        return None

    def stream_process(self, cmd, on_done):
        def worker():
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except OSError as exc:
                GLib.idle_add(self.append_log, f"Fehler beim Starten: {exc}\n")
                GLib.idle_add(on_done, 1)
                return
            for line in proc.stdout:
                match = STEP_RE.match(line.strip())
                if match:
                    GLib.idle_add(
                        self.set_step,
                        int(match.group(1)),
                        int(match.group(2)),
                        match.group(3),
                    )
                GLib.idle_add(self.append_log, line)
            returncode = proc.wait()
            GLib.idle_add(on_done, returncode)

        threading.Thread(target=worker, daemon=True).start()

    def on_setup_clicked(self, _button):
        app_dir = host_app_dir()
        if app_dir is None:
            self.append_log(
                "Konnte den Installationspfad der Flatpak nicht ermitteln.\n"
            )
            return
        source = os.path.join(app_dir, "bin", "razer-blackshark-fix")
        cmd = [
            "flatpak-spawn",
            "--host",
            "pkexec",
            "install",
            "-Dm0755",
            source,
            HELPER_PATHS[0],
        ]
        self.set_busy(True)
        self.set_status("Einrichtung läuft – Admin-Passwort im System-Dialog eingeben.")
        self.append_log("$ " + " ".join(cmd) + "\n")

        def done(returncode):
            self.append_log(f"\nEinrichtung beendet (Exit-Code {returncode}).\n")
            self.set_busy(False)
            self.update_helper_state()
            if self.helper_path is not None:
                self.set_status(f"Hilfsprogramm bereit: {self.helper_path}")
            else:
                self.set_status("Einrichtung fehlgeschlagen – Details siehe Log.")

        self.stream_process(cmd, done)

    def on_start_clicked(self, _button):
        if self.helper_path is None:
            return
        cmd = [
            "flatpak-spawn",
            "--host",
            "pkexec",
            self.helper_path,
            "--gui",
            "--user",
            self.username,
        ]
        self.set_busy(True)
        self.step_label.set_text("Fix läuft – bitte den angezeigten Schritten folgen.")
        self.progress.set_fraction(0.0)
        self.progress.set_text("0/7")
        self.append_log("\n$ " + " ".join(cmd) + "\n")

        def done(returncode):
            self.set_busy(False)
            self.update_helper_state()
            if returncode == 0:
                self.set_step(7, 7, "")
                self.step_label.set_text("Fertig: Razer BlackShark erfolgreich initialisiert.")
                self.set_status("Erfolg. Audio, Mikrofon und Lautstärketasten sollten jetzt funktionieren.")
            else:
                self.step_label.set_text("Fix fehlgeschlagen – Details siehe Log.")
                self.set_status(
                    f"Fehlgeschlagen (Exit-Code {returncode}). "
                    "Falls pkexec abgelehnt wurde, Admin-Passwort im System-Dialog eingeben."
                )

        self.stream_process(cmd, done)


class FixApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        window = FixWindow(self)
        window.present()


def main():
    app = FixApplication()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
