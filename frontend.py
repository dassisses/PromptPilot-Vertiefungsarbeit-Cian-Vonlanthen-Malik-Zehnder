import sys
import pyperclip
import threading
try:
    from pynput import keyboard as _pynput_keyboard
    PYNPUT_AVAILABLE = True
except Exception:
    _pynput_keyboard = None
    PYNPUT_AVAILABLE = False
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QFont, QAction, QKeySequence, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFrame, QScrollArea, QMessageBox, QStackedWidget,
    QTextEdit, QDialog, QSplitter,

    QSystemTrayIcon, QMenu, QStyle
)
from backend import APIBackend


# ===== HELPER FUNCTIONS (müssen vor den Klassen definiert sein) =====

# New UI / behavior constants
MAX_PRESET_NAME_LENGTH = 30  # displayed length before truncation
MAX_PRESET_NAME_STORE = 60   # max length allowed for storing names
EDIT_BUTTON_COLOR = "#7c3aed"  # violet-ish instead of yellow for the edit button


def is_valid_shortcut(shortcut_str: str, platform: str = None) -> tuple:
    """
    Validiert einen Shortcut-String.
    Returniert (is_valid, error_message)
    """
    if platform is None:
        platform = sys.platform

    if not shortcut_str or not shortcut_str.strip():
        return False, "Shortcut darf nicht leer sein"

    shortcut_str = shortcut_str.strip()

    # Erlaubte Modifier und Keys
    # Entferne 'Cmd' als erlaubte Eingabe (problematisch auf manchen Systemen)
    valid_modifiers = {"Ctrl", "Control", "Shift", "Alt", "Option", "Meta", "AltGr"}
    valid_keys = {
        # Function keys
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
        # Letter keys
        *[chr(i) for i in range(ord('A'), ord('Z') + 1)],
        *[str(i) for i in range(10)],
        # Special keys
        "Return", "Enter", "Space", "Tab", "Backspace", "Delete", "Escape",
        "Home", "End", "PageUp", "PageDown", "Left", "Right", "Up", "Down",
        "Insert", "Pause", "Print", "ScrollLock", "CapsLock", "NumLock",
        "+", "-", "*", "/", "=", "[", "]", "{", "}", ";", ":", "'", '"',
        ",", ".", "<", ">", "?", "/", "\\", "|", "`", "~", "!", "@", "#",
        "$", "%", "^", "&"
    }

    # Parse shortcut
    parts = shortcut_str.split("+")
    if len(parts) < 2:
        return False, "Shortcut benötigt mindestens einen Modifier (z.B. Ctrl+T, Control+Alt+P)"

    modifiers = [m.strip() for m in parts[:-1]]
    key = parts[-1].strip()

    # Validiere Modifiers
    for mod in modifiers:
        if mod not in valid_modifiers:
            allowed = ", ".join(sorted(valid_modifiers))
            return False, f"Ungültiger Modifier: '{mod}'. Erlaubt: {allowed}"

    # Validiere Key
    if key not in valid_keys:
        return False, f"Ungültiger Key: '{key}'"

    # Grundlegende Plausibilitätschecks (plattformunabhängig, redundanz-safe)
    if len(modifiers) == 1 and modifiers[0] in {"Alt", "Option"}:
        # Option/Alt alleine ist oft nicht ideal — nur als Warnung (aber wir lassen es zu)
        return True, ""

    return True, ""


def normalize_shortcut_for_platform(shortcut_str: str, platform: str = None) -> str:
    """
    Normalisiert einen Shortcut-String (benutzerfreundliche Synonyme) für Speicherung.
    Ersetzt z.B. 'Control' -> 'Ctrl', 'Option' -> 'Alt' usw.
    """
    if platform is None:
        platform = sys.platform

    s = shortcut_str.strip()

    # Vereinheitliche Synonyme
    s = s.replace('Control', 'Ctrl')
    s = s.replace('Option', 'Alt')
    s = s.replace('AltGr', 'AltGr')
    # Falls jemand noch 'Cmd' schreibt, wandeln wir es intern zu 'Meta' (aber 'Cmd' wird nicht in valid_modifiers angeboten)
    s = s.replace('Cmd', 'Meta')

    if platform != 'darwin':
        # Auf Windows/Linux: Meta (wenn vorhanden) ist in der Regel Ctrl
        s = s.replace('Meta', 'Ctrl')

    return s


