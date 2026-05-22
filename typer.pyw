import sys
import time
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QTimer
from pynput.keyboard import Controller
from pynput.keyboard import Key

SHIFT_CHARS = {
    "A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F": "f",
    "G": "g", "H": "h", "I": "i", "J": "j", "K": "k", "L": "l",
    "M": "m", "N": "n", "O": "o", "P": "p", "Q": "q", "R": "r",
    "S": "s", "T": "t", "U": "u", "V": "v", "W": "w", "X": "x",
    "Y": "y", "Z": "z",

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

class ClipboardTyper:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.keyboard = Controller()

        self.wait_seconds = 3
        self.speed_seconds = 0.1

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon.fromTheme("edit-paste"))
        self.tray.setToolTip("Clipboard Typer")

        self.menu = QMenu()

        self.current_wait_action = QAction(self.menu)
        self.current_wait_action.setEnabled(False)

        self.wait_up_action = QAction("Wait (+1s)", self.menu)
        self.wait_up_action.triggered.connect(self.increase_wait)

        self.wait_down_action = QAction("Wait (-1s)", self.menu)
        self.wait_down_action.triggered.connect(self.decrease_wait)

        self.current_speed_action = QAction(self.menu)
        self.current_speed_action.setEnabled(False)

        self.speed_up_action = QAction("Speed (+0.1s)", self.menu)
        self.speed_up_action.triggered.connect(self.increase_speed)

        self.speed_down_action = QAction("Speed (-0.1s)", self.menu)
        self.speed_down_action.triggered.connect(self.decrease_speed)

        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.app.quit)

        self.menu.addAction(self.current_wait_action)
        self.menu.addAction(self.wait_up_action)
        self.menu.addAction(self.wait_down_action)
        self.menu.addSeparator()
        self.menu.addAction(self.current_speed_action)
        self.menu.addAction(self.speed_up_action)
        self.menu.addAction(self.speed_down_action)
        self.menu.addSeparator()
        self.menu.addAction(quit_action)

        self.update_menu_labels()

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_clicked)
        self.tray.show()

    def update_menu_labels(self):
        self.current_wait_action.setText(f"Current Wait: ({self.wait_seconds}s)")
        self.current_speed_action.setText(f"Current Speed: ({self.speed_seconds:.1f}s)")

        self.wait_down_action.setEnabled(self.wait_seconds > 0)
        self.speed_down_action.setEnabled(self.speed_seconds > 0)

    def increase_wait(self):
        self.wait_seconds += 1
        self.update_menu_labels()

    def decrease_wait(self):
        self.wait_seconds = max(0, self.wait_seconds - 1)
        self.update_menu_labels()

    def increase_speed(self):
        self.speed_seconds = round(self.speed_seconds + 0.1, 1)
        self.update_menu_labels()

    def decrease_speed(self):
        self.speed_seconds = max(0.0, round(self.speed_seconds - 0.1, 1))
        self.update_menu_labels()

    def on_tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.start_typing_timer()

    def start_typing_timer(self):
        text = QApplication.clipboard().text()

        if not text:
            self.tray.showMessage(
                "Clipboard Typer",
                "Clipboard is empty",
                QSystemTrayIcon.MessageIcon.Warning,
                1500,
            )
            return

        self.tray.showMessage(
            "Clipboard Typer",
            f"Click where you want to type. Typing in {self.wait_seconds}s...",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

        QTimer.singleShot(self.wait_seconds * 1000, lambda: self.type_text(text))

    def type_text(self, text):
        for char in text:
            if char in SHIFT_CHARS:
                base_key = SHIFT_CHARS[char]
                self.keyboard.press(Key.shift)
                self.keyboard.press(base_key)
                self.keyboard.release(base_key)
                self.keyboard.release(Key.shift)
            else:
                self.keyboard.press(char)
                self.keyboard.release(char)

            time.sleep(self.speed_seconds)

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    ClipboardTyper().run()