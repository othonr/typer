import sys
import time
import json
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QTimer

from pynput.keyboard import Controller, Key, Listener


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "clipboard.json"

MAX_TEXT_LENGTH = 100


SHIFT_CHARS = {
    **{chr(c): chr(c).lower() for c in range(ord("A"), ord("Z") + 1)},

    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
    "~": "`",
}


DEFAULT_CONFIG = {
    "settings": {
        "wait_seconds": 3,
        "keystrokes_per_second": 10
    },
    "custom_entries": [
        {
            "menu_name": "Adm Usr",
            "string_to_copy": "user@example.com"
        },
        {
            "menu_name": "Adm Psw",
            "string_to_copy": "password123"
        }
    ]
}

class ClipboardTyper:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.keyboard = Controller()
        self.cancel_typing = False
        self.is_typing = False

        self.listener = Listener(on_press=self.on_key_press)
        self.listener.start()

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon.fromTheme("edit-paste"))
        self.tray.setToolTip("Clipboard Typer")

        self.menu = QMenu()

        self.load_config()
        self.build_menu()

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_clicked)
        self.tray.show()

    def load_config(self):
        if not CONFIG_FILE.exists():
            CONFIG_FILE.write_text(
                json.dumps(DEFAULT_CONFIG, indent=4),
                encoding="utf-8"
            )

        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as file:
                self.config = json.load(file)
        except Exception:
            self.config = DEFAULT_CONFIG.copy()

        settings = self.config.get("settings", {})

        self.wait_seconds = int(settings.get("wait_seconds", 3))
        self.keystrokes_per_second = int(settings.get("keystrokes_per_second", 10))

        self.wait_seconds = max(0, self.wait_seconds)
        self.keystrokes_per_second = max(1, self.keystrokes_per_second)

    def save_config(self):
        self.config["settings"] = {
            "wait_seconds": self.wait_seconds,
            "keystrokes_per_second": self.keystrokes_per_second
        }

        CONFIG_FILE.write_text(
            json.dumps(self.config, indent=4),
            encoding="utf-8"
        )

    def build_menu(self):
        self.menu.clear()

        self.current_wait_action = QAction(self.menu)
        self.current_wait_action.setEnabled(False)

        wait_up_action = QAction("Wait (+1s)", self.menu)
        wait_up_action.triggered.connect(self.increase_wait)

        wait_down_action = QAction("Wait (-1s)", self.menu)
        wait_down_action.triggered.connect(self.decrease_wait)

        self.current_kps_action = QAction(self.menu)
        self.current_kps_action.setEnabled(False)

        kps_up_action = QAction("Keystrokes/sec (+1)", self.menu)
        kps_up_action.triggered.connect(self.increase_kps)

        kps_down_action = QAction("Keystrokes/sec (-1)", self.menu)
        kps_down_action.triggered.connect(self.decrease_kps)

        self.menu.addAction(self.current_wait_action)
        self.menu.addAction(wait_up_action)
        self.menu.addAction(wait_down_action)
        self.menu.addSeparator()

        self.menu.addAction(self.current_kps_action)
        self.menu.addAction(kps_up_action)
        self.menu.addAction(kps_down_action)
        self.menu.addSeparator()

        custom_entries = self.config.get("custom_entries", [])

        if custom_entries:
            for entry in custom_entries:
                menu_name = entry.get("menu_name", "Unnamed")
                string_to_copy = entry.get("string_to_copy", "")

                action = QAction(menu_name, self.menu)
                action.triggered.connect(
                    lambda checked=False, text=string_to_copy: self.start_typing_timer(text)
                )
                self.menu.addAction(action)

            self.menu.addSeparator()

        reload_action = QAction("Reload Custom Entries", self.menu)
        reload_action.triggered.connect(self.reload_custom_entries)
        self.menu.addAction(reload_action)

        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)

        self.update_menu_labels()

    def update_menu_labels(self):
        self.current_wait_action.setText(f"Current Wait: ({self.wait_seconds}s)")
        self.current_kps_action.setText(
            f"Current Keystrokes/sec: ({self.keystrokes_per_second})"
        )

    def reload_custom_entries(self):
        self.load_config()
        self.build_menu()

        self.tray.showMessage(
            "Clipboard Typer",
            "Custom entries reloaded",
            QSystemTrayIcon.MessageIcon.Information,
            1500,
        )

    def increase_wait(self):
        self.wait_seconds += 1
        self.update_menu_labels()
        self.save_config()

    def decrease_wait(self):
        self.wait_seconds = max(0, self.wait_seconds - 1)
        self.update_menu_labels()
        self.save_config()

    def increase_kps(self):
        self.keystrokes_per_second += 1
        self.update_menu_labels()
        self.save_config()

    def decrease_kps(self):
        self.keystrokes_per_second = max(1, self.keystrokes_per_second - 1)
        self.update_menu_labels()
        self.save_config()

    def on_tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            clipboard_text = QApplication.clipboard().text()
            self.start_typing_timer(clipboard_text)

    def start_typing_timer(self, text):
        if self.is_typing:
            self.tray.showMessage(
                "Clipboard Typer",
                "Already typing. Press Esc to cancel.",
                QSystemTrayIcon.MessageIcon.Warning,
                1500,
            )
            return

        if not text:
            self.tray.showMessage(
                "Clipboard Typer",
                "No text to type",
                QSystemTrayIcon.MessageIcon.Warning,
                1500,
            )
            return

        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]

            self.tray.showMessage(
                "Clipboard Typer",
                f"Text limited to {MAX_TEXT_LENGTH} characters.",
                QSystemTrayIcon.MessageIcon.Warning,
                1500,
            )

        self.cancel_typing = False

        self.tray.showMessage(
            "Clipboard Typer",
            f"Click where you want to type. Typing in {self.wait_seconds}s. Press Esc to cancel.",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

        QTimer.singleShot(
            self.wait_seconds * 1000,
            lambda: self.type_text(text)
        )

    def type_text(self, text):
        if self.cancel_typing:
            self.cancel_typing = False
            return

        self.is_typing = True

        delay_between_keys = 1.0 / self.keystrokes_per_second

        try:
            for char in text:
                if self.cancel_typing:
                    break

                self.type_char(char)
                time.sleep(delay_between_keys)
        finally:
            was_cancelled = self.cancel_typing

            self.is_typing = False
            self.cancel_typing = False

            if was_cancelled:
                self.tray.showMessage(
                    "Clipboard Typer",
                    "Typing cancelled.",
                    QSystemTrayIcon.MessageIcon.Information,
                    1500,
                )

    def type_char(self, char):
        if char == "\n":
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
            return

        if char == "\t":
            self.keyboard.press(Key.tab)
            self.keyboard.release(Key.tab)
            return

        if char in SHIFT_CHARS:
            base_key = SHIFT_CHARS[char]

            self.keyboard.press(Key.shift)
            self.keyboard.press(base_key)
            self.keyboard.release(base_key)
            self.keyboard.release(Key.shift)
            return

        self.keyboard.press(char)
        self.keyboard.release(char)

    def on_key_press(self, key):
        if key == Key.esc and self.is_typing:
            self.cancel_typing = True

    def quit_app(self):
        self.cancel_typing = True

        if self.listener:
            self.listener.stop()

        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    ClipboardTyper().run()