def canonicalize_shortcut_for_qt(shortcut_str: str, platform: str = None) -> str:
    """
    Erzeugt eine Qt-kompatible Shortcut-Notation aus einer vom Nutzer eingegebenen Shortcut-Notation.
    - Normalisiert Synonyme (Control->Ctrl, Option->Alt)
    - Auf macOS: lässt Meta als Meta (Qt erwartet 'Meta' für Command)
    - Auf Windows/Linux: wandelt Meta -> Ctrl
    """
    if platform is None:
        platform = sys.platform

    parts = [p.strip() for p in shortcut_str.split('+') if p.strip()]
    if not parts:
        return shortcut_str

    modifiers = parts[:-1]
    key = parts[-1]

    map_mod = {
        'Control': 'Ctrl', 'Ctrl': 'Ctrl', 'Shift': 'Shift',
        'Alt': 'Alt', 'Option': 'Alt', 'AltGr': 'AltGr',
        'Meta': 'Meta', 'Cmd': 'Meta'
    }

    canonical_mods = []
    for m in modifiers:
        canonical_mods.append(map_mod.get(m, m))

    # Plattform-spezifische Anpassungen
    if platform == 'darwin':
        # Auf macOS: Qt erwartet 'Meta' für Command und 'Alt' für Option. Wir belassen 'Meta' unverändert.
        pass
    else:
        # Auf Windows/Linux: Meta -> Ctrl
        canonical_mods = ['Ctrl' if m == 'Meta' else m for m in canonical_mods]

    return "+".join(canonical_mods + [key])


# Platform-specific modifier key (Anzeige / Tooltip)
def get_modifier_key():
    """Returns 'Meta' for macOS, 'Ctrl' for Windows/Linux"""
    return "Meta" if sys.platform == "darwin" else "Ctrl"

MODIFIER_KEY = get_modifier_key()
MODIFIER_KEY_DISPLAY = "⌘" if sys.platform == "darwin" else "Ctrl"


