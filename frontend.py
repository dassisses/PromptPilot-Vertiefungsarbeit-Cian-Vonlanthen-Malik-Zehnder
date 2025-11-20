import os
import sys
import pyperclip
import threading
from typing import Optional

from backend import APIBackend, resource_path, get_platform

PLATFORM = get_platform()

if PLATFORM == "windows":
    try:
        from pynput import keyboard as _pynput_keyboard
        PYNPUT_AVAILABLE = True
    except Exception:
        _pynput_keyboard = None
        PYNPUT_AVAILABLE = False
else:
    _pynput_keyboard = None
    PYNPUT_AVAILABLE = False

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QFont, QAction, QKeySequence, QPalette, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFrame, QScrollArea, QMessageBox, QStackedWidget,
    QTextEdit, QDialog, QSplitter, QKeySequenceEdit,
    QSystemTrayIcon, QMenu, QStyle
)


MAC_ACCESSIBILITY_TRUSTED = True


def _is_process_trusted() -> bool:
    # PyInstaller gibt bei macOS immer False zurück.
    # Wir deaktivieren die native Abfrage vollständig.
    return True


# ===== HELPER FUNCTIONS (müssen vor den Klassen definiert sein) =====

# New UI / behavior constants
MAX_PRESET_NAME_LENGTH = 30  # displayed length before truncation
MAX_PRESET_NAME_STORE = 60   # max length allowed for storing names


MODIFIER_ORDER = ("Ctrl", "Meta", "Alt", "AltGr", "Shift")
PRIMARY_MODIFIERS = {"Ctrl", "Alt", "AltGr", "Meta"}
MODIFIER_SYNONYMS = {
    "ctrl": "Ctrl",
    "control": "Ctrl",
    "shift": "Shift",
    "alt": "Alt",
    "option": "Alt",
    "altgr": "AltGr",
    "meta": "Meta",
    "cmd": "Meta",
    "command": "Meta",
    "super": "Meta",
}

KEY_SYNONYMS = {
    "return": "Enter",
    "enter": "Enter",
    "esc": "Escape",
    "escape": "Escape",
    "space": "Space",
    "tab": "Tab",
    "backspace": "Backspace",
    "del": "Delete",
    "delete": "Delete",
    "plus": "+",
    "minus": "-",
    "asterisk": "*",
    "slash": "/",
    "period": ".",
    "comma": ",",
}


def _lookup(mapping, key):
    if key in mapping:
        return mapping[key]
    lower = key.lower()
    return mapping.get(lower)


def canonicalize_shortcut(shortcut_str: str, platform: str = None) -> str:
    """Create a canonical representation of a shortcut that is stable across platforms."""
    if platform is None:
        platform = sys.platform

    if not shortcut_str or not shortcut_str.strip():
        raise ValueError("Shortcut darf nicht leer sein")

    raw = shortcut_str.strip()
    sequence = QKeySequence(raw)
    if sequence.isEmpty():
        raise ValueError("Shortcut konnte nicht interpretiert werden")

    seq_str = sequence.toString(QKeySequence.SequenceFormat.PortableText)
    if not seq_str:
        raise ValueError("Shortcut konnte nicht interpretiert werden")

    # Qt kann mehrere Sequenzen liefern (durch Komma getrennt). Wir verwenden nur die erste.
    if "," in seq_str:
        seq_str = seq_str.split(",", 1)[0].strip()

    if "+" not in seq_str:
        raise ValueError("Shortcut benötigt mindestens einen Modifier (z.B. Ctrl+T)")

    mods_part, key_part = seq_str.rsplit("+", 1)
    modifiers_raw = [m.strip() for m in mods_part.split("+") if m.strip()]
    key_raw = key_part.strip()

    if not modifiers_raw:
        raise ValueError("Shortcut benötigt mindestens einen Modifier (z.B. Ctrl+T)")
    if not key_raw:
        raise ValueError("Shortcut-Taste konnte nicht erkannt werden")

    modifiers = []
    seen_mods = set()
    for mod in modifiers_raw:
        canonical = _lookup(MODIFIER_SYNONYMS, mod)
        if not canonical:
            raise ValueError(f"Ungültiger Modifier: '{mod}'")
        if canonical not in seen_mods:
            seen_mods.add(canonical)
            modifiers.append(canonical)

    if not any(m in PRIMARY_MODIFIERS for m in modifiers):
        raise ValueError(
            "Shortcut benötigt mindestens einen Haupt-Modifier (Ctrl/Cmd oder Alt)."
        )

    # Sortiere Modifier für eine stabile Darstellung
    modifiers.sort(key=lambda m: MODIFIER_ORDER.index(m) if m in MODIFIER_ORDER else len(MODIFIER_ORDER))

    key_lookup = _lookup(KEY_SYNONYMS, key_raw) or key_raw
    if len(key_lookup) == 1:
        key_lookup = key_lookup.upper()

    canonical = "+".join(modifiers + [key_lookup])

    # Plattform-spezifische Feinheiten (z.B. Cmd auf macOS als Meta belassen)
    if platform == "darwin":
        canonical = canonical.replace("Cmd+", "Meta+")

    return canonical


def format_shortcut_for_display(shortcut_str: str, platform: str = None) -> str:
    """Returns a user-facing representation of the shortcut (with platform glyphs where appropriate)."""
    if not shortcut_str:
        return ""

    if platform is None:
        platform = sys.platform

    if "+" not in shortcut_str:
        return shortcut_str

    mods_part, key_part = shortcut_str.rsplit("+", 1)
    modifiers = [p.strip() for p in mods_part.split("+") if p.strip()]
    key = key_part.strip() or "+"
    key_display = _lookup(KEY_SYNONYMS, key) or key
    if len(key_display) == 1:
        key_display = key_display.upper()

    display_map = {
        "Ctrl": "Ctrl",
        "Alt": "Alt" if platform != "darwin" else "⌥",
        "Shift": "Shift" if platform != "darwin" else "⇧",
        "AltGr": "AltGr",
        "Meta": "⌘" if platform == "darwin" else "Meta",
    }

    display_mods = [display_map.get(mod, mod) for mod in modifiers]
    return " + ".join(display_mods + [key_display])


def is_valid_shortcut(shortcut_str: str, platform: str = None) -> tuple:
    """
    Validiert einen Shortcut-String.
    Returniert (is_valid, error_message)
    """
    try:
        canonicalize_shortcut(shortcut_str, platform)
        return True, ""
    except ValueError as exc:
        return False, str(exc)


def normalize_shortcut_for_platform(shortcut_str: str, platform: str = None) -> str:
    """
    Normalisiert einen Shortcut-String (benutzerfreundliche Synonyme) für Speicherung.
    Ersetzt z.B. 'Control' -> 'Ctrl', 'Option' -> 'Alt' usw.
    """
    try:
        return canonicalize_shortcut(shortcut_str, platform)
    except ValueError:
        return shortcut_str.strip()


def canonicalize_shortcut_for_qt(shortcut_str: str, platform: str = None) -> str:
    """
    Erzeugt eine Qt-kompatible Shortcut-Notation aus einer vom Nutzer eingegebenen Shortcut-Notation.
    - Normalisiert Synonyme (Control->Ctrl, Option->Alt)
    - Auf macOS: lässt Meta als Meta (Qt erwartet 'Meta' für Command)
    - Auf Windows/Linux: wandelt Meta -> Ctrl
    """
    try:
        return canonicalize_shortcut(shortcut_str, platform)
    except ValueError:
        return shortcut_str.strip()


# Platform-specific modifier key (Anzeige / Tooltip)
def get_modifier_key():
    """Returns 'Meta' for macOS, 'Ctrl' for Windows/Linux"""
    return "Meta" if sys.platform == "darwin" else "Ctrl"

MODIFIER_KEY = get_modifier_key()
MODIFIER_KEY_DISPLAY = "⌘" if sys.platform == "darwin" else "Ctrl"

# Use a guaranteed available font family to avoid expensive lookups for missing
# fonts such as "SF Pro Display".
# NOTE: Accessing QFont/QFontDatabase before a QApplication exists causes
# "QFontDatabase: Must construct a QGuiApplication" errors.  We therefore use a
# static fallback that is updated once the QApplication is created.
APP_FONT_FAMILY = "SF Pro Text"

# Layout baseline values for consistent macOS-inspired spacing
OUTER_MARGIN = 24
SECTION_SPACING = 16
CONTROL_SPACING = 12


def refresh_app_font_family() -> None:
    """Update the global font family after a QApplication exists."""

    global APP_FONT_FAMILY

    try:
        # Prefer the application font when available.  This only works after a
        # QApplication (or QGuiApplication) has been constructed.
        app_font = QApplication.font()
        if app_font and app_font.family():
            APP_FONT_FAMILY = app_font.family()
            return
    except Exception:
        # QApplication.font() may raise if no application instance exists yet.
        pass

    try:
        default_family = QFont().defaultFamily()
        if default_family:
            APP_FONT_FAMILY = default_family
    except Exception:
        # If we cannot query Qt for a font we simply keep the fallback.
        pass


def create_section_divider() -> QFrame:
    """Return a subtle horizontal divider for separating logical sections."""

    divider = QFrame()
    divider.setObjectName("section_divider")
    divider.setFrameShape(QFrame.Shape.HLine)
    divider.setFrameShadow(QFrame.Shadow.Plain)
    divider.setFixedHeight(1)
    return divider


