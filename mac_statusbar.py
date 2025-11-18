"""macOS specific status bar integration built with PySide6."""
from __future__ import annotations

import os
from typing import Dict, Set, TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QAction, QCursor, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from backend import resource_path

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from backend import APIBackend
    from frontend import PromptPilotWindow


class _PresetExecutionSignals(QObject):
    finished = Signal(str, dict)
    failed = Signal(str, str)


class _PresetExecutionTask(QRunnable):
    """Runs a preset execution in a background thread."""

    def __init__(self, backend: "APIBackend", preset_name: str, clipboard_text: str):
        super().__init__()
        self._backend = backend
        self._preset_name = preset_name
        self._clipboard_text = clipboard_text
        self.signals = _PresetExecutionSignals()

    def run(self) -> None:  # pragma: no cover - executed in separate thread
        try:
            result = self._backend.execute_preset(self._preset_name, self._clipboard_text)
            self.signals.finished.emit(self._preset_name, result)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.signals.failed.emit(self._preset_name, str(exc))


class MacStatusBarApp(QObject):
    """Encapsulates the macOS status bar experience."""

    def __init__(self, backend: "APIBackend", window: "PromptPilotWindow"):
        super().__init__(window)
        self._backend = backend
        self._window = window
        self._thread_pool = QThreadPool.globalInstance()
        self._pending_tasks: Set[_PresetExecutionTask] = set()

        self._tray = QSystemTrayIcon(self._load_icon(), self)
        self._menu = QMenu()
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._handle_activation)
        self._tray.setVisible(True)

        self.update_presets()

    @property
    def tray_icon(self) -> QSystemTrayIcon:
        return self._tray

    # ------------------------------------------------------------------
    def update_presets(self) -> None:
        self._menu.clear()
        presets = list(self._backend.presets)
        if presets:
            for preset in presets:
                action = QAction(preset["name"], self._menu)
                action.triggered.connect(
                    lambda _checked=False, name=preset["name"]: self._handle_preset_selection(name)
                )
                self._menu.addAction(action)
        else:
            placeholder = QAction("Keine Presets verfügbar", self._menu)
            placeholder.setEnabled(False)
            self._menu.addAction(placeholder)

        self._menu.addSeparator()

        settings_action = QAction("Einstellungen", self._menu)
        settings_action.triggered.connect(self._open_settings)
        self._menu.addAction(settings_action)

        quit_action = QAction("Beenden", self._menu)
        quit_action.triggered.connect(self._quit_application)
        self._menu.addAction(quit_action)

    # ------------------------------------------------------------------
    def _handle_preset_selection(self, preset_name: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            self._notify(
                "PromptPilot",
                "Zwischenablage ist nicht verfügbar.",
                QSystemTrayIcon.Critical,
            )
            return

        text = clipboard.text() or ""
        if not text.strip():
            self._notify(
                "PromptPilot",
                "Zwischenablage ist leer.",
                QSystemTrayIcon.Warning,
            )
            return

        task = _PresetExecutionTask(self._backend, preset_name, text)
        self._pending_tasks.add(task)
        task.signals.finished.connect(
            lambda name, result, task=task: self._handle_execution_result(task, name, result)
        )
        task.signals.failed.connect(
            lambda name, message, task=task: self._handle_execution_error(task, name, message)
        )
        self._thread_pool.start(task)
        self._notify("PromptPilot", f"'{preset_name}' wird ausgeführt …", QSystemTrayIcon.Information)

    def _handle_execution_result(
        self, task: _PresetExecutionTask, preset_name: str, result: Dict[str, str]
    ) -> None:
        self._pending_tasks.discard(task)
        if result.get("status") == "success":
            response = (result.get("response") or "").strip()
            snippet = response if len(response) <= 180 else f"{response[:177]}…"
            if response:
                clipboard = QApplication.clipboard()
                clipboard.setText(response)
            message = snippet or "Antwort wurde kopiert."
            self._notify_preset_finished(preset_name, message)
        else:
            self._notify(
                preset_name,
                result.get("message", "Unbekannter Fehler"),
                QSystemTrayIcon.Critical,
            )

    def _handle_execution_error(self, task: _PresetExecutionTask, preset_name: str, message: str) -> None:
        self._pending_tasks.discard(task)
        self._notify(preset_name, message, QSystemTrayIcon.Critical)

    def _open_settings(self) -> None:
        self._window.show_window()
        self._window.open_settings()

    def _quit_application(self) -> None:
        app = QApplication.instance()
        if app:
            app.quit()

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # Showing the popup for every activation reason caused the menu to appear
        # twice on macOS (the native menu plus our manual popup). Limiting the
        # manual popup to left-clicks keeps the UX clean.
        if reason == QSystemTrayIcon.Trigger:
            self._menu.popup(QCursor.pos())

    def _load_icon(self) -> QIcon:
        for icon_name in ("icon.icns", "icon.png"):
            icon_path = resource_path(icon_name)
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    return icon
        app = QApplication.instance()
        if app and not app.windowIcon().isNull():
            return app.windowIcon()
        fallback = QIcon.fromTheme("applications-utilities")
        return fallback if not fallback.isNull() else QIcon()

    def _notify(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon,
    ) -> None:
        self._tray.showMessage(title, message, icon, 8000)

    def _notify_preset_finished(self, preset_name: str, message: str) -> None:
        """Show a notification when a preset triggered via the status bar finishes."""
        title = f"{preset_name} abgeschlossen"
        body = message or "Preset erfolgreich beendet."
        self._notify(title, body, QSystemTrayIcon.Information)