class EditPresetDialog(QDialog):
    """Dialog zum Bearbeiten eines bestehenden Presets"""

    def __init__(self, parent=None, preset_data=None):
        super().__init__(parent)
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

        # API Type
        api_label = QLabel("API-Typ")
        api_label.setObjectName("input_label")
        layout.addWidget(api_label)

        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["ChatGPT", "GPT-4", "GPT-3.5-Turbo"])
        self.api_type_combo.setMinimumHeight(40)
        if preset_data:
            api_type = preset_data.get("api_type", "ChatGPT")
            index = self.api_type_combo.findText(api_type)
            if index >= 0:
                self.api_type_combo.setCurrentIndex(index)
        layout.addWidget(self.api_type_combo)

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
            "api_type": self.api_type_combo.currentText()
        }


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
        info_label.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        layout.addWidget(info_label)

        desc = QLabel("Definiere eine Tastenkombination für schnellen Zugriff")
        desc.setObjectName("section_subtitle")
        layout.addWidget(desc)

        self.shortcut_input = QLineEdit()
        self.shortcut_input.setText(current_shortcut)
        # Avoid suggesting 'Cmd' as user input — suggest platform-agnostic names
        if sys.platform == "darwin":
            self.shortcut_input.setPlaceholderText("z.B. Control+Shift+T oder Option+Shift+T")
        else:
            self.shortcut_input.setPlaceholderText("z.B. Ctrl+Shift+T")
        layout.addWidget(self.shortcut_input)

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
        shortcut = self.shortcut_input.text().strip()

        if not shortcut:
            self.show_error("Shortcut darf nicht leer sein")
            return

        # Validiere Shortcut
        is_valid, error_msg = is_valid_shortcut(shortcut)

        if not is_valid:
            self.show_error(error_msg)
            return

        # Normalisiere für Plattform
        normalized = normalize_shortcut_for_platform(shortcut)
        self.shortcut_input.setText(normalized)

        self.accept()

    def show_error(self, message):
        """Zeigt einen Fehler an"""
        self.error_label.setText(message)
        self.error_label.show()
        self.shortcut_input.setProperty("error", True)
        self.shortcut_input.style().unpolish(self.shortcut_input)
        self.shortcut_input.style().polish(self.shortcut_input)

    def get_shortcut(self):
        return self.shortcut_input.text().strip()


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
        title.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
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
        system_title.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        system_layout.addWidget(system_title)

        system_layout.addWidget(self.create_shortcut_item("Ctrl+1", "Presets-Seite"))
        system_layout.addWidget(self.create_shortcut_item("Ctrl+2", "API Einstellungen"))
        content_layout.addWidget(system_card)

        # Preset Shortcuts
        preset_card = QWidget()
        preset_card.setObjectName("shortcut_card")
        preset_layout = QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(20, 16, 20, 16)
        preset_layout.setSpacing(10)

        preset_title = QLabel("Preset-Shortcuts")
        preset_title.setObjectName("card_title")
        preset_title.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        preset_layout.addWidget(preset_title)

        if shortcuts_dict and presets:
            for shortcut, idx in shortcuts_dict.items():
                if 0 <= idx < len(presets):
                    preset_name = presets[idx]["name"]
                    preset_layout.addWidget(self.create_shortcut_item(shortcut, preset_name))
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
        self.setWindowTitle("PromptPilot")
        # Fenster auf feste Größe setzen (nicht veränderbar)
        self.setFixedSize(1200, 700)

        # Backend frühzeitig initialisieren, damit Einstellungen gelesen werden können
        self.backend = APIBackend()
        # Verwaltung von Shortcuts
        self.preset_shortcuts = {}
        self.preset_shortcut_actions = {}
        self.visibility_action = None

        # Tray Icon Setup
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        tray_menu = QMenu()
        restore_action = QAction("Wiederherstellen", self)
        restore_action.triggered.connect(self.show)
        tray_menu.addAction(restore_action)

        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Theme initialisieren (dark/light) aus Backend-Einstellungen
        self.current_theme = self.backend.get_setting('theme', 'dark')
        self.apply_stylesheets(self.current_theme)

        self.current_page_index = 0

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.create_top_nav()
        main_layout.addWidget(self.top_nav)

        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

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
        # and keep a parsed representation of the visibility shortcut. This ensures a single
        # visibility shortcut is tracked and handled consistently.
        self.visibility_shortcut_parsed = None  # (set(modifiers_str), key_str)
        self.visibility_shortcut_raw = None
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        # Lade und registriere gespeicherte Preset-Shortcuts
        self.load_saved_shortcuts()

        # Prepare pynput global hotkey structures
        self._pynput_listener = None
        self._global_hotkey_map = {}
        if PYNPUT_AVAILABLE:
            # Start listener if there are already shortcuts
            self._update_pynput_listener()

    def start_hotkey_listener(self):
        """(deprecated) kept for compatibility"""
        pass

    def trigger_preset_by_index(self, index):
        """Safely trigger preset execution on the Qt main thread from background threads."""
        try:
            # Use QTimer.singleShot with 0 ms to enqueue on the main thread
            QTimer.singleShot(0, lambda idx=index: self.execute_preset_by_index(idx))
        except Exception:
            # Last-resort: call directly
            try:
                self.execute_preset_by_index(index)
            except Exception:
                pass

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
        if not PYNPUT_AVAILABLE:
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

    def _register_global_hotkey(self, qt_shortcut: str, preset_index: int):
        """Adds or updates the mapping used by the pynput listener and restarts it."""
        if not PYNPUT_AVAILABLE or not qt_shortcut:
            return

        pynput_hotkey = self._convert_to_pynput_hotkey(qt_shortcut)
        if not pynput_hotkey:
            return

        # Build callback
        def make_callback(idx):
            def _cb():
                try:
                    self.trigger_preset_by_index(idx)
                except Exception:
                    pass
            return _cb

        # Store mapping and restart listener
        self._global_hotkey_map[pynput_hotkey] = make_callback(preset_index)
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
        self.top_nav.setFixedHeight(60)

        layout = QHBoxLayout(self.top_nav)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(16)

        title = QLabel("PromptPilot")
        title.setObjectName("app_title")
        title.setFont(QFont("SF Pro Display", 22, QFont.Weight.Bold))
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(20, 24, 20, 24)
        nav_layout.setSpacing(8)

        nav_label = QLabel("NAVIGATION")
        nav_label.setObjectName("nav_label")
        nav_label.setFont(QFont("SF Pro Display", 11, QFont.Weight.Bold))
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
        bottom_layout.setContentsMargins(20, 16, 20, 16)

        info = QLabel("PromptPilot v2.0")
        info.setObjectName("sidebar_info")
        info.setFont(QFont("SF Pro Display", 10))
        bottom_layout.addWidget(info)

        authors = QLabel("by Cian & Malik")
        authors.setObjectName("sidebar_authors")
        authors.setFont(QFont("SF Pro Display", 9))
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
            if shortcut:
                self.register_preset_shortcut(shortcut, idx)

        # Sichtbarkeits-Shortcut aus Einstellungen laden
        vis = self.backend.get_setting('show_shortcut', '')
        if vis:
            self.register_visibility_shortcut(vis)

    def register_preset_shortcut(self, shortcut_key, preset_index):
        """Registriert einen Shortcut für ein Preset mit korrekter QKeySequence-Unterstützung"""
        if not shortcut_key:
            return

        # Entferne alte Shortcuts für dieses Preset
        for key, idx in list(self.preset_shortcuts.items()):
            if idx == preset_index:
                if key in self.preset_shortcut_actions:
                    self.removeAction(self.preset_shortcut_actions[key])
                    del self.preset_shortcut_actions[key]
                del self.preset_shortcuts[key]

        # Normalize and canonicalize for QKeySequence
        normalized = normalize_shortcut_for_platform(shortcut_key)
        qt_shortcut = canonicalize_shortcut_for_qt(normalized)

        print(f"[DEBUG] Registriere Shortcut: {shortcut_key} -> QKeySequence: {qt_shortcut}")

        # Erstelle die Action
        action = QAction(self)
        action.setShortcut(QKeySequence(qt_shortcut))
        action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        action.triggered.connect(lambda idx=preset_index, key=shortcut_key: self.on_preset_shortcut_triggered(idx, key))
        self.addAction(action)

        self.preset_shortcuts[shortcut_key] = preset_index
        self.preset_shortcut_actions[shortcut_key] = action

        print(f"[DEBUG] Shortcut registriert. Aktive Shortcuts: {self.preset_shortcuts}")
        self.show_toast(f"✓ Shortcut {shortcut_key} aktiviert")

        # Wenn pynput verfügbar, registriere denselben Shortcut global
        try:
            normalized = normalize_shortcut_for_platform(shortcut_key)
            qt_shortcut = canonicalize_shortcut_for_qt(normalized)
            # For global hotkeys we want a pynput-compatible string
            self._register_global_hotkey(qt_shortcut, preset_index)
        except Exception:
            pass

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
                if self.backend.set_setting('show_shortcut', shortcut):
                    # (Re-)registriere Shortcut
                    self.register_visibility_shortcut(shortcut)
                    self.show_toast(f"Visibility Shortcut gesetzt: {shortcut}")
                else:
                    self.show_toast("Fehler beim Speichern des Shortcuts")

    def register_visibility_shortcut(self, shortcut_key):
        """Registriert den Shortcut, der die App zeigt/versteckt."""
        # Entferne alte Aktion wenn vorhanden
        if hasattr(self, 'visibility_action') and getattr(self, 'visibility_action'):
            try:
                self.removeAction(self.visibility_action)
            except Exception:
                pass

        # Normalize and canonicalize for QKeySequence
        normalized = normalize_shortcut_for_platform(shortcut_key)
        qt_shortcut = canonicalize_shortcut_for_qt(normalized)

        # Keep parsed representation to match key events in the eventFilter
        parts = [p.strip() for p in qt_shortcut.split('+') if p.strip()]
        if parts:
            mods = set(parts[:-1])
            key = parts[-1]
            self.visibility_shortcut_parsed = (mods, key)
            self.visibility_shortcut_raw = qt_shortcut

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
            print(f"[DEBUG] Fehler: Preset-Index {preset_index} außerhalb des Bereichs")
            return

        preset = self.backend.presets[preset_index]
        print(f"[DEBUG] Preset gefunden: {preset['name']}")

        try:
            clipboard_text = pyperclip.paste()
            print(f"[DEBUG] Zwischenablage gelesen: {len(clipboard_text) if clipboard_text else 0} Zeichen")
        except Exception as e:
            self.show_toast(f"❌ Fehler beim Lesen der Zwischenablage: {str(e)}")
            print(f"[DEBUG] Fehler beim Lesen der Zwischenablage: {e}")
            return

        if not clipboard_text:
            self.show_toast(f"ℹ️ Zwischenablage ist leer")
            print(f"[DEBUG] Zwischenablage ist leer")
            # Zeige System-Benachrichtigung
            self.tray_icon.showMessage(
                "Zwischenablage leer",
                f"Kopiere zuerst einen Text, dann drücke {shortcut_key}",
                QSystemTrayIcon.MessageIcon.Warning,
                5000
            )
            return

        print(f"[DEBUG] Starte Preset-Verarbeitung...")
        self.show_toast(f"⚙️ Verarbeite mit '{preset['name']}'...")
        self.home_page.show_loading()
        QTimer.singleShot(100, lambda: self._execute_preset_async(preset, clipboard_text))

    def execute_preset_by_index(self, preset_index):
        if preset_index < 0 or preset_index >= len(self.backend.presets):
            self.show_toast("Preset nicht gefunden")
            return

        preset = self.backend.presets[preset_index]
        clipboard_text = pyperclip.paste()

        if not clipboard_text:
            self.show_toast("Zwischenablage ist leer")
            return

        self.show_toast(f"Verarbeite mit '{preset['name']}'...")
        self.home_page.show_loading()
        QTimer.singleShot(100, lambda: self._execute_preset_async(preset, clipboard_text))

    def _execute_preset_async(self, preset, clipboard_text):
        """Führt das Preset asynchron aus"""
        print(f"[DEBUG] Starte Preset-Ausführung: {preset['name']}")
        result = self.backend.execute_preset(preset["name"], clipboard_text)

        if result.get("status") == "success":
            response = result.get("response", "")
            pyperclip.copy(response)
            self.show_toast("✅ Fertig! Ergebnis kopiert", 3000)
            self.home_page.show_result(preset["name"], clipboard_text, response)

            # Show system notification if minimized
            if self.isMinimized():
                self.tray_icon.showMessage(
                    "✅ Preset abgeschlossen",
                    f"Das Preset '{preset['name']}' wurde erfolgreich ausgeführt.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )
        else:
            error_msg = result.get("message", "Unbekannter Fehler")
            print(f"[DEBUG] Fehler bei Preset-Ausführung: {error_msg}")
            self.show_toast(f"❌ Fehler: {error_msg}", 3000)
            self.home_page.show_error(error_msg)

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
        # Farben definieren
        accent = "#2563eb"  # Primär-Akzent (deeper blue)
        success = "#3fb950"
        danger = "#f85149"
        warning = "#ffb86b"

        QApplication.setStyle("Fusion")

        if theme == 'dark':
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(230, 230, 230))
            palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(230, 230, 230))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(230, 230, 230))
            palette.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
            palette.setColor(QPalette.ColorRole.Button, QColor(36, 40, 44))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
            palette.setColor(QPalette.ColorRole.Link, QColor(88, 166, 255))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(88, 166, 255))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            app = QApplication.instance()
            if app:
                app.setPalette(palette)
            self.setPalette(palette)

            # Modernes, farbiges Stylesheet für Dark Mode
            base_styles = f"""
                QWidget {{ background-color: #121212; color: #e6e6e6; }}
                #top_nav {{ background-color: rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.03); }}
                #sidebar {{ background-color: #0f1720; }}
                #sidebar_info, #sidebar_authors {{ color: #9aa6b2; }}
                QPushButton#nav_button[active="true"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 #2b6fbf); color: white; font-weight: 600; }}
                QPushButton#nav_button {{ background: transparent; border: none; color: #cbd5e1; text-align: left; padding-left: 12px; }}
                .content_card, .preset_card, .shortcut_card, #result_panel {{ background-color: #111316; border-radius: 12px; border: 1px solid rgba(255,255,255,0.03); }}
                #page_stack {{ background: transparent; }}
                /* Buttons */
                QPushButton#btn_primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 #1e40af); color: white; border-radius: 10px; padding: 10px 14px; font-weight: 700; }}
                QPushButton#btn_primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e40af, stop:1 {accent}); }}
                QPushButton#btn_secondary {{ background: rgba(255,255,255,0.03); color: #e6e6e6; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_secondary:hover {{ background: rgba(255,255,255,0.06); }}
                QPushButton#btn_success {{ background: {success}; color: white; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_danger {{ background: {danger}; color: white; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_warning {{ background: {warning}; color: #1f1f1f; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_ghost {{ background: transparent; color: {accent}; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_ghost:hover {{ background: rgba(37,99,235,0.06); }}
                /* Inputs */
                QLineEdit, QTextEdit, QComboBox {{ background: #0b0d0f; border: 1px solid rgba(255,255,255,0.04); color: #e6e6e6; }}
                QLineEdit[error="true"], QTextEdit[error="true"] {{ border: 1px solid {danger}; }}
                /* Cards */
                .preset_card {{ padding: 14px; }}
                .section_title {{ color: #e6eefb; }}
                QLabel#preset_meta {{ color: #9aa6b2; font-size: 12px; }}
                /* Toast */
                QLabel#toast {{ background: rgba(0,0,0,0.7); color: white; padding: 8px 14px; border-radius: 10px; }}
            """
        else:
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(250, 250, 250))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(20, 20, 20))
            palette.setColor(QPalette.ColorRole.Base, QColor(245, 245, 245))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(235, 235, 235))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(20, 20, 20))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(20, 20, 20))
            palette.setColor(QPalette.ColorRole.Text, QColor(20, 20, 20))
            palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(20, 20, 20))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
            palette.setColor(QPalette.ColorRole.Link, QColor(8, 88, 166))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(8, 88, 166))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            app = QApplication.instance()
            if app:
                app.setPalette(palette)
            self.setPalette(palette)

            base_styles = f"""
                QWidget {{ background-color: #ffffff; color: #111827; }}
                #top_nav {{ background-color: rgba(0,0,0,0.02); border-bottom: 1px solid rgba(16,24,40,0.04); }}
                #sidebar {{ background-color: #f7fafc; }}
                #sidebar_info, #sidebar_authors {{ color: #6b7280; }}
                QPushButton#nav_button[active="true"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 #2b6fbf); color: white; font-weight: 600; }}
                QPushButton#nav_button {{ background: transparent; border: none; color: #0f172a; text-align: left; padding-left: 12px; }}
                .content_card, .preset_card, .shortcut_card, #result_panel {{ background-color: #ffffff; border-radius: 12px; border: 1px solid rgba(15,23,42,0.04); box-shadow: 0 6px 18px rgba(15,23,42,0.04); }}
                /* Buttons */
                QPushButton#btn_primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 #1e40af); color: white; border-radius: 10px; padding: 10px 14px; font-weight: 700; }}
                QPushButton#btn_primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e40af, stop:1 {accent}); }}
                QPushButton#btn_secondary {{ background: rgba(15,23,42,0.04); color: #0f172a; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_secondary:hover {{ background: rgba(15,23,42,0.06); }}
                QPushButton#btn_success {{ background: {success}; color: white; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_danger {{ background: {danger}; color: white; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_warning {{ background: {warning}; color: #1f1f1f; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_ghost {{ background: transparent; color: {accent}; border-radius: 10px; padding: 8px 12px; }}
                QPushButton#btn_ghost:hover {{ background: rgba(37,99,235,0.06); }}
                /* Inputs */
                QLineEdit, QTextEdit, QComboBox {{ background: #ffffff; border: 1px solid rgba(15,23,42,0.06); color: #0f172a; }}
                QLineEdit[error="true"], QTextEdit[error="true"] {{ border: 1px solid {danger}; }}
                /* Cards */
                .preset_card {{ padding: 14px; }}
                .section_title {{ color: #0f172a; }}
                QLabel#preset_meta {{ color: #6b7280; font-size: 12px; }}
                /* Toast */
                QLabel#toast {{ background: rgba(16,24,40,0.9); color: white; padding: 8px 14px; border-radius: 10px; }}
            """

        # Gemeinsames Stylesheet-Grundgerüst (Schriftfamilie, allgemeine Rundungen)
        common = """
            * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }
            QLineEdit, QComboBox, QTextEdit { border-radius: 8px; padding: 10px; }
            QPushButton { border-radius: 8px; padding: 8px 14px; }
            QLabel#section_subtitle { color: rgba(100,116,139,0.9); }
        """

        # Anwenden
        try:
            self.setStyleSheet(base_styles + common)
        except Exception:
            # Fallback: Mindestens common anwenden
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
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(28)