class EditPresetDialog(QDialog):
    """Dialog zum Bearbeiten eines bestehenden Presets"""

    def __init__(self, parent=None, preset_data=None, provider_models=None):
        super().__init__(parent)
        self.provider_models = provider_models or {}
        self.setWindowTitle("Preset bearbeiten")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Name
        name_label = QLabel("Preset-Name")
        name_label.setObjectName("input_label")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("z.B. Text Zusammenfassung")
        self.name_input.setMinimumHeight(40)
        self.name_input.setMaxLength(MAX_PRESET_NAME_STORE)
        if preset_data:
            self.name_input.setText(preset_data.get("name", ""))
        layout.addWidget(self.name_input)

        # Prompt
        prompt_label = QLabel("Prompt-Text")
        prompt_label.setObjectName("input_label")
        layout.addWidget(prompt_label)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Schreibe deinen Prompt hier...")
        self.prompt_input.setAcceptRichText(False)
        self.prompt_input.setMinimumHeight(180)
        if preset_data:
            self.prompt_input.setPlainText(preset_data.get("prompt", ""))
        layout.addWidget(self.prompt_input)

        # Provider
        provider_label = QLabel("Provider")
        provider_label.setObjectName("input_label")
        layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumHeight(40)
        self.provider_combo.addItems(list(self.provider_models.keys()))
        self.provider_combo.currentTextChanged.connect(self._update_models)
        layout.addWidget(self.provider_combo)

        # Model
        model_label = QLabel("Modell")
        model_label.setObjectName("input_label")
        layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(40)
        layout.addWidget(self.model_combo)

        provider_value = preset_data.get("provider") if preset_data else None
        model_value = preset_data.get("model") if preset_data else None
        fallback_provider = preset_data.get("api_type") if preset_data else None
        if provider_value and provider_value not in self.provider_models:
            self.provider_combo.addItem(provider_value)
        if fallback_provider and fallback_provider not in self.provider_models:
            self.provider_combo.addItem(fallback_provider)

        if provider_value:
            idx = self.provider_combo.findText(provider_value)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        elif fallback_provider:
            idx = self.provider_combo.findText(fallback_provider)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        self._update_models(self.provider_combo.currentText())
        if model_value:
            m_idx = self.model_combo.findText(model_value)
            if m_idx >= 0:
                self.model_combo.setCurrentIndex(m_idx)

        layout.addSpacing(16)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.setMinimumHeight(44)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("btn_primary")
        save_btn.setMinimumHeight(44)
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "prompt": self.prompt_input.toPlainText().strip(),
            "api_type": self.provider_combo.currentText(),
            "provider": self.provider_combo.currentText(),
            "model": self.model_combo.currentText(),
        }

    def _update_models(self, provider: str):
        models = self.provider_models.get(provider, [])
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)


class ShortcutDialog(QDialog):
    """Dialog zum Einstellen eines Shortcuts für ein Preset"""

    def __init__(self, parent=None, current_shortcut=""):
        super().__init__(parent)
        self.setWindowTitle("Shortcut einstellen")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        info_label = QLabel("Tastenkombination")
        info_label.setObjectName("dialog_title")
        info_label.setFont(QFont(APP_FONT_FAMILY, 16, QFont.Weight.Bold))
        layout.addWidget(info_label)

        desc = QLabel("Definiere eine Tastenkombination für schnellen Zugriff")
        desc.setObjectName("section_subtitle")
        layout.addWidget(desc)

        self.shortcut_edit = QKeySequenceEdit()
        self.shortcut_edit.setObjectName("shortcut_input")
        self.shortcut_edit.setMaximumSequenceLength(1)
        if current_shortcut:
            try:
                normalized = canonicalize_shortcut(current_shortcut)
            except ValueError:
                normalized = current_shortcut
            self.shortcut_edit.setKeySequence(QKeySequence(normalized))
        layout.addWidget(self.shortcut_edit)

        # Beispiele - plattformspezifisch
        if sys.platform == "darwin":
            examples = QLabel("Beispiele: Control+Shift+S, Control+T, Option+Control+P")
        else:
            examples = QLabel("Beispiele: Ctrl+Shift+S, Ctrl+T, Ctrl+Alt+P")
        examples.setObjectName("hint_text")
        layout.addWidget(examples)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("error_label")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        layout.addSpacing(12)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Bestätigen")
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self.validate_and_accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def validate_and_accept(self):
        """Validiert den Shortcut vor dem Akzeptieren"""
        sequence = self.shortcut_edit.keySequence()
        if sequence.isEmpty():
            self.show_error("Shortcut darf nicht leer sein")
            return

        portable = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        try:
            normalized = canonicalize_shortcut(portable)
        except ValueError as exc:
            self.show_error(str(exc))
            return

        self._result_shortcut = normalized
        self.error_label.hide()
        self.shortcut_edit.setProperty("error", False)
        self.accept()

    def show_error(self, message):
        """Zeigt einen Fehler an"""
        self.error_label.setText(message)
        self.error_label.show()
        self.shortcut_edit.setProperty("error", True)
        self.shortcut_edit.style().unpolish(self.shortcut_edit)
        self.shortcut_edit.style().polish(self.shortcut_edit)

    def get_shortcut(self):
        return getattr(self, "_result_shortcut", "")


