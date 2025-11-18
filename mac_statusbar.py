"""macOS specific status bar integration built with PySide6."""
from __future__ import annotations

import base64

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

ICON_DATA = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAA5ElEQVR42u3bQQ6FIAyE4Tm3x9aFS70CyBRo/ZuwfpkPTF6g1Xndz5+XAAAAgHk/djxNqwxAa+CVINo19CwMZQkeBaGM4Z0IyhjcCaGZ4VtrJoKiw49WNIKiwrsrCkHu8NHlRlCm8BEIcoRfVQ6EYYDVFQ6wc3gHgjIefeenoOy7P3oKVCH8CAIAvQC7lwUg4+5/PQWqtPtfTgEAABQL34sAAAAAAAAAAAAAAAB/hQEAgAsRrsS4FAWAhxGexngc5XmcBglaZGiSok2ORklaZWmWpl2egQlGZhiaYmyOwUkAAKi9XjNvW0B6AG0FAAAAAElFTkSuQmCC"
)


def _build_icon() -> QIcon:
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(ICON_DATA), "PNG")
    return QIcon(pixmap)


class MacStatusBarApp(QObject):
    """Encapsulates the macOS status bar experience."""

    def __init__(self, backend, window):
        super().__init__(window)
        self._backend = backend
        self._window = window
        self._icon = _build_icon()
        self._tray = QSystemTrayIcon(self._icon, self)
        self._menu = QMenu()
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._handle_activation)
        self._tray.setVisible(True)
        self.update_presets()

    def update_presets(self) -> None:
        self._menu.clear()
        presets = self._backend.presets
        if presets:
            for preset in presets:
                action = QAction(preset["name"], self._menu)
                action.triggered.connect(
                    lambda _checked=False, name=preset["name"]: self._window.open_with_preset(name)
                )
                self._menu.addAction(action)
        else:
            placeholder = QAction("Keine Presets verfügbar", self._menu)
            placeholder.setEnabled(False)
            self._menu.addAction(placeholder)

        self._menu.addSeparator()
        window_action = QAction("Fenster öffnen", self._menu)
        window_action.triggered.connect(self._window.show_window)
        self._menu.addAction(window_action)

        settings_action = QAction("Einstellungen", self._menu)
        settings_action.triggered.connect(self._window.open_settings)
        self._menu.addAction(settings_action)

        quit_action = QAction("Beenden", self._menu)
        quit_action.triggered.connect(self._quit_application)
        self._menu.addAction(quit_action)

    def _quit_application(self) -> None:
        app = QApplication.instance()
        if app:
            app.quit()

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick}:
            self._window.show_window()