class HomePage(BasePage):
    """Aufgeräumte HomePage: Liste, Suche, Form zum Erstellen, Result-Panel."""

    def __init__(self, parent):
        super().__init__(parent)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Preset-Liste + Suche
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        title = QLabel("Meine Presets")
        title.setObjectName("section_title")
        title.setFont(QFont("SF Pro Display", 28, QFont.Weight.Bold))
        header_layout.addWidget(title)
        subtitle = QLabel("Erstelle, verwalte und nutze deine API-Prompts")
        subtitle.setObjectName("section_subtitle")
        subtitle.setFont(QFont("SF Pro Display", 14))
        header_layout.addWidget(subtitle)
        left_layout.addLayout(header_layout)

        # Suche
        search_card = QWidget()
        search_card.setObjectName("content_card")
        search_layout = QVBoxLayout(search_card)
        search_layout.setSpacing(10)
        search_label = QLabel("Suche")
        search_label.setObjectName("input_label")
        search_layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nach Name oder Prompt suchen...")
        self.search_input.textChanged.connect(self.filter_presets)
        search_layout.addWidget(self.search_input)
        left_layout.addWidget(search_card)

        # Preset-Liste (keine ScrollArea - alle Presets sollen in einem Blick sichtbar sein)
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(16)
        self.presets_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.addWidget(self.presets_container, 1)
        self.main_splitter.addWidget(left_widget)

        # RIGHT: Form + Result
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(20)

        # Form zum Erstellen
        form_card = QWidget()
        form_card.setObjectName("content_card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(18)
        form_title = QLabel("Neues Preset erstellen")
        form_title.setObjectName("section_title")
        form_title.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
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

        api_label = QLabel("API-Typ")
        api_label.setObjectName("input_label")
        form_layout.addWidget(api_label)
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["ChatGPT", "GPT-4", "GPT-3.5-Turbo"])
        form_layout.addWidget(self.api_type_combo)

        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Zurücksetzen")
        reset_btn.setObjectName("btn_secondary")
        reset_btn.setFixedHeight(44)
        reset_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(reset_btn)
        save_btn = QPushButton("Preset Speichern")
        save_btn.setObjectName("btn_success")
        save_btn.setFixedHeight(44)
        save_btn.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        save_btn.clicked.connect(self.save_new_preset)
        btn_layout.addWidget(save_btn, 1)
        form_layout.addLayout(btn_layout)
        right_layout.addWidget(form_card)

        # Result-Panel
        self.result_card = QWidget()
        self.result_card.setObjectName("result_panel")
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setSpacing(14)
        result_header = QLabel("Ergebnis")
        result_header.setObjectName("section_title")
        result_header.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        result_layout.addWidget(result_header)
        self.result_content = QTextEdit()
        self.result_content.setReadOnly(True)
        self.result_content.setPlaceholderText("Das Ergebnis der API-Anfrage wird hier angezeigt...")
        result_layout.addWidget(self.result_content, 1)
        result_btn_layout = QHBoxLayout()
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
        if text:
            pyperclip.copy(text)
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast("In Zwischenablage kopiert")

    def clear_result(self):
        self.result_content.clear()
        self.result_card.hide()

    # --- Preset-Liste ---
    def update_presets_list(self):
        # Alle Widgets entfernen
        for i in reversed(range(self.presets_layout.count())):
            w = self.presets_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        presets = self.controller.presets
        filtered = [(i, p) for i, p in enumerate(presets) if not self.current_search or
                    self.current_search.lower() in p["name"].lower() or
                    self.current_search.lower() in p["prompt"].lower()]

        if not filtered:
            empty = QWidget()
            empty.setObjectName("empty_state")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(16)
            empty_title = QLabel("Keine Presets gefunden")
            empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_title.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
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
        api_type = self.api_type_combo.currentText()

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

        success = self.controller.backend.save_preset(name, prompt, api_type)
        if success:
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast(f"Preset '{name}' gespeichert")
            self.clear_form()
            self.update_presets_list()
        else:
            if hasattr(self.controller, 'show_toast'):
                self.controller.show_toast("Fehler: Preset konnte nicht gespeichert werden (evtl. Name bereits vorhanden)")

    def create_preset_widget(self, index, preset):
        card = QWidget()
        card.setObjectName("preset_card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 18, 20, 18)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_box = QWidget()
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        title = QLabel(preset["name"])
        title.setObjectName("preset_header")
        title_layout.addWidget(title)
        meta = QLabel(f"API: {preset['api_type']}")
        meta.setObjectName("preset_meta")
        title_layout.addWidget(meta)
        header_layout.addWidget(title_box, 1)

        btn_box = QWidget()
        btn_layout_h = QHBoxLayout(btn_box)
        btn_layout_h.setContentsMargins(0, 0, 0, 0)
        btn_layout_h.setSpacing(8)

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
        edit_btn.setStyleSheet(f"background-color: {EDIT_BUTTON_COLOR}; color: white;")
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
        if len(prompt) > 180:
            prompt = prompt[:180] + "..."

        prompt_label = QLabel(prompt)
        prompt_label.setObjectName("preset_prompt")
        prompt_label.setWordWrap(True)
        layout.addWidget(prompt_label)

        return card

    def set_shortcut(self, index):
        dialog = ShortcutDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            shortcut = dialog.get_shortcut()
            if shortcut:
                # Persistiere Shortcut im Backend und registriere danach
                if self.controller.backend.save_preset_shortcut(index, shortcut):
                    # Registrierung im Controller
                    if hasattr(self.controller, 'register_preset_shortcut'):
                        self.controller.register_preset_shortcut(shortcut, index)
                else:
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast("Fehler beim Speichern des Shortcuts")

    def edit_preset(self, index):
        if 0 <= index < len(self.controller.presets):
            preset = self.controller.presets[index]
            dialog = EditPresetDialog(self, preset)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if not data["name"] or not data["prompt"]:
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast("Name und Prompt erforderlich")
                    return
                if self.controller.backend.update_preset_by_index(index, data["name"], data["prompt"], data["api_type"]):
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast(f"Preset '{data['name']}' aktualisiert")
                    self.update_presets_list()
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
                    self.update_presets_list()
                else:
                    if hasattr(self.controller, 'show_toast'):
                        self.controller.show_toast("Fehler beim Löschen")

    def clear_form(self):
        self.preset_name_input.clear()
        self.preset_prompt_input.clear()
        self.api_type_combo.setCurrentIndex(0)
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
        title.setFont(QFont("SF Pro Display", 28, QFont.Weight.Bold))
        self.main_layout.addWidget(title)

        subtitle = QLabel("Konfiguriere deine OpenAI API-Zugangsdaten")
        subtitle.setObjectName("section_subtitle")
        subtitle.setFont(QFont("SF Pro Display", 14))
        self.main_layout.addWidget(subtitle)

        # API Key Card
        api_card = QWidget()
        api_card.setObjectName("content_card")
        api_layout = QVBoxLayout(api_card)
        api_layout.setSpacing(16)

        key_label = QLabel("OpenAI API-Key")
        key_label.setObjectName("input_label")
        api_layout.addWidget(key_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        api_layout.addWidget(self.api_key_input)

        hint = QLabel("Den API-Key findest du unter: platform.openai.com/api-keys")
        hint.setObjectName("hint_text")
        api_layout.addWidget(hint)

        api_layout.addSpacing(16)

        # Buttons
        btn_layout = QHBoxLayout()

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
        creds = self.controller.api_credentials
        if "OpenAI" in creds:
            self.api_key_input.setText(creds["OpenAI"])
            self.status_label.setText("API-Key gespeichert")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")

    def save_credentials(self):
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self.controller.show_toast("Bitte API-Key eingeben")
            return

        if not api_key.startswith("sk-"):
            self.controller.show_toast("API-Key sollte mit 'sk-' beginnen")
            return

        if self.controller.backend.save_credentials(api_key, "OpenAI"):
            self.controller.show_toast("API-Key gespeichert")
            self.status_label.setText("Gespeichert")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
        else:
            self.controller.show_toast("Fehler beim Speichern")

    def test_api(self):
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self.controller.show_toast("Bitte API-Key eingeben")
            return

        self.controller.backend.save_credentials(api_key, "OpenAI")

        self.status_label.setText("Teste Verbindung...")
        self.status_label.setStyleSheet("color: #58a6ff; font-weight: 600;")
        QApplication.processEvents()

        result = self.controller.backend.test_credential("OpenAI")

        if result.get("status") == "success":
            self.status_label.setText("Verbindung erfolgreich!")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
            self.controller.show_toast("API-Test erfolgreich")
        else:
            error = result.get("message", "Unbekannter Fehler")
            self.status_label.setText(f"Fehler: {error}")
            self.status_label.setStyleSheet("color: #f85149; font-weight: 600;")
            self.controller.show_toast("API-Test fehlgeschlagen")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PromptPilot")
    app.setOrganizationName("Cian & Malik")

    window = APIManager()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