class ShortcutOverviewDialog(QDialog):
    """Dialog zur Anzeige aller registrierten Shortcuts"""

    def __init__(self, parent=None, shortcuts_dict=None, presets=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcuts")
        self.setMinimumWidth(650)
        self.setMinimumHeight(450)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Registrierte Shortcuts")
        title.setObjectName("dialog_title")
        title.setFont(QFont(APP_FONT_FAMILY, 20, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Alle verfügbaren Tastenkombinationen auf einen Blick")
        subtitle.setObjectName("section_subtitle")
        layout.addWidget(subtitle)

        # Scroll area für Shortcuts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("scroll_area")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # System Shortcuts
        system_card = QWidget()
        system_card.setObjectName("shortcut_card")
        system_layout = QVBoxLayout(system_card)
        system_layout.setContentsMargins(20, 16, 20, 16)
        system_layout.setSpacing(10)

        system_title = QLabel("System-Shortcuts")
        system_title.setObjectName("card_title")
        system_title.setFont(QFont(APP_FONT_FAMILY, 14, QFont.Weight.Bold))
        system_layout.addWidget(system_title)

        system_layout.addWidget(self.create_shortcut_item(format_shortcut_for_display(f"{MODIFIER_KEY}+1"), "Presets-Seite"))
        system_layout.addWidget(self.create_shortcut_item(format_shortcut_for_display(f"{MODIFIER_KEY}+2"), "API Einstellungen"))
        content_layout.addWidget(system_card)

        # Preset Shortcuts
        preset_card = QWidget()
        preset_card.setObjectName("shortcut_card")
        preset_layout = QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(20, 16, 20, 16)
        preset_layout.setSpacing(10)

        preset_title = QLabel("Preset-Shortcuts")
        preset_title.setObjectName("card_title")
        preset_title.setFont(QFont(APP_FONT_FAMILY, 14, QFont.Weight.Bold))
        preset_layout.addWidget(preset_title)

        if shortcuts_dict and presets:
            for shortcut, idx in shortcuts_dict.items():
                if 0 <= idx < len(presets):
                    preset_name = presets[idx]["name"]
                    preset_layout.addWidget(self.create_shortcut_item(format_shortcut_for_display(shortcut), preset_name))
        else:
            no_shortcuts = QLabel("Keine Preset-Shortcuts definiert")
            no_shortcuts.setObjectName("section_subtitle")
            preset_layout.addWidget(no_shortcuts)

        content_layout.addWidget(preset_card)
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Close button
        close_btn = QPushButton("Schließen")
        close_btn.setObjectName("btn_primary")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(40)
        layout.addWidget(close_btn)

    def create_shortcut_item(self, shortcut, description):
        """Erstellt ein Shortcut-Item"""
        container = QWidget()
        container.setObjectName("shortcut_item")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        key_label = QLabel(shortcut)
        key_label.setObjectName("shortcut_key")
        key_label.setFont(QFont("SF Mono", 11, QFont.Weight.Medium))
        layout.addWidget(key_label)

        arrow = QLabel("→")
        arrow.setObjectName("shortcut_arrow")
        layout.addWidget(arrow)

        desc_label = QLabel(description)
        desc_label.setObjectName("shortcut_desc")
        layout.addWidget(desc_label, 1)

        return container


class APIManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self._platform = PLATFORM
        self.setWindowTitle("PromptPilot")
        # Erlaube eine größere Standardgröße und verhindere unnötiges Scrollen
        self.setMinimumSize(1200, 720)
        self.resize(1380, 860)

        # Backend frühzeitig initialisieren, damit Einstellungen gelesen werden können
        self.backend = APIBackend()

        self.global_hotkeys_supported = self._platform == "windows" and PYNPUT_AVAILABLE

        # Verwaltung von Shortcuts
        self.preset_shortcuts = {}
        self.preset_shortcut_actions = {}
        self.visibility_action = None

        # Globale Hotkey-Verwaltung (pynput)
        self._pynput_listener = None
        self._global_hotkey_map = {}
        self._shortcut_to_pynput = {}
        self._visibility_pynput_key = None

        # Sichtbarkeits-Shortcut Tracking
        self.visibility_shortcut_parsed = None
        self.visibility_shortcut_raw = None

        self._is_quitting = False
        self._close_to_tray_notified = False
        self.tray_icon = None
        self.tray_menu = None
        self.statusbar_app = None

        # Theme initialisieren (dark/light) aus Backend-Einstellungen
        self.current_theme = self.backend.get_setting('theme', 'dark')
        self.apply_stylesheets(self.current_theme)

        self.current_page_index = 0

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN)
        main_layout.setSpacing(SECTION_SPACING)

        self.create_top_nav()
        main_layout.addWidget(self.top_nav)

        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(SECTION_SPACING)

        self.create_sidebar()
        content_layout.addWidget(self.sidebar)

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("page_stack")

        self.home_page = HomePage(self)
        self.credentials_page = CredentialsPage(self)

        self.page_stack.addWidget(self.home_page)
        self.page_stack.addWidget(self.credentials_page)
        self.page_stack.setCurrentIndex(0)

        content_layout.addWidget(self.page_stack, 1)
        main_layout.addWidget(content_container, 1)

        # Prepare toast UI early so load_saved_shortcuts can call show_toast safely
        self.toast_label = QLabel(self)
        self.toast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toast_label.setObjectName("toast")
        self.toast_label.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.timeout.connect(self.hide_toast)

        # For improved visibility-shortcut handling install an application-level event filter
        # and keep a parsed representation of the visibility shortcut for consistent behaviour
        # across platforms.
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        # Lade und registriere gespeicherte Preset-Shortcuts
        self.load_saved_shortcuts()

        if self.global_hotkeys_supported and self._global_hotkey_map:
            # Start listener if es bereits registrierte Shortcuts gibt
            self._update_pynput_listener()

        self._tray_boot_message_shown = False
        if self._platform != "mac":
            self._setup_tray_icon()

    def start_hotkey_listener(self):
        """(deprecated) kept for compatibility"""
        pass

    def closeEvent(self, event):
        if self._is_quitting:
            super().closeEvent(event)
            return
        tray = self._current_tray_icon()
        if tray:
            event.ignore()
            self.hide()
            if not self._close_to_tray_notified:
                self._notify_tray(
                    "PromptPilot",
                    "PromptPilot läuft weiter in der Statusleiste.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4500,
                )
                self._close_to_tray_notified = True
        else:
            super().closeEvent(event)

    # ------------------------------------------------------------------
    # Status bar / tray helpers
    def attach_statusbar_app(self, status_app):
        self.statusbar_app = status_app

    def _current_tray_icon(self):
        if self.tray_icon and self.tray_icon.isVisible():
            return self.tray_icon
        if self.statusbar_app and getattr(self.statusbar_app, "tray_icon", None):
            tray = self.statusbar_app.tray_icon
            if tray and tray.isVisible():
                return tray
        return None

    def _notify_tray(self, title, message, icon, duration=4500):
        tray = self._current_tray_icon()
        if tray:
            tray.showMessage(title, message, icon, duration)

    def _setup_tray_icon(self):
        icon = self._load_tray_icon()
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("PromptPilot läuft im Hintergrund")
        self.tray_menu = QMenu()
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._handle_tray_activation)
        self.refresh_tray_menu()
        self.tray_icon.show()
        if not self._tray_boot_message_shown:
            self._notify_tray(
                "PromptPilot",
                "PromptPilot läuft im Hintergrund. Über das Statusleisten-Symbol kannst du Presets und Einstellungen öffnen.",
                QSystemTrayIcon.MessageIcon.Information,
                6000,
            )
            self._tray_boot_message_shown = True

    def refresh_tray_menu(self):
        if self.tray_menu:
            self.tray_menu.clear()
            presets = list(self.backend.presets)
            if presets:
                for idx, preset in enumerate(presets):
                    action = QAction(preset["name"], self)
                    action.triggered.connect(lambda _checked=False, i=idx: self.execute_preset_by_index(i))
                    self.tray_menu.addAction(action)
            else:
                placeholder = QAction("Keine Presets verfügbar", self)
                placeholder.setEnabled(False)
                self.tray_menu.addAction(placeholder)

            self.tray_menu.addSeparator()

            show_action = QAction("PromptPilot anzeigen", self)
            show_action.triggered.connect(self.show_window)
            self.tray_menu.addAction(show_action)

            presets_action = QAction("Preset Manager öffnen", self)
            presets_action.triggered.connect(self.open_preset_manager)
            self.tray_menu.addAction(presets_action)

            api_action = QAction("API Einstellungen öffnen", self)
            api_action.triggered.connect(self.open_api_settings)
            self.tray_menu.addAction(api_action)

            self.tray_menu.addSeparator()

            quit_action = QAction("Beenden", self)
            quit_action.triggered.connect(self._quit_from_tray)
            self.tray_menu.addAction(quit_action)

        if self.statusbar_app:
            self.statusbar_app.update_presets()

    def _load_tray_icon(self):
        for icon_name in ("promtpilot_icon.icns", "promtpilot_icon.png", "icon.icns", "icon.png"):
            icon_path = resource_path(icon_name)
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    return icon
        return self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

    def _handle_tray_activation(self, reason):
        if reason in {QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick}:
            self.show_window()

    def _quit_from_tray(self):
        self._is_quitting = True
        app = QApplication.instance()
        if app:
            app.quit()

    # Public helpers used by status bar integrations
    def show_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def open_preset_manager(self):
        self.show_window()
        self.change_page(0)

    def open_api_settings(self):
        self.show_window()
        self.change_page(1)

    def open_settings(self):
        self.open_preset_manager()

    def trigger_preset_by_index(self, index, shortcut_key: Optional[str] = None):
        """Safely trigger preset execution on the Qt main thread from background threads."""

        def _run(idx=index, key=shortcut_key):
            if key:
                self.on_preset_shortcut_triggered(idx, key)
            else:
                self.execute_preset_by_index(idx)

        try:
            # Use QTimer.singleShot with 0 ms to enqueue on the main thread
            QTimer.singleShot(0, _run)
        except Exception:
            # Last-resort: call directly
            try:
                _run()
            except Exception:
                pass

    def _read_clipboard_text(self, triggered_shortcut: Optional[str] = None) -> Optional[str]:
        """Liest Text aus der Zwischenablage und zeigt bei Fehlern einheitliche Hinweise an."""
        try:
            return pyperclip.paste()
        except Exception as exc:
            if triggered_shortcut:
                shortcut = format_shortcut_for_display(triggered_shortcut)
                toast = f"❌ {shortcut}: Zwischenablage konnte nicht gelesen werden"
                detail = f"{shortcut} konnte nicht ausgeführt werden: {exc}"
            else:
                toast = "❌ Zwischenablage konnte nicht gelesen werden"
                detail = f"Zwischenablage konnte nicht gelesen werden: {exc}"

            self.show_toast(toast)
            self._notify_tray(
                "Zwischenablage-Fehler",
                detail,
                QSystemTrayIcon.MessageIcon.Critical,
                5000
            )
            print(f"[DEBUG] Fehler beim Lesen der Zwischenablage: {exc}")
            return None

    def copy_to_clipboard(self, text: str, *, success_toast: Optional[str] = None, error_context: str = "Text") -> bool:
        """Kopiert Text in die Zwischenablage und behandelt Fehler konsistent."""
        try:
            pyperclip.copy(text)
        except Exception as exc:
            message = f"❌ {error_context} konnte nicht kopiert werden: {exc}"
            self.show_toast(message)
            self._notify_tray(
                "Zwischenablage-Fehler",
                message,
                QSystemTrayIcon.MessageIcon.Critical,
                4500
            )
            print(f"[DEBUG] Fehler beim Schreiben in die Zwischenablage: {exc}")
            return False

        if success_toast:
            self.show_toast(success_toast, 3000)
        return True

    def _convert_to_pynput_hotkey(self, qt_shortcut: str) -> str:
        """Convert a canonicalized Qt-like shortcut (e.g. 'Ctrl+Alt+Z') to a pynput GlobalHotKeys string ('<ctrl>+<alt>+z')."""
        if not qt_shortcut:
            return ""
        parts = [p.strip() for p in qt_shortcut.split('+') if p.strip()]
        if not parts:
            return ""

        mod_map = {
            'Ctrl': 'ctrl', 'Control': 'ctrl', 'Shift': 'shift', 'Alt': 'alt', 'Option': 'alt',
            'Meta': 'cmd', 'Cmd': 'cmd', 'AltGr': 'alt_gr'
        }

        tokens = []
        for p in parts[:-1]:
            low = mod_map.get(p, p).lower()
            # wrap standard modifiers
            if low in ('ctrl', 'shift', 'alt', 'cmd'):
                tokens.append(f"<{low}>")
            else:
                tokens.append(f"<{low}>")

        key = parts[-1]
        # single character keys -> lower
        if len(key) == 1:
            key_token = key.lower()
        else:
            # Named keys: try to map common ones
            named = {
                'Enter': 'enter', 'Return': 'enter', 'Space': 'space', 'Tab': 'tab',
                'Backspace': 'backspace', 'Delete': 'delete', 'Escape': 'esc',
                'Esc': 'esc'
            }
            key_token = named.get(key, key.lower())

        tokens.append(key_token)
        return '+'.join(tokens)

    def _update_pynput_listener(self):
        """Starts or restarts the pynput GlobalHotKeys listener with current _global_hotkey_map."""
        # Nur starten, wenn pynput verfügbar ist
        if not PYNPUT_AVAILABLE:
            return

        if not self.global_hotkeys_supported:
            return

        # Stop previous listener if running
        try:
            if self._pynput_listener:
                try:
                    self._pynput_listener.stop()
                except Exception:
                    pass
                self._pynput_listener = None
        except Exception:
            pass

        if not self._global_hotkey_map:
            return

        try:
            self._pynput_listener = _pynput_keyboard.GlobalHotKeys(self._global_hotkey_map)
            # run listener in a daemon thread
            threading.Thread(target=self._pynput_listener.start, daemon=True).start()
        except Exception as e:
            print(f"[DEBUG] Failed to start pynput listener: {e}", file=sys.stderr)

    def _register_global_hotkey(self, qt_shortcut: str, preset_index: int, canonical: str):
        """Adds or updates the mapping used by the pynput listener and restarts it."""
        # Wenn kein pynput vorhanden oder kein Shortcut-String, abbrechen
        if not PYNPUT_AVAILABLE or not qt_shortcut:
            return

        if not self.global_hotkeys_supported:
            return

        pynput_hotkey = self._convert_to_pynput_hotkey(qt_shortcut)
        if not pynput_hotkey:
            return

        # Build callback
        def make_callback(idx, shortcut):
            def _cb():
                try:
                    self.trigger_preset_by_index(idx, shortcut)
                except Exception:
                    pass
            return _cb

        # Remove existing mapping for the same canonical shortcut
        if canonical:
            existing_key = self._shortcut_to_pynput.get(canonical)
            if existing_key and existing_key in self._global_hotkey_map:
                try:
                    del self._global_hotkey_map[existing_key]
                except Exception:
                    pass

        # Store mapping and restart listener
        self._global_hotkey_map[pynput_hotkey] = make_callback(preset_index, canonical)
        if canonical:
            self._shortcut_to_pynput[canonical] = pynput_hotkey
        self._update_pynput_listener()

    def _register_visibility_global_hotkey(self, qt_shortcut: str):
        """Registriert den Sichtbarkeits-Shortcut auch global via pynput."""
        # Aufrufen nur, wenn pynput verfügbar ist und ein Shortcut gesetzt wurde
        if not PYNPUT_AVAILABLE or not qt_shortcut:
            return

        if not self.global_hotkeys_supported:
            return

        pynput_hotkey = self._convert_to_pynput_hotkey(qt_shortcut)
        if not pynput_hotkey:
            return

        # Entferne vorherigen Sichtbarkeits-Hotkey aus der Map
        if self._visibility_pynput_key and self._visibility_pynput_key in self._global_hotkey_map:
            try:
                del self._global_hotkey_map[self._visibility_pynput_key]
            except Exception:
                pass

        self._visibility_pynput_key = pynput_hotkey

        def _cb():
            try:
                QTimer.singleShot(0, self.toggle_visibility)
            except Exception:
                pass

        self._global_hotkey_map[pynput_hotkey] = _cb
        self._update_pynput_listener()

    def _unregister_visibility_global_hotkey(self):
        if not PYNPUT_AVAILABLE or not self.global_hotkeys_supported:
            return
        if self._visibility_pynput_key and self._visibility_pynput_key in self._global_hotkey_map:
            try:
                del self._global_hotkey_map[self._visibility_pynput_key]
            except Exception:
                pass
        self._visibility_pynput_key = None
        self._update_pynput_listener()

    def eventFilter(self, obj, event):
        # Intercept key events to handle visibility shortcut reliably while app is running.
        if event.type() == QEvent.Type.KeyPress and self.visibility_shortcut_parsed:
            mods_set, key_str = self.visibility_shortcut_parsed

            # Compare modifiers
            ev_mods = set()
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                ev_mods.add('Ctrl')
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                ev_mods.add('Shift')
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                ev_mods.add('Alt')
            if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
                ev_mods.add('Meta')

            # Key compare (letters/digits)
            key_name = None
            try:
                # Letters and digits: Qt.Key_A..Qt.Key_Z, Qt.Key_0..Qt.Key_9
                val = event.key()
                if Qt.Key_A <= val <= Qt.Key_Z:
                    key_name = chr(val)
                elif Qt.Key_0 <= val <= Qt.Key_9:
                    key_name = chr(val)
                else:
                    # Fallback: map common keys
                    common = {
                        Qt.Key_Return: 'Enter', Qt.Key_Enter: 'Enter', Qt.Key_Space: 'Space', Qt.Key_Tab: 'Tab',
                        Qt.Key_Backspace: 'Backspace', Qt.Key_Delete: 'Delete', Qt.Key_Escape: 'Escape'
                    }
                    key_name = common.get(val, None)
            except Exception:
                key_name = None

            if key_name:
                # Normalize to uppercase single-char if necessary
                if len(key_name) == 1:
                    key_name = key_name.upper()

                if ev_mods == mods_set and key_name == key_str:
                    # Trigger toggle and consume event
                    try:
                        self.toggle_visibility()
                    except Exception:
                        pass
                    return True

        return super().eventFilter(obj, event)

    def create_top_nav(self):
        self.top_nav = QWidget()
        self.top_nav.setObjectName("top_nav")
        self.top_nav.setFixedHeight(64)

        layout = QHBoxLayout(self.top_nav)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(SECTION_SPACING)

        title = QLabel("PromptPilot")
        title.setObjectName("app_title")
        title.setFont(QFont(APP_FONT_FAMILY, 22, QFont.Weight.Bold))
        layout.addWidget(title)

        # Separator
        separator = QFrame()
        separator.setObjectName("top_nav_separator")
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFixedWidth(1)
        separator.setFixedHeight(30)
        layout.addWidget(separator)

        layout.addStretch()

        # Shortcut Overview Button
        shortcuts_btn = QPushButton("Shortcuts")
        shortcuts_btn.setObjectName("btn_ghost")
        shortcuts_btn.setToolTip("Zeige alle verfügbaren Shortcuts")
        shortcuts_btn.setMinimumHeight(36)
        shortcuts_btn.clicked.connect(self.show_shortcuts_overview)
        layout.addWidget(shortcuts_btn)

        # Sichtbarkeit-Shortcut Button (öffnet Dialog zum Setzen)
        vis_btn = QPushButton("Visibility Shortcut")
        vis_btn.setObjectName("btn_ghost")
        vis_btn.setMinimumHeight(36)
        vis_btn.setToolTip("Shortcut zum Anzeigen/Verstecken der App setzen")
        vis_btn.clicked.connect(self.set_visibility_shortcut)
        layout.addWidget(vis_btn)

        # Theme-Umschalter
        theme_btn = QPushButton("Theme")
        theme_btn.setObjectName("btn_ghost")
        theme_btn.setMinimumHeight(36)
        theme_btn.setToolTip("Wechsle zwischen Dark und Light Mode")
        theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(theme_btn)

    def create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(260)

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(SECTION_SPACING)

        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(16, 18, 16, 18)
        nav_layout.setSpacing(CONTROL_SPACING)

        nav_label = QLabel("NAVIGATION")
        nav_label.setObjectName("nav_label")
        nav_label.setFont(QFont(APP_FONT_FAMILY, 11, QFont.Weight.Bold))
        nav_layout.addWidget(nav_label)

        nav_layout.addSpacing(8)

        self.nav_presets = self.create_nav_button("Presets", 0)
        self.nav_credentials = self.create_nav_button("API Einstellungen", 1)

        nav_layout.addWidget(self.nav_presets)
        nav_layout.addWidget(self.nav_credentials)
        nav_layout.addStretch()

        layout.addWidget(nav_container)

        self.nav_presets.setProperty("active", True)
        self.nav_presets.style().unpolish(self.nav_presets)
        self.nav_presets.style().polish(self.nav_presets)

        bottom = QWidget()
        bottom.setObjectName("sidebar_bottom")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(20, 18, 20, 18)

        info = QLabel("PromptPilot v2.0")
        info.setObjectName("sidebar_info")
        info.setFont(QFont(APP_FONT_FAMILY, 10))
        bottom_layout.addWidget(info)

        authors = QLabel("by Cian & Malik")
        authors.setObjectName("sidebar_authors")
        authors.setFont(QFont(APP_FONT_FAMILY, 9))
        bottom_layout.addWidget(authors)

        layout.addWidget(bottom)

    def create_nav_button(self, text, page):
        btn = QPushButton(text)
        btn.setObjectName("nav_button")
        btn.setFixedHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(f"Wechsle zu {text} ({MODIFIER_KEY_DISPLAY}+{page + 1})")
        btn.clicked.connect(lambda: self.change_page(page))
        return btn

    def change_page(self, page_index):
        if page_index == self.current_page_index:
            return
        self.page_stack.setCurrentIndex(page_index)
        self.update_nav_buttons(page_index)
        self.current_page_index = page_index

    def update_nav_buttons(self, active_index):
        self.nav_presets.setProperty("active", active_index == 0)
        self.nav_credentials.setProperty("active", active_index == 1)

        self.nav_presets.style().unpolish(self.nav_presets)
        self.nav_presets.style().polish(self.nav_presets)
        self.nav_credentials.style().unpolish(self.nav_credentials)
        self.nav_credentials.style().polish(self.nav_credentials)

    def setup_shortcuts(self):
        # Keine festen Navigation-Shortcuts mehr. Nutzer kann eigene Shortcuts
        # für Presets und die Sichtbarkeit setzen.
        return
    def load_saved_shortcuts(self):
        """Lädt beim Start alle in presets.json gespeicherten Shortcuts und registriert sie."""
        for idx, preset in enumerate(self.backend.presets):
            shortcut = preset.get('shortcut', '')
            if not shortcut:
                continue
            try:
                canonical = canonicalize_shortcut(shortcut)
            except ValueError:
                continue
            self.register_preset_shortcut(canonical, idx, silent=True)

        # Sichtbarkeits-Shortcut aus Einstellungen laden
        vis = self.backend.get_setting('show_shortcut', '')
        if vis:
            self.register_visibility_shortcut(vis, silent=True)

    def reload_shortcuts(self):
        """Entfernt alle registrierten Preset-Shortcuts und lädt sie aus der Persistenz neu."""
        for action in list(self.preset_shortcut_actions.values()):
            try:
                self.removeAction(action)
            except Exception:
                pass
        self.preset_shortcut_actions.clear()
        self.preset_shortcuts.clear()

        if self.global_hotkeys_supported:
            if self._pynput_listener:
                try:
                    self._pynput_listener.stop()
                except Exception:
                    pass
                self._pynput_listener = None
            self._global_hotkey_map.clear()
            self._shortcut_to_pynput.clear()
            self._visibility_pynput_key = None

        self.load_saved_shortcuts()

    def _unregister_global_hotkey(self, shortcut_key: str):
        if not PYNPUT_AVAILABLE or not self.global_hotkeys_supported or not shortcut_key:
            return
        pynput_key = self._shortcut_to_pynput.pop(shortcut_key, None)
        if pynput_key and pynput_key in self._global_hotkey_map:
            try:
                del self._global_hotkey_map[pynput_key]
            except Exception:
                pass
            self._update_pynput_listener()

    def register_preset_shortcut(self, shortcut_key, preset_index, *, silent: bool = False):
        """Registriert einen Shortcut für ein Preset mit korrekter QKeySequence-Unterstützung"""
        if not shortcut_key:
            return False

        try:
            canonical = canonicalize_shortcut(shortcut_key)
        except ValueError as exc:
            if not silent:
                self.show_toast(str(exc))
            return False

        existing = self.preset_shortcuts.get(canonical)
        if existing is not None and existing != preset_index:
            if not silent:
                conflict = self.backend.presets[existing]["name"] if existing < len(self.backend.presets) else "anderes Preset"
                self.show_toast(f"⚠️ Shortcut bereits vergeben ({format_shortcut_for_display(canonical)} → {conflict})")
            return False

        # Entferne alte Shortcuts für dieses Preset
        for key, idx in list(self.preset_shortcuts.items()):
            if idx == preset_index and key != canonical:
                if key in self.preset_shortcut_actions:
                    try:
                        self.removeAction(self.preset_shortcut_actions[key])
                    except Exception:
                        pass
                    del self.preset_shortcut_actions[key]
                del self.preset_shortcuts[key]
                self._unregister_global_hotkey(key)

        qt_shortcut = canonicalize_shortcut_for_qt(canonical)
        print(f"[DEBUG] Registriere Shortcut: {canonical} -> QKeySequence: {qt_shortcut}")

        # Entferne evtl. vorhandene Action (z.B. gleiche Kombination)
        if canonical in self.preset_shortcut_actions:
            try:
                self.removeAction(self.preset_shortcut_actions[canonical])
            except Exception:
                pass

        action = QAction(self)
        action.setShortcut(QKeySequence(qt_shortcut))
        action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        action.triggered.connect(lambda idx=preset_index, key=canonical: self.on_preset_shortcut_triggered(idx, key))
        self.addAction(action)

        self.preset_shortcuts[canonical] = preset_index
        self.preset_shortcut_actions[canonical] = action

        print(f"[DEBUG] Shortcut registriert. Aktive Shortcuts: {self.preset_shortcuts}")
        if not silent:
            self.show_toast(f"✓ Shortcut {format_shortcut_for_display(canonical)} aktiviert")

        # Wenn pynput verfügbar, registriere denselben Shortcut global
        try:
            qt_shortcut = canonicalize_shortcut_for_qt(canonical)
            self._register_global_hotkey(qt_shortcut, preset_index, canonical)
        except Exception:
            pass

        return True

    def toggle_theme(self):
        """Wechselt zwischen Dark und Light Mode und speichert die Einstellung"""
        new_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self.current_theme = new_theme
        # Persistiere Einstellung
        try:
            self.backend.set_setting('theme', new_theme)
        except Exception:
            pass
        self.apply_stylesheets(new_theme)
        self.show_toast(f"Theme: {new_theme}")

    def set_visibility_shortcut(self):
        """Zeigt Dialog zum Setzen eines Shortcuts um die App sichtbar/unsichtbar zu machen."""
        dialog = ShortcutDialog(self, self.backend.get_setting('show_shortcut', ''))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            shortcut = dialog.get_shortcut()
            if shortcut:
                if shortcut in self.preset_shortcuts:
                    conflict = self.preset_shortcuts[shortcut]
                    if conflict < len(self.backend.presets):
                        name = self.backend.presets[conflict]["name"]
                    else:
                        name = "Preset"
                    self.show_toast(f"⚠️ Shortcut kollidiert mit '{name}'")
                    return

                if self.backend.set_setting('show_shortcut', shortcut):
                    if self.register_visibility_shortcut(shortcut):
                        self.show_toast(f"Visibility Shortcut gesetzt: {format_shortcut_for_display(shortcut)}")
                    else:
                        self.backend.set_setting('show_shortcut', '')
                        self.show_toast("Shortcut konnte nicht registriert werden")
                else:
                    self.show_toast("Fehler beim Speichern des Shortcuts")

    def register_visibility_shortcut(self, shortcut_key, *, silent: bool = False):
        """Registriert den Shortcut, der die App zeigt/versteckt."""
        if not shortcut_key:
            return False

        try:
            canonical = canonicalize_shortcut(shortcut_key)
        except ValueError as exc:
            if not silent:
                self.show_toast(str(exc))
            return False

        if canonical in self.preset_shortcuts:
            if not silent:
                conflict_idx = self.preset_shortcuts[canonical]
                conflict = self.backend.presets[conflict_idx]["name"] if conflict_idx < len(self.backend.presets) else "Preset"
                self.show_toast(f"⚠️ Shortcut bereits als Preset genutzt ({format_shortcut_for_display(canonical)} → {conflict})")
            return False

        # Entferne alte Aktion wenn vorhanden
        if hasattr(self, 'visibility_action') and getattr(self, 'visibility_action'):
            try:
                self.removeAction(self.visibility_action)
            except Exception:
                pass

        # Entferne auch ggf. registrierten globalen Sichtbarkeits-Hotkey,
        # bevor ein neuer gesetzt wird.
        self._unregister_visibility_global_hotkey()

        qt_shortcut = canonicalize_shortcut_for_qt(canonical)

        # Keep parsed representation to match key events in the eventFilter
        parts = [p.strip() for p in canonical.split('+') if p.strip()]
        if parts:
            mods = set(parts[:-1])
            key = parts[-1]
            self.visibility_shortcut_parsed = (mods, key)
            self.visibility_shortcut_raw = canonical

        action = QAction(self)
        try:
            action.setShortcut(QKeySequence(qt_shortcut))
            action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
            action.triggered.connect(self.toggle_visibility)
            self.addAction(action)
            self.visibility_action = action
        except Exception:
            # Fallback: still store parsed shortcut and rely on eventFilter
            self.visibility_action = None

        try:
            self._register_visibility_global_hotkey(qt_shortcut)
        except Exception:
            pass

        return True

    def toggle_visibility(self):
        """Zeigt/versteckt das Hauptfenster."""
        if self.isVisible() and not self.isActiveWindow():
            # Falls sichtbar aber nicht aktiv, bringe es nach vorne
            self.show()
            self.activateWindow()
        elif self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def show_shortcuts_overview(self):
        dialog = ShortcutOverviewDialog(self, self.preset_shortcuts, self.backend.presets)
        dialog.exec()


    def on_preset_shortcut_triggered(self, preset_index, shortcut_key):
        """Wird aufgerufen wenn ein Preset-Shortcut gedrückt wird"""
        print(f"[DEBUG] ============================================")
        print(f"[DEBUG] Shortcut {shortcut_key} ausgelöst für Preset {preset_index}")
        print(f"[DEBUG] ============================================")

        if preset_index < 0 or preset_index >= len(self.backend.presets):
            self.show_toast("❌ Preset nicht gefunden")
            self._notify_tray(
                "Preset nicht gefunden",
                f"Der Shortcut {format_shortcut_for_display(shortcut_key)} verweist auf ein unbekanntes Preset.",
                QSystemTrayIcon.MessageIcon.Critical,
                4000
            )
            print(f"[DEBUG] Fehler: Preset-Index {preset_index} außerhalb des Bereichs")
            return

        preset = self.backend.presets[preset_index]
        print(f"[DEBUG] Preset gefunden: {preset['name']}")

        clipboard_text = self._read_clipboard_text(triggered_shortcut=shortcut_key)
        if clipboard_text is None:
            return
        print(f"[DEBUG] Zwischenablage gelesen: {len(clipboard_text) if clipboard_text else 0} Zeichen")

        if not clipboard_text:
            self.show_toast(f"ℹ️ Zwischenablage ist leer")
            print(f"[DEBUG] Zwischenablage ist leer")
            # Zeige System-Benachrichtigung
            self._notify_tray(
                "Zwischenablage leer",
                f"Kopiere zuerst einen Text, dann drücke {format_shortcut_for_display(shortcut_key)}",
                QSystemTrayIcon.MessageIcon.Warning,
                5000
            )
            return

        print(f"[DEBUG] Starte Preset-Verarbeitung...")
        self.show_toast(f"⚙️ Verarbeite mit '{preset['name']}'...")
        self.home_page.show_loading()
        QTimer.singleShot(
            100,
            lambda p=preset, text=clipboard_text, key=shortcut_key: self._execute_preset_async(p, text, key)
        )

    def execute_preset_by_index(self, preset_index):
        if preset_index < 0 or preset_index >= len(self.backend.presets):
            self.show_toast("Preset nicht gefunden")
            return

        preset = self.backend.presets[preset_index]
        clipboard_text = self._read_clipboard_text()
        if clipboard_text is None:
            return

        if not clipboard_text:
            self.show_toast("Zwischenablage ist leer")
            return

        self.show_toast(f"Verarbeite mit '{preset['name']}'...")
        self.home_page.show_loading()
        QTimer.singleShot(100, lambda p=preset, text=clipboard_text: self._execute_preset_async(p, text))

    def _execute_preset_async(self, preset, clipboard_text, triggered_shortcut: Optional[str] = None):
        """Führt das Preset asynchron aus"""
        print(f"[DEBUG] Starte Preset-Ausführung: {preset['name']}")
        result = self.backend.execute_preset(preset["name"], clipboard_text)

        if result.get("status") == "success":
            response = result.get("response", "")
            self.copy_to_clipboard(
                response,
                success_toast="✅ Fertig! Ergebnis kopiert",
                error_context=f"Ergebnis von '{preset['name']}'"
            )
            self.home_page.show_result(preset["name"], clipboard_text, response)

            # Show system notification if via Shortcut oder Fenster minimiert
            if triggered_shortcut or self.isMinimized():
                shortcut_info = ""
                if triggered_shortcut:
                    shortcut_info = f" ({format_shortcut_for_display(triggered_shortcut)})"
                self._notify_tray(
                    "✅ Preset abgeschlossen",
                    f"'{preset['name']}'{shortcut_info} wurde erfolgreich ausgeführt. Ergebnis befindet sich in der Zwischenablage.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3500
                )
        else:
            error_msg = result.get("message", "Unbekannter Fehler")
            print(f"[DEBUG] Fehler bei Preset-Ausführung: {error_msg}")
            self.show_toast(f"❌ Fehler: {error_msg}", 3000)
            self.home_page.show_error(error_msg)
            if triggered_shortcut or self.isMinimized():
                shortcut_info = ""
                if triggered_shortcut:
                    shortcut_info = f" ({format_shortcut_for_display(triggered_shortcut)})"
                self._notify_tray(
                    "❌ Preset fehlgeschlagen",
                    f"'{preset['name']}'{shortcut_info} konnte nicht ausgeführt werden: {error_msg}",
                    QSystemTrayIcon.MessageIcon.Critical,
                    4000
                )

    def show_toast(self, message, duration=2000):
        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        self.toast_label.move(
            (self.width() - self.toast_label.width()) // 2,
            self.height() - self.toast_label.height() - 40
        )
        self.toast_label.show()
        self.toast_timer.start(duration)

    def hide_toast(self):
        self.toast_label.hide()
        self.toast_timer.stop()

    def apply_stylesheets(self, theme='dark'):
        """Wendet Stylesheet und Palette für das gewählte Theme an (dark/light)."""
        accent = "#007aff"
        success = "#34c759"
        danger = "#ff3b30"
        font_stack = f"'{APP_FONT_FAMILY}', 'SF Pro Text', 'SF Pro Display', '-apple-system', 'Helvetica Neue', 'Segoe UI', sans-serif"

        QApplication.setStyle("Fusion")
        app = QApplication.instance()

        if theme == 'dark':
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(28, 28, 30))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
            palette.setColor(QPalette.ColorRole.Base, QColor(44, 44, 46))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(58, 58, 60))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(240, 240, 240))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(12, 12, 12))
            palette.setColor(QPalette.ColorRole.Text, QColor(245, 245, 247))
            palette.setColor(QPalette.ColorRole.Button, QColor(44, 44, 46))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(245, 245, 247))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Link, QColor(0, 122, 255))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 255))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            if app:
                app.setPalette(palette)
            self.setPalette(palette)

            base_styles = f"""
                QWidget {{ background-color: #1c1c1e; color: #f5f5f7; font-family: {font_stack}; }}
                #top_nav {{ background-color: rgba(28,28,30,0.92); border-bottom: 1px solid rgba(255,255,255,0.08); border-radius: 18px; }}
                #top_nav QLabel#app_title {{ color: #f5f5f7; letter-spacing: 0.2px; }}
                #top_nav_separator {{ background-color: rgba(255,255,255,0.12); width: 1px; }}
                #sidebar {{ background-color: #2c2c2e; border: 1px solid rgba(255,255,255,0.05); border-radius: 20px; }}
                #sidebar_info, #sidebar_authors {{ color: rgba(255,255,255,0.55); }}
                #sidebar_bottom {{ background-color: transparent; border-top: 1px solid rgba(255,255,255,0.06); border-radius: 14px; }}
                QPushButton#nav_button {{ background: transparent; border: none; color: rgba(255,255,255,0.72); text-align: left; padding: 10px 16px; border-radius: 12px; }}
                QPushButton#nav_button[active="true"] {{ background-color: rgba(255,255,255,0.12); color: #ffffff; font-weight: 600; }}
                QPushButton#nav_button:hover {{ background-color: rgba(255,255,255,0.08); }}
                .content_card, .preset_card, .shortcut_card, #result_panel {{ background-color: rgba(44,44,46,0.9); border-radius: 18px; border: 1px solid rgba(255,255,255,0.08); }}
                #page_stack {{ background: transparent; }}
                QPushButton#btn_primary {{ background-color: {accent}; color: #ffffff; }}
                QPushButton#btn_primary:hover {{ background-color: #0a84ff; }}
                QPushButton#btn_secondary {{ background-color: rgba(255,255,255,0.12); color: #f5f5f7; }}
                QPushButton#btn_secondary:hover {{ background-color: rgba(255,255,255,0.2); }}
                QPushButton#btn_success {{ background-color: {success}; color: #0b0b0c; }}
                QPushButton#btn_danger {{ background-color: {danger}; color: #ffffff; }}
                QPushButton#btn_warning {{ background-color: rgba(255, 204, 0, 0.3); color: #ffe066; }}
                QPushButton#btn_ghost {{ background-color: transparent; color: {accent}; padding: 6px 12px; border-radius: 10px; }}
                QPushButton#btn_ghost:hover {{ background-color: rgba(255,255,255,0.08); }}
                QLineEdit, QTextEdit, QComboBox, QKeySequenceEdit {{ background: rgba(58,58,60,0.95); border: 1px solid rgba(255,255,255,0.12); color: #f5f5f7; border-radius: 12px; selection-background-color: {accent}; selection-color: #ffffff; }}
                QLineEdit[error="true"], QTextEdit[error="true"], QKeySequenceEdit[error="true"] {{ border: 1px solid {danger}; }}
                QLabel#section_title {{ color: #ffffff; }}
                QLabel#section_subtitle {{ color: rgba(255,255,255,0.65); }}
                QLabel#input_label {{ color: rgba(255,255,255,0.82); font-weight: 600; letter-spacing: 0.2px; }}
                QLabel#hint_text {{ color: rgba(255,255,255,0.55); font-size: 13px; }}
                QLabel#error_label {{ color: {danger}; font-size: 13px; }}
                QLabel#preset_header {{ color: #ffffff; font-size: 16px; font-weight: 600; }}
                QLabel#preset_meta, QLabel#presets_counter {{ color: rgba(255,255,255,0.55); font-size: 12px; }}
                QLabel#preset_prompt {{ color: rgba(255,255,255,0.85); }}
                QLabel#shortcut_badge {{ background-color: rgba(255,255,255,0.12); color: #ffffff; border-radius: 999px; padding: 4px 12px; font-weight: 600; }}
                QLabel#toast {{ background: rgba(0,0,0,0.8); color: #ffffff; padding: 12px 20px; border-radius: 14px; font-weight: 600; }}
                QLabel#shortcut_key {{ color: #f5f5f7; font-family: 'JetBrains Mono', 'SF Mono', monospace; font-weight: 600; }}
                QLabel#shortcut_desc {{ color: rgba(255,255,255,0.65); }}
                QWidget#shortcut_item {{ background-color: rgba(58,58,60,0.9); border-radius: 14px; border: 1px solid rgba(255,255,255,0.04); }}
                QWidget#empty_state {{ background: transparent; color: rgba(255,255,255,0.6); }}
                QScrollArea#preset_scroll {{ border: none; background: transparent; }}
                QSplitter::handle:horizontal {{ width: 2px; background: rgba(255,255,255,0.08); }}
                QKeySequenceEdit#shortcut_input {{ color: #f5f5f7; }}
                QFrame#section_divider {{ background-color: rgba(255,255,255,0.12); max-height: 1px; min-height: 1px; }}
            """
        else:
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(245, 246, 248))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(28, 28, 30))
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(242, 242, 247))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(28, 28, 30))
            palette.setColor(QPalette.ColorRole.Text, QColor(28, 28, 30))
            palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(28, 28, 30))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(0, 0, 0))
            palette.setColor(QPalette.ColorRole.Link, QColor(0, 122, 255))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 255))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            if app:
                app.setPalette(palette)
            self.setPalette(palette)

            base_styles = f"""
                QWidget {{ background-color: #f5f5f7; color: #1c1c1e; font-family: {font_stack}; }}
                #top_nav {{ background-color: rgba(255,255,255,0.9); border-bottom: 1px solid rgba(60,60,67,0.12); border-radius: 18px; }}
                #top_nav QLabel#app_title {{ color: #1c1c1e; letter-spacing: 0.2px; }}
                #top_nav_separator {{ background-color: rgba(60,60,67,0.18); width: 1px; }}
                #sidebar {{ background-color: #ffffff; border: 1px solid rgba(60,60,67,0.12); border-radius: 20px; }}
                #sidebar_info, #sidebar_authors {{ color: rgba(60,60,67,0.6); }}
                #sidebar_bottom {{ background-color: rgba(250,250,252,0.8); border-top: 1px solid rgba(60,60,67,0.08); border-radius: 14px; }}
                QPushButton#nav_button {{ background: transparent; border: none; color: rgba(28,28,30,0.8); text-align: left; padding: 10px 16px; border-radius: 12px; }}
                QPushButton#nav_button[active="true"] {{ background-color: rgba(0,122,255,0.12); color: #0a84ff; font-weight: 600; }}
                QPushButton#nav_button:hover {{ background-color: rgba(0,0,0,0.05); }}
                .content_card, .preset_card, .shortcut_card, #result_panel {{ background-color: #ffffff; border-radius: 18px; border: 1px solid rgba(60,60,67,0.12); }}
                #page_stack {{ background: transparent; }}
                QPushButton#btn_primary {{ background-color: {accent}; color: #ffffff; }}
                QPushButton#btn_primary:hover {{ background-color: #0a84ff; }}
                QPushButton#btn_secondary {{ background-color: rgba(60,60,67,0.08); color: #1c1c1e; }}
                QPushButton#btn_secondary:hover {{ background-color: rgba(60,60,67,0.14); }}
                QPushButton#btn_success {{ background-color: {success}; color: #ffffff; }}
                QPushButton#btn_danger {{ background-color: {danger}; color: #ffffff; }}
                QPushButton#btn_warning {{ background-color: rgba(255,149,0,0.28); color: #c93400; }}
                QPushButton#btn_ghost {{ background-color: transparent; color: {accent}; padding: 6px 12px; border-radius: 10px; }}
                QPushButton#btn_ghost:hover {{ background-color: rgba(0,122,255,0.08); }}
                QLineEdit, QTextEdit, QComboBox, QKeySequenceEdit {{ background: #ffffff; border: 1px solid rgba(60,60,67,0.18); color: #1c1c1e; border-radius: 12px; selection-background-color: {accent}; selection-color: #ffffff; }}
                QLineEdit[error="true"], QTextEdit[error="true"], QKeySequenceEdit[error="true"] {{ border: 1px solid {danger}; }}
                QLabel#section_title {{ color: #111; }}
                QLabel#section_subtitle {{ color: rgba(60,60,67,0.75); }}
                QLabel#input_label {{ color: rgba(28,28,30,0.9); font-weight: 600; letter-spacing: 0.2px; }}
                QLabel#hint_text {{ color: rgba(60,60,67,0.6); font-size: 13px; }}
                QLabel#error_label {{ color: {danger}; font-size: 13px; }}
                QLabel#preset_header {{ color: #111; font-size: 16px; font-weight: 600; }}
                QLabel#preset_meta, QLabel#presets_counter {{ color: rgba(60,60,67,0.6); font-size: 12px; }}
                QLabel#preset_prompt {{ color: rgba(28,28,30,0.78); }}
                QLabel#shortcut_badge {{ background-color: rgba(0,122,255,0.12); color: #0a84ff; border-radius: 999px; padding: 4px 12px; font-weight: 600; }}
                QLabel#toast {{ background: rgba(28,28,30,0.85); color: #ffffff; padding: 12px 20px; border-radius: 14px; font-weight: 600; }}
                QLabel#shortcut_key {{ color: #111; font-family: 'JetBrains Mono', 'SF Mono', monospace; font-weight: 600; }}
                QLabel#shortcut_desc {{ color: rgba(28,28,30,0.6); }}
                QWidget#shortcut_item {{ background-color: rgba(0,0,0,0.03); border-radius: 14px; border: 1px solid rgba(60,60,67,0.08); }}
                QWidget#empty_state {{ background: transparent; color: rgba(60,60,67,0.55); }}
                QScrollArea#preset_scroll {{ border: none; background: transparent; }}
                QSplitter::handle:horizontal {{ width: 2px; background: rgba(60,60,67,0.12); }}
                QKeySequenceEdit#shortcut_input {{ color: #1c1c1e; }}
                QFrame#section_divider {{ background-color: rgba(60,60,67,0.15); max-height: 1px; min-height: 1px; }}
            """

        common = f"""
            * {{ font-family: {font_stack}; font-size: 13px; }}
            QPushButton {{ border: none; border-radius: 12px; font-weight: 600; padding: 10px 18px; }}
            QLineEdit, QComboBox, QTextEdit, QKeySequenceEdit {{ padding: 10px 14px; font-size: 13px; }}
            QTextEdit {{ padding: 12px 14px; }}
        """

        try:
            self.setStyleSheet(base_styles + common)
        except Exception:
            self.setStyleSheet(common)

    @property
    def api_credentials(self):
        return self.backend.api_credentials

    @property
    def presets(self):
        return self.backend.presets


class BasePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = parent
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN)
        self.main_layout.setSpacing(SECTION_SPACING + 4)


class HomePage(BasePage):
    """Aufgeräumte HomePage: Liste, Suche, Form zum Erstellen, Result-Panel."""

    def __init__(self, parent):
        super().__init__(parent)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Preset-Liste + Suche
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(SECTION_SPACING)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        title = QLabel("Meine Presets")
        title.setObjectName("section_title")
        title.setFont(QFont(APP_FONT_FAMILY, 28, QFont.Weight.Bold))
        header_layout.addWidget(title)
        subtitle = QLabel("Erstelle, verwalte und nutze deine API-Prompts")
        subtitle.setObjectName("section_subtitle")
        subtitle.setFont(QFont(APP_FONT_FAMILY, 14))
        header_layout.addWidget(subtitle)
        left_layout.addLayout(header_layout)

        # Suche + Preset-Liste in einem Card-Container
        library_card = QWidget()
        library_card.setObjectName("content_card")
        library_layout = QVBoxLayout(library_card)
        library_layout.setSpacing(SECTION_SPACING)
        library_layout.setContentsMargins(24, 24, 24, 24)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(CONTROL_SPACING)
        search_label = QLabel("Suche")
        search_label.setObjectName("input_label")
        header_row.addWidget(search_label)
        header_row.addStretch()
        self.preset_count_label = QLabel("")
        self.preset_count_label.setObjectName("presets_counter")
        header_row.addWidget(self.preset_count_label)
        library_layout.addLayout(header_row)
        library_layout.addWidget(create_section_divider())

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nach Name oder Prompt suchen...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_presets)
        library_layout.addWidget(self.search_input)

        self.presets_scroll = QScrollArea()
        self.presets_scroll.setObjectName("preset_scroll")
        self.presets_scroll.setWidgetResizable(True)
        self.presets_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.presets_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(16)
        self.presets_layout.setContentsMargins(0, 0, 0, 0)
        self.presets_scroll.setWidget(self.presets_container)
        library_layout.addWidget(self.presets_scroll, 1)

        left_layout.addWidget(library_card, 1)
        self.main_splitter.addWidget(left_widget)

        # RIGHT: Form + Result
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(SECTION_SPACING)

        # Form zum Erstellen
        form_card = QWidget()
        form_card.setObjectName("content_card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(SECTION_SPACING)
        form_title = QLabel("Neues Preset erstellen")
        form_title.setObjectName("section_title")
        form_title.setFont(QFont(APP_FONT_FAMILY, 18, QFont.Weight.Bold))
        form_layout.addWidget(form_title)

        name_label = QLabel("Preset-Name")
        name_label.setObjectName("input_label")
        form_layout.addWidget(name_label)
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("z.B. Text Zusammenfassung")
        self.preset_name_input.textChanged.connect(self.validate_form)
        self.preset_name_input.setMaxLength(MAX_PRESET_NAME_STORE)
        form_layout.addWidget(self.preset_name_input)
        self.name_error_label = QLabel("")
        self.name_error_label.setObjectName("error_label")
        self.name_error_label.hide()
        form_layout.addWidget(self.name_error_label)

        prompt_label = QLabel("Prompt-Text")
        prompt_label.setObjectName("input_label")
        form_layout.addWidget(prompt_label)
        self.preset_prompt_input = QTextEdit()
        self.preset_prompt_input.setPlaceholderText("Schreibe deinen Prompt hier...")
        self.preset_prompt_input.setAcceptRichText(False)
        self.preset_prompt_input.setFixedHeight(120)
        self.preset_prompt_input.textChanged.connect(self.validate_form)
        form_layout.addWidget(self.preset_prompt_input)
        self.prompt_error_label = QLabel("")
        self.prompt_error_label.setObjectName("error_label")
        self.prompt_error_label.hide()
        form_layout.addWidget(self.prompt_error_label)

        form_layout.addWidget(create_section_divider())

        provider_label = QLabel("Provider")
        provider_label.setObjectName("input_label")
        form_layout.addWidget(provider_label)
        self.provider_models_map = self.controller.backend.provider_models()
        self.provider_combo = QComboBox()
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        form_layout.addWidget(self.provider_combo)

        model_label = QLabel("Modell")
        model_label.setObjectName("input_label")
        form_layout.addWidget(model_label)
        self.model_combo = QComboBox()
        form_layout.addWidget(self.model_combo)
        self.populate_provider_options()

        form_layout.addWidget(create_section_divider())

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(CONTROL_SPACING)
        reset_btn = QPushButton("Zurücksetzen")
        reset_btn.setObjectName("btn_secondary")
        reset_btn.setFixedHeight(44)
        reset_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(reset_btn)
        save_btn = QPushButton("Preset Speichern")
        save_btn.setObjectName("btn_success")
        save_btn.setFixedHeight(44)
        save_btn.setFont(QFont(APP_FONT_FAMILY, 14, QFont.Weight.Bold))
        save_btn.clicked.connect(self.save_new_preset)
        btn_layout.addWidget(save_btn, 1)
        form_layout.addLayout(btn_layout)
        right_layout.addWidget(form_card)

        # Result-Panel
        self.result_card = QWidget()
        self.result_card.setObjectName("result_panel")
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(24, 24, 24, 24)
        result_layout.setSpacing(SECTION_SPACING)
        result_header = QLabel("Ergebnis")
        result_header.setObjectName("section_title")
        result_header.setFont(QFont(APP_FONT_FAMILY, 16, QFont.Weight.Bold))
        result_layout.addWidget(result_header)
        result_layout.addWidget(create_section_divider())
        self.result_content = QTextEdit()
        self.result_content.setReadOnly(True)
        self.result_content.setPlaceholderText("Das Ergebnis der API-Anfrage wird hier angezeigt...")
        result_layout.addWidget(self.result_content, 1)
        result_btn_layout = QHBoxLayout()
        result_btn_layout.setSpacing(CONTROL_SPACING)
        clear_result_btn = QPushButton("Löschen")
        clear_result_btn.setObjectName("btn_secondary")
        clear_result_btn.clicked.connect(self.clear_result)
        result_btn_layout.addWidget(clear_result_btn)
        copy_btn = QPushButton("In Zwischenablage kopieren")
        copy_btn.setObjectName("btn_primary")
        copy_btn.clicked.connect(self.copy_result)
        result_btn_layout.addWidget(copy_btn, 1)
        result_layout.addLayout(result_btn_layout)
        self.result_card.hide()
        right_layout.addWidget(self.result_card, 1)

        self.main_splitter.addWidget(right_widget)
        self.main_splitter.setStretchFactor(0, 6)
        self.main_splitter.setStretchFactor(1, 4)
        self.main_splitter.setSizes([700, 500])
        self.main_layout.addWidget(self.main_splitter)

        self.current_search = ""
        self.update_presets_list()
    # --- Formular-Validierung ---
    def validate_form(self):
        name = self.preset_name_input.text().strip()
        prompt = self.preset_prompt_input.toPlainText().strip()

        if not name:
            self.name_error_label.setText("Name ist erforderlich")
            self.name_error_label.show()
            self.preset_name_input.setProperty("error", True)
        elif len(name) < 3:
            self.name_error_label.setText("Name muss mindestens 3 Zeichen haben")
            self.name_error_label.show()
            self.preset_name_input.setProperty("error", True)
        else:
            self.name_error_label.hide()
            self.preset_name_input.setProperty("error", False)

        if not prompt:
            self.prompt_error_label.setText("Prompt ist erforderlich")
            self.prompt_error_label.show()
            self.preset_prompt_input.setProperty("error", True)
        elif len(prompt) < 10:
            self.prompt_error_label.setText("Prompt sollte mindestens 10 Zeichen haben")
            self.prompt_error_label.show()
            self.preset_prompt_input.setProperty("error", True)
        else:
            self.prompt_error_label.hide()
            self.preset_prompt_input.setProperty("error", False)

        self.preset_name_input.style().unpolish(self.preset_name_input)
        self.preset_name_input.style().polish(self.preset_name_input)
        self.preset_prompt_input.style().unpolish(self.preset_prompt_input)
        self.preset_prompt_input.style().polish(self.preset_prompt_input)

    def populate_provider_options(self):
        self.provider_models_map = self.controller.backend.provider_models()
        providers = list(self.provider_models_map.keys()) or ["OpenAI"]
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        self.provider_combo.addItems(providers)
        self.provider_combo.blockSignals(False)
        self.on_provider_changed(self.provider_combo.currentText())

    def on_provider_changed(self, provider: str):
        models = self.provider_models_map.get(provider, [])
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)
        else:
            self.model_combo.addItem("")

    # --- Preset Verarbeitung / UI ---
    def show_loading(self):
        self.result_card.show()
        self.result_content.setPlainText("Verarbeite Anfrage...\n\nBitte warten...")

    def show_result(self, preset_name, input_text, result):
        self.result_card.show()
        output = f"PRESET\n{preset_name}\n\nEINGABE\n{input_text}\n\nERGEBNIS\n{result}"
        self.result_content.setPlainText(output)

    def show_error(self, error_msg):
        self.result_card.show()
        self.result_content.setPlainText(f"FEHLER\n\n{error_msg}")

    def copy_result(self):
        text = self.result_content.toPlainText()
        if not text:
            return

        controller = getattr(self, 'controller', None)
        if controller and hasattr(controller, 'copy_to_clipboard'):
            controller.copy_to_clipboard(
                text,
                success_toast="In Zwischenablage kopiert",
                error_context="Ergebnis-Text"
            )
        else:
            try:
                pyperclip.copy(text)
            except Exception:
                pass

    def clear_result(self):
        self.result_content.clear()
        self.result_card.hide()

    # --- Preset-Liste ---
    def update_presets_list(self):
        # Alle Widgets entfernen
        for i in reversed(range(self.presets_layout.count())):
            item = self.presets_layout.takeAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        presets = self.controller.presets
        filtered = [(i, p) for i, p in enumerate(presets) if not self.current_search or
                    self.current_search.lower() in p["name"].lower() or
                    self.current_search.lower() in p["prompt"].lower()]

        total = len(filtered)
        if hasattr(self, 'preset_count_label'):
            if total == 0:
                self.preset_count_label.setText("Keine Presets")
            elif total == 1:
                self.preset_count_label.setText("1 Preset")
            else:
                self.preset_count_label.setText(f"{total} Presets")

        if not filtered:
            empty = QWidget()
            empty.setObjectName("empty_state")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(16)
            empty_title = QLabel("Keine Presets gefunden")
            empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_title.setFont(QFont(APP_FONT_FAMILY, 18, QFont.Weight.Bold))
            empty_title.setStyleSheet("color: #6c757d;")
            empty_layout.addWidget(empty_title)
            empty_text = QLabel("Erstelle dein erstes Preset mit dem Formular")
            empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_text.setObjectName("section_subtitle")
            empty_layout.addWidget(empty_text)
            self.presets_layout.addWidget(empty)
            self.presets_layout.addStretch()
            return

        for idx, preset in filtered:
            self.presets_layout.addWidget(self.create_preset_widget(idx, preset))

        self.presets_layout.addStretch()

    def filter_presets(self, text: str):
        """Filtert die Preset-Liste basierend auf der Sucheingabe."""
        self.current_search = text.strip()
        self.update_presets_list()

    def save_new_preset(self):
        """Speichert ein neues Preset über das Backend nach Validierung."""
        name = self.preset_name_input.text().strip()
        prompt = self.preset_prompt_input.toPlainText().strip()
        provider = self.provider_combo.currentText() or "OpenAI"
        model = self.model_combo.currentText() or ""
        api_type = provider

        if not name:
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast("Name ist erforderlich")
            return
        if len(name) < 3:
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast("Name zu kurz")
            return
        if not prompt or len(prompt) < 10:
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast("Prompt zu kurz")
            return

        success = self.controller.backend.save_preset(name, prompt, api_type, provider, model)
        if success:
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast(f"Preset '{name}' gespeichert")
            self.clear_form()
            self.update_presets_list()
            if hasattr(self.controller, "refresh_tray_menu"):
                self.controller.refresh_tray_menu()
        else:
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast("Fehler: Preset konnte nicht gespeichert werden (evtl. Name bereits vorhanden)")

    def resolve_preset_provider_model(self, preset):
        provider, model = self.controller.backend.resolve_preset_target(preset)
        if not provider:
            provider = preset.get("api_type", "")
        return provider, model or ""

    def create_preset_widget(self, index, preset):
        card = QWidget()
        card.setObjectName("preset_card")
        layout = QVBoxLayout(card)
        layout.setSpacing(SECTION_SPACING)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(SECTION_SPACING)

        title_box = QWidget()
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        original_name = preset["name"]
        display_name = original_name
        if len(display_name) > MAX_PRESET_NAME_LENGTH:
            display_name = original_name[:MAX_PRESET_NAME_LENGTH - 1] + "…"
        title = QLabel(display_name)
        title.setObjectName("preset_header")
        if display_name != original_name:
            title.setToolTip(original_name)
        title_layout.addWidget(title)
        provider, model = self.resolve_preset_provider_model(preset)
        meta_text = provider or preset.get("api_type", "")
        if model:
            meta_text = f"{provider} • {model}" if provider else model
        meta = QLabel(f"API: {meta_text}")
        meta.setObjectName("preset_meta")
        title_layout.addWidget(meta)
        shortcut_value = preset.get("shortcut")
        if shortcut_value:
            badge = QLabel(format_shortcut_for_display(shortcut_value))
            badge.setObjectName("shortcut_badge")
            title_layout.addWidget(badge)
        header_layout.addWidget(title_box, 1)

        btn_box = QWidget()
        btn_layout_h = QHBoxLayout(btn_box)
        btn_layout_h.setContentsMargins(0, 0, 0, 0)
        btn_layout_h.setSpacing(CONTROL_SPACING)

        # Shortcut Button
        shortcut_btn = QPushButton("Shortcut")
        shortcut_btn.setObjectName("btn_secondary")
        shortcut_btn.setToolTip("Tastenkombination festlegen")
        shortcut_btn.setMinimumWidth(100)
        shortcut_btn.setFixedHeight(40)
        shortcut_btn.clicked.connect(lambda idx=index: self.set_shortcut(idx))
        btn_layout_h.addWidget(shortcut_btn)

        # Edit Button
        edit_btn = QPushButton("Bearbeiten")
        edit_btn.setObjectName("btn_warning")
        edit_btn.setToolTip("Preset bearbeiten")
        edit_btn.setMinimumWidth(110)
        edit_btn.setFixedHeight(40)
        edit_btn.clicked.connect(lambda idx=index: self.edit_preset(idx))
        btn_layout_h.addWidget(edit_btn)

        # Execute Button
        use_btn = QPushButton("Ausführen")
        use_btn.setObjectName("btn_primary")
        use_btn.setMinimumWidth(120)
        use_btn.setFixedHeight(40)
        use_btn.setToolTip("Preset mit Zwischenablage ausführen")
        use_btn.clicked.connect(lambda idx=index: self.controller.execute_preset_by_index(idx))
        btn_layout_h.addWidget(use_btn)

        # Delete Button
        delete_btn = QPushButton("Löschen")
        delete_btn.setObjectName("btn_danger")
        delete_btn.setMinimumWidth(95)
        delete_btn.setFixedHeight(40)
        delete_btn.setToolTip("Preset entfernen")
        delete_btn.clicked.connect(lambda idx=index: self.delete_preset(idx))
        btn_layout_h.addWidget(delete_btn)

        header_layout.addWidget(btn_box)
        layout.addWidget(header)

        prompt = preset["prompt"]
        truncated_prompt = prompt
        if len(prompt) > 180:
            truncated_prompt = prompt[:180].rstrip() + "…"

        prompt_label = QLabel(truncated_prompt)
        prompt_label.setObjectName("preset_prompt")
        prompt_label.setWordWrap(True)
        if truncated_prompt != prompt:
            prompt_label.setToolTip(prompt)
        layout.addWidget(prompt_label)

        return card

    def set_shortcut(self, index):
        dialog = ShortcutDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            shortcut = dialog.get_shortcut()
            if shortcut:
                existing = self.controller.preset_shortcuts.get(shortcut)
                if existing is not None and existing != index:
                    if hasattr(self.controller, 'show_toast'):
                        if existing < len(self.controller.backend.presets):
                            name = self.controller.backend.presets[existing]["name"]
                        else:
                            name = "Preset"
                        self.controller.show_toast(f"⚠️ Shortcut bereits vergeben an '{name}'")
                    return
                # Persistiere Shortcut im Backend und registriere danach
                if self.controller.backend.save_preset_shortcut(index, shortcut):
                    # Registrierung im Controller
                    if hasattr(self.controller, 'register_preset_shortcut'):
                        success = self.controller.register_preset_shortcut(shortcut, index)
                        if not success:
                            # Revert gespeicherten Shortcut
                            self.controller.backend.save_preset_shortcut(index, "")
                            if hasattr(self.controller, 'show_toast'):
                                self.controller.show_toast("Shortcut konnte nicht registriert werden")
                        else:
                            self.update_presets_list()
                else:
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast("Fehler beim Speichern des Shortcuts")

    def edit_preset(self, index):
        if 0 <= index < len(self.controller.presets):
            preset = self.controller.presets[index]
            provider, model = self.resolve_preset_provider_model(preset)
            preset_with_defaults = dict(preset)
            preset_with_defaults.setdefault("provider", provider)
            preset_with_defaults.setdefault("model", model)
            dialog = EditPresetDialog(self, preset_with_defaults, provider_models=self.provider_models_map)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if not data["name"] or not data["prompt"]:
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast("Name und Prompt erforderlich")
                    return
                if self.controller.backend.update_preset_by_index(index, data["name"], data["prompt"], data["api_type"], data.get("provider"), data.get("model")):
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast(f"Preset '{data['name']}' aktualisiert")
                    self.update_presets_list()
                    if hasattr(self.controller, "refresh_tray_menu"):
                        self.controller.refresh_tray_menu()
                else:
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast("Fehler beim Aktualisieren")

    def delete_preset(self, index):
        if 0 <= index < len(self.controller.presets):
            p = self.controller.presets[index]
            reply = QMessageBox.question(self, "Preset löschen",
                                         f"Möchtest du das Preset '{p['name']}' wirklich löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.controller.backend.delete_preset_by_index(index):
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast(f"'{p['name']}' gelöscht")
                    if hasattr(self.controller, 'reload_shortcuts'):
                        self.controller.reload_shortcuts()
                    self.update_presets_list()
                    if hasattr(self.controller, "refresh_tray_menu"):
                        self.controller.refresh_tray_menu()
                else:
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast("Fehler beim Löschen")

    def clear_form(self):
        self.preset_name_input.clear()
        self.preset_prompt_input.clear()
        self.populate_provider_options()
        self.name_error_label.hide()
        self.prompt_error_label.hide()
        self.preset_name_input.setProperty("error", False)
        self.preset_prompt_input.setProperty("error", False)
        self.preset_name_input.style().unpolish(self.preset_name_input)
        self.preset_name_input.style().polish(self.preset_name_input)
        self.preset_prompt_input.style().unpolish(self.preset_prompt_input)
        self.preset_prompt_input.style().polish(self.preset_prompt_input)


class CredentialsPage(BasePage):
    def __init__(self, parent):
        super().__init__(parent)

        title = QLabel("API Einstellungen")
        title.setObjectName("section_title")
        title.setFont(QFont(APP_FONT_FAMILY, 28, QFont.Weight.Bold))
        self.main_layout.addWidget(title)

        subtitle = QLabel("Konfiguriere deine API-Zugangsdaten")
        subtitle.setObjectName("section_subtitle")
        subtitle.setFont(QFont(APP_FONT_FAMILY, 14))
        self.main_layout.addWidget(subtitle)

        # API Key Card
        api_card = QWidget()
        api_card.setObjectName("content_card")
        api_layout = QVBoxLayout(api_card)
        api_layout.setContentsMargins(24, 24, 24, 24)
        api_layout.setSpacing(SECTION_SPACING)

        provider_label = QLabel("Provider")
        provider_label.setObjectName("input_label")
        api_layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(self.controller.backend.list_providers())
        self.provider_combo.currentTextChanged.connect(self.load_credentials)
        api_layout.addWidget(self.provider_combo)

        key_label = QLabel("API-Key")
        key_label.setObjectName("input_label")
        api_layout.addWidget(key_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("API-Key einfügen")
        api_layout.addWidget(self.api_key_input)

        hint = QLabel("Hinterlege den API-Key deines gewählten Providers.")
        hint.setObjectName("hint_text")
        api_layout.addWidget(hint)
        api_layout.addWidget(create_section_divider())

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(CONTROL_SPACING)

        test_btn = QPushButton("Verbindung testen")
        test_btn.setObjectName("btn_secondary")
        test_btn.setToolTip("Testet die API-Verbindung")
        test_btn.setMinimumHeight(44)
        test_btn.clicked.connect(self.test_api)
        btn_layout.addWidget(test_btn)

        save_btn = QPushButton("API-Key speichern")
        save_btn.setObjectName("btn_success")
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self.save_credentials)
        btn_layout.addWidget(save_btn, 1)

        api_layout.addLayout(btn_layout)

        self.status_label = QLabel("")
        self.status_label.setObjectName("section_subtitle")
        api_layout.addWidget(self.status_label)

        self.main_layout.addWidget(api_card)
        self.main_layout.addStretch()

        self.load_credentials()

    def load_credentials(self):
        provider = self.provider_combo.currentText()
        creds = self.controller.api_credentials
        key = creds.get(provider)
        if key:
            self.api_key_input.setText(key)
            self.status_label.setText("API-Key gespeichert")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
        else:
            self.api_key_input.clear()
            self.status_label.setText("")

    def save_credentials(self):
        api_key = self.api_key_input.text().strip()
        provider = self.provider_combo.currentText() or "OpenAI"
        if not api_key:
            self.controller.show_toast("Bitte API-Key eingeben")
            return

        if self.controller.backend.save_credentials(api_key, provider):
            self.controller.show_toast("API-Key gespeichert")
            self.status_label.setText("Gespeichert")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
        else:
            self.controller.show_toast("Fehler beim Speichern")

    def test_api(self):
        api_key = self.api_key_input.text().strip()
        provider = self.provider_combo.currentText() or "OpenAI"
        if not api_key:
            self.controller.show_toast("Bitte API-Key eingeben")
            return

        self.controller.backend.save_credentials(api_key, provider)

        self.status_label.setText("Teste Verbindung...")
        self.status_label.setStyleSheet("color: #58a6ff; font-weight: 600;")
        QApplication.processEvents()

        result = self.controller.backend.test_credential(provider)

        if result.get("status") == "success":
            self.status_label.setText("Verbindung erfolgreich!")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
            self.controller.show_toast("API-Test erfolgreich")
        else:
            error = result.get("message", "Unbekannter Fehler")
            self.status_label.setText(f"Fehler: {error}")
            self.status_label.setStyleSheet("color: #f85149; font-weight: 600;")
            self.controller.show_toast("API-Test fehlgeschlagen")


def launch_app():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PromptPilot")
    app.setOrganizationName("Cian & Malik")
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("SF Pro Text", 13))

    refresh_app_font_family()

    window = APIManager()
    window.hide()

    status_app = None
    if PLATFORM == "mac":
        from mac_statusbar import MacStatusBarApp  # lazy import to avoid platform issues

        status_app = MacStatusBarApp(window.backend, window)
        window.attach_statusbar_app(status_app)

    return app.exec()


def main():
    sys.exit(launch_app())


if __name__ == "__main__":
    main()
