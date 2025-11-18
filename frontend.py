from __future__ import annotations

import sys
from typing import Dict, List, Optional

import pyperclip
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend import APIBackend, get_platform
from hotkeys import GlobalHotkeyManager

try:  # Import lazily to keep Linux/Windows installations lightweight
    from mac_statusbar import MacStatusBarApp
except Exception:  # pragma: no cover - optional dependency during testing
    MacStatusBarApp = None  # type: ignore


def copy_to_clipboard(text: str) -> None:
    try:
        pyperclip.copy(text)
    except Exception:
        pass


def _hide_macos_dock_icon() -> None:
    if get_platform() != "mac":
        return
    try:
        import ctypes
        import ctypes.util

        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        ctypes.cdll.LoadLibrary(ctypes.util.find_library("AppKit"))

        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        ns_app = objc.objc_getClass(b"NSApplication")
        shared_app = objc.sel_registerName(b"sharedApplication")
        app_instance = objc.objc_msgSend(ns_app, shared_app)

        set_policy = objc.sel_registerName(b"setActivationPolicy:")
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        objc.objc_msgSend(app_instance, set_policy, 1)  # NSApplicationActivationPolicyAccessory
    except Exception:
        pass


class PresetEditorDialog(QDialog):
    def __init__(self, preset: Optional[Dict] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Preset bearbeiten")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.name_edit = QLineEdit(preset["name"] if preset else "")
        self.prompt_edit = QTextEdit(preset["prompt"] if preset else "")
        self.api_edit = QLineEdit(preset["api_type"] if preset else "chatgpt")

        form.addRow("Name", self.name_edit)
        form.addRow("Prompt", self.prompt_edit)
        form.addRow("API", self.api_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:  # type: ignore[override]
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Fehler", "Name darf nicht leer sein")
            return
        if not self.prompt_edit.toPlainText().strip():
            QMessageBox.warning(self, "Fehler", "Prompt darf nicht leer sein")
            return
        super().accept()

    def data(self) -> Dict[str, str]:
        return {
            "name": self.name_edit.text().strip(),
            "prompt": self.prompt_edit.toPlainText().strip(),
            "api_type": self.api_edit.text().strip() or "chatgpt",
        }


class SettingsDialog(QDialog):
    def __init__(self, backend: APIBackend, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.backend = backend
        self.refresh_required = False

        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        description = QLabel("Verwalte Presets und Zugangsdaten")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.preset_list = QListWidget()
        layout.addWidget(self.preset_list)

        button_row = QHBoxLayout()
        self.add_btn = QPushButton("Neu")
        self.edit_btn = QPushButton("Bearbeiten")
        self.delete_btn = QPushButton("Löschen")
        button_row.addWidget(self.add_btn)
        button_row.addWidget(self.edit_btn)
        button_row.addWidget(self.delete_btn)
        layout.addLayout(button_row)

        shortcut_row = QHBoxLayout()
        self.shortcut_edit = QLineEdit()
        self.shortcut_edit.setPlaceholderText("Shortcut z.B. Ctrl+Alt+K")
        self.save_shortcut_btn = QPushButton("Shortcut speichern")
        shortcut_row.addWidget(self.shortcut_edit, 2)
        shortcut_row.addWidget(self.save_shortcut_btn, 1)
        layout.addLayout(shortcut_row)

        form = QFormLayout()
        self.api_key_edit = QLineEdit(self.backend.api_credentials.get("OpenAI", ""))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        form.addRow("OpenAI API Key", self.api_key_edit)
        layout.addLayout(form)

        self.save_api_btn = QPushButton("API Key speichern")
        layout.addWidget(self.save_api_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.add_btn.clicked.connect(self._handle_add)
        self.edit_btn.clicked.connect(self._handle_edit)
        self.delete_btn.clicked.connect(self._handle_delete)
        self.save_shortcut_btn.clicked.connect(self._handle_shortcut)
        self.save_api_btn.clicked.connect(self._handle_save_api)
        self.preset_list.currentRowChanged.connect(self._sync_shortcut_field)

        self._presets: List[Dict] = []
        self._load_presets()

    def _load_presets(self) -> None:
        self._presets = list(self.backend.presets)
        self.preset_list.clear()
        for preset in self._presets:
            self.preset_list.addItem(QListWidgetItem(preset["name"]))
        self._sync_shortcut_field(self.preset_list.currentRow())

    def _current_index(self) -> int:
        return self.preset_list.currentRow()

    def _handle_add(self) -> None:
        dialog = PresetEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.data()
            if self.backend.save_preset(data["name"], data["prompt"], data["api_type"]):
                self.refresh_required = True
                self._load_presets()
            else:
                QMessageBox.warning(self, "Fehler", "Preset konnte nicht gespeichert werden")

    def _handle_edit(self) -> None:
        index = self._current_index()
        if index < 0:
            return
        preset = self._presets[index]
        dialog = PresetEditorDialog(preset, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.data()
            if self.backend.update_preset_by_index(index, data["name"], data["prompt"], data["api_type"]):
                self.refresh_required = True
                self._load_presets()
            else:
                QMessageBox.warning(self, "Fehler", "Preset konnte nicht aktualisiert werden")

    def _handle_delete(self) -> None:
        index = self._current_index()
        if index < 0:
            return
        preset = self._presets[index]
        if QMessageBox.question(
            self,
            "Preset löschen",
            f"Möchtest du '{preset['name']}' wirklich löschen?",
        ) == QMessageBox.Yes:
            if self.backend.delete_preset_by_index(index):
                self.refresh_required = True
                self._load_presets()

    def _handle_shortcut(self) -> None:
        index = self._current_index()
        if index < 0:
            return
        shortcut = self.shortcut_edit.text().strip()
        if self.backend.save_preset_shortcut(index, shortcut):
            self.refresh_required = True
            QMessageBox.information(self, "Gespeichert", "Shortcut aktualisiert")
        else:
            QMessageBox.warning(self, "Fehler", "Shortcut konnte nicht gespeichert werden")

    def _handle_save_api(self) -> None:
        if self.backend.save_credentials(self.api_key_edit.text().strip(), "OpenAI"):
            QMessageBox.information(self, "Gespeichert", "API Key gespeichert")
        else:
            QMessageBox.warning(self, "Fehler", "API Key konnte nicht gespeichert werden")

    def _sync_shortcut_field(self, index: int) -> None:
        if index < 0 or index >= len(self._presets):
            self.shortcut_edit.setText("")
            return
        shortcut = self._presets[index].get("shortcut", "")
        self.shortcut_edit.setText(shortcut)


class PromptPilotWindow(QMainWindow):
    def __init__(self, backend: APIBackend):
        super().__init__()
        self.backend = backend
        self.platform = get_platform()
        self.hotkeys = GlobalHotkeyManager(self._handle_hotkey_trigger)
        self._mac_statusbar: Optional[object] = None

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.hotkeys.stop)

        self._build_ui()
        self._initialize_statusbar()

        if self.platform == "mac" and MacStatusBarApp is not None:
            self._mac_statusbar = MacStatusBarApp(self.backend, self)

        self.load_presets()

    def _build_ui(self) -> None:
        self.setWindowTitle("PromptPilot")
        self.setMinimumSize(660, 440)
        self.setStyleSheet(
            """
            QMainWindow { background: #f5f5f7; }
            QLabel#TitleLabel { font-size: 26px; font-weight: 600; }
            QComboBox, QTextEdit, QLineEdit {
                border: 1px solid #dcdce1;
                border-radius: 10px;
                padding: 8px;
                background: #ffffff;
            }
            QPushButton#PrimaryButton {
                background-color: #007aff;
                color: white;
                border-radius: 12px;
                padding: 12px 18px;
                font-weight: 600;
            }
            QPushButton#PrimaryButton:disabled { background-color: #aac8ff; }
            QPushButton#SecondaryButton {
                background-color: transparent;
                border: 1px solid #d0d0d5;
                border-radius: 10px;
                padding: 8px 14px;
            }
            """
        )

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(24)

        header_row = QHBoxLayout()
        header_row.setSpacing(16)
        title = QLabel("PromptPilot")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Kurze, klare Eingaben für deine Presets")
        subtitle.setStyleSheet("color: #6e6e73;")
        header_left = QVBoxLayout()
        header_left.setSpacing(4)
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_row.addLayout(header_left, 1)

        self.settings_btn = QPushButton("Einstellungen")
        self.settings_btn.setObjectName("SecondaryButton")
        self.settings_btn.clicked.connect(self.open_settings)
        header_row.addWidget(self.settings_btn, 0, Qt.AlignRight)
        layout.addLayout(header_row)

        combo_container = QVBoxLayout()
        combo_container.setSpacing(6)
        combo_label = QLabel("Preset")
        combo_label.setStyleSheet("color: #6e6e73;")
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumHeight(36)
        combo_container.addWidget(combo_label)
        combo_container.addWidget(self.preset_combo)
        layout.addLayout(combo_container)

        input_container = QVBoxLayout()
        input_container.setSpacing(6)
        input_label = QLabel("Eingabe")
        input_label.setStyleSheet("color: #6e6e73;")
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Beschreibe, was erledigt werden soll…")
        self.prompt_edit.setMinimumHeight(220)
        input_container.addWidget(input_label)
        input_container.addWidget(self.prompt_edit)
        layout.addLayout(input_container)

        self.run_button = QPushButton("Ausführen")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.clicked.connect(self.execute_current_preset)
        layout.addWidget(self.run_button, alignment=Qt.AlignRight)

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.execute_current_preset)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.execute_current_preset)

    def _initialize_statusbar(self) -> None:
        status = QStatusBar()
        status.showMessage("Bereit.")
        self.setStatusBar(status)

    # ------------------------------------------------------------------
    def load_presets(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        presets = list(self.backend.presets)
        for preset in presets:
            self.preset_combo.addItem(preset["name"])
        self.preset_combo.blockSignals(False)
        self.run_button.setEnabled(bool(presets))

        shortcut_map = {
            preset.get("shortcut", ""): preset["name"] for preset in presets if preset.get("shortcut")
        }
        self.hotkeys.update_shortcuts(shortcut_map)

        if self._mac_statusbar:
            self._mac_statusbar.update_presets()

    def execute_current_preset(self) -> None:
        preset_name = self.preset_combo.currentText()
        user_input = self.prompt_edit.toPlainText().strip()
        if not preset_name:
            QMessageBox.warning(self, "Kein Preset", "Bitte wähle ein Preset aus")
            return
        if not user_input:
            QMessageBox.warning(self, "Leere Eingabe", "Bitte gib einen Text ein")
            return

        self.run_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = self.backend.execute_preset(preset_name, user_input)
        finally:
            QApplication.restoreOverrideCursor()
            self.run_button.setEnabled(True)

        if result.get("status") != "success":
            QMessageBox.critical(self, "Fehler", result.get("message", "Unbekannter Fehler"))
            return

        response = result.get("response", "")
        copy_to_clipboard(response)
        QMessageBox.information(self, "Fertig", "Antwort wurde in die Zwischenablage kopiert.")
        self.statusBar().showMessage("Ausgabe kopiert", 5000)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.backend, self)
        dialog.exec()
        if dialog.refresh_required:
            self.load_presets()

    def open_with_preset(self, preset_name: str) -> None:
        index = self.preset_combo.findText(preset_name)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        self.show_window()

    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _handle_hotkey_trigger(self, preset_name: str) -> None:
        self.open_with_preset(preset_name)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.platform == "mac":
            event.ignore()
            self.hide()
            return
        self.hotkeys.stop()
        super().closeEvent(event)


def launch_app() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    platform = get_platform()
    if platform == "mac":
        _hide_macos_dock_icon()
        app.setQuitOnLastWindowClosed(False)
    backend = APIBackend()
    window = PromptPilotWindow(backend)
    if platform != "mac":
        window.show()
    else:
        window.hide()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_app()
