import sys
import pyperclip
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QAction, QKeySequence, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFrame, QScrollArea, QMessageBox, QStackedWidget,
    QTextEdit, QDialog, QDialogButtonBox, QSplitter,

    QProgressBar, QSystemTrayIcon, QMenu, QStyle
)
from backend import APIBackend
import re


# ===== HELPER FUNCTIONS (müssen vor den Klassen definiert sein) =====

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
    valid_modifiers = {"Ctrl", "Shift", "Alt", "Cmd", "Meta"}
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
        return False, "Shortcut benötigt mindestens einen Modifier (z.B. Ctrl+, Cmd+)"

    modifiers = parts[:-1]
    key = parts[-1].strip()

    # Validiere Modifiers
    for mod in modifiers:
        mod = mod.strip()
        if mod not in valid_modifiers:
            return False, f"Ungültiger Modifier: '{mod}'. Erlaubt: Ctrl, Shift, Alt, Cmd"

    # Validiere Key
    if key not in valid_keys:
        return False, f"Ungültiger Key: '{key}'"

    # Platform-spezifische Validierung
    if platform == "darwin":  # macOS
        has_cmd = any(m.strip() in ("Cmd", "Meta") for m in modifiers)
        has_ctrl = any(m.strip() == "Ctrl" for m in modifiers)
        has_alt = any(m.strip() == "Alt" for m in modifiers)

        if has_ctrl and not has_cmd and len(modifiers) == 1:
            return False, "Auf macOS: Verwende 'Cmd' statt 'Ctrl' (z.B. Cmd+G statt Ctrl+G)"

        if has_alt and not (has_cmd or has_ctrl):
            return False, "Auf macOS: Alt sollte mit Cmd oder Ctrl kombiniert werden"
    else:  # Windows/Linux
        has_cmd = any(m.strip() in ("Cmd", "Meta") for m in modifiers)
        if has_cmd:
            return False, "Auf Windows/Linux: Verwende 'Ctrl' statt 'Cmd' (z.B. Ctrl+G)"

    return True, ""


def normalize_shortcut_for_platform(shortcut_str: str, platform: str = None) -> str:
    """
    Normalisiert einen Shortcut für die aktuelle Plattform.
    """
    if platform is None:
        platform = sys.platform

    shortcut_str = shortcut_str.strip()

    if platform == "darwin":  # macOS
        if shortcut_str.startswith("Ctrl+") and len(shortcut_str.split("+")) == 2:
            shortcut_str = shortcut_str.replace("Ctrl", "Cmd")
    else:  # Windows/Linux
        shortcut_str = shortcut_str.replace("Cmd", "Ctrl")
        shortcut_str = shortcut_str.replace("Meta", "Ctrl")

    return shortcut_str


# Platform-specific modifier key
def get_modifier_key():
    """Returns 'Cmd' for macOS, 'Ctrl' for Windows/Linux"""
    return "Cmd" if sys.platform == "darwin" else "Ctrl"

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
            index = self.api_type_combo.findText(api_type, Qt.MatchFixedString)
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
        self.shortcut_input.setPlaceholderText("z.B. Cmd+Shift+T" if sys.platform == "darwin" else "z.B. Ctrl+Shift+T")
        layout.addWidget(self.shortcut_input)

        # Beispiele - plattformspezifisch
        if sys.platform == "darwin":
            examples = QLabel("Beispiele: Cmd+Shift+S, Cmd+T, Cmd+Alt+P")
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
        self.setMinimumSize(1200, 700)

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

        # Erzwinge Dark Mode
        self.force_dark_mode()

        self.backend = APIBackend()
        self.current_page_index = 0
        self.preset_shortcuts = {}
        self.preset_shortcut_actions = {}

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

        self.setup_shortcuts()
        self.apply_stylesheets()

        self.toast_label = QLabel(self)
        self.toast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toast_label.setObjectName("toast")
        self.toast_label.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.timeout.connect(self.hide_toast)

    def force_dark_mode(self):
        """Erzwingt Dark Mode für die gesamte Anwendung"""
        QApplication.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.Button, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(88, 166, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(88, 166, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

        app = QApplication.instance()
        if app:
            app.setPalette(palette)
        self.setPalette(palette)

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
        shortcut1 = QAction(self)
        shortcut1.setShortcut(QKeySequence("Ctrl+1"))
        shortcut1.triggered.connect(lambda: self.change_page(0))
        self.addAction(shortcut1)

        shortcut2 = QAction(self)
        shortcut2.setShortcut(QKeySequence("Ctrl+2"))
        shortcut2.triggered.connect(lambda: self.change_page(1))
        self.addAction(shortcut2)

    def show_shortcuts_overview(self):
        dialog = ShortcutOverviewDialog(self, self.preset_shortcuts, self.backend.presets)
        dialog.exec()

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

        # Konvertiere für QKeySequence
        # QKeySequence erkennt: Ctrl, Shift, Alt, Meta (=Cmd auf macOS)
        qt_shortcut = shortcut_key

        # Auf macOS: Cmd -> Meta für QKeySequence
        if sys.platform == "darwin":
            qt_shortcut = qt_shortcut.replace("Cmd", "Meta")

        print(f"[DEBUG] Registriere Shortcut: {shortcut_key} -> QKeySequence: {qt_shortcut}")

        # Erstelle die Action
        action = QAction(self)
        action.setShortcut(QKeySequence(qt_shortcut))
        action.triggered.connect(lambda idx=preset_index, key=shortcut_key: self.on_preset_shortcut_triggered(idx, key))
        self.addAction(action)

        self.preset_shortcuts[shortcut_key] = preset_index
        self.preset_shortcut_actions[shortcut_key] = action

        print(f"[DEBUG] Shortcut registriert. Aktive Shortcuts: {self.preset_shortcuts}")
        self.show_toast(f"✓ Shortcut {shortcut_key} aktiviert")

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

    def apply_stylesheets(self):
        self.setStyleSheet("""
            * {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }

            QWidget {
                font-size: 13px;
                background-color: #121212;
                color: #e6e6e6;
            }

            QMainWindow {
                background-color: #121212;
            }

            #top_nav {
                background-color: #1a1a1a;
                border-bottom: 1px solid #333333;
            }
            
            #top_nav_separator {
                background-color: #333333;
            }

            #app_title {
                color: #58a6ff;
                letter-spacing: -0.5px;
            }

            #sidebar {
                background-color: #161616;
                border-right: 1px solid #333333;
            }

            #nav_label {
                color: #8b8b8b;
                letter-spacing: 0.5px;
                font-size: 10px;
            }

            #sidebar_bottom {
                background-color: #1a1a1a;
                border-top: 1px solid #333333;
            }

            #sidebar_info {
                color: #6c757d;
            }

            #sidebar_authors {
                color: #4a4a4a;
            }

            #nav_button {
                background-color: transparent;
                color: #b0b0b0;
                border: none;
                border-left: 3px solid transparent;
                border-radius: 6px;
                text-align: left;
                padding: 14px 16px;
                font-weight: 500;
                font-size: 14px;
            }

            #nav_button:hover {
                background-color: #222222;
                color: #e6e6e6;
            }

            #nav_button[active="true"] {
                background-color: #1a3a52;
                color: #58a6ff;
                font-weight: 600;
                border-left: 3px solid #58a6ff;
            }

            #page_stack {
                background-color: #121212;
            }

            #content_card {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 12px;
                padding: 24px;
            }

            #section_title {
                font-size: 28px;
                font-weight: 700;
                color: #e6e6e6;
                letter-spacing: -0.5px;
                line-height: 1.2;
            }

            #section_subtitle {
                font-size: 14px;
                color: #8b8b8b;
                line-height: 1.6;
            }

            #input_label {
                font-weight: 500;
                color: #d0d0d0;
                font-size: 13px;
                margin-bottom: 8px;
            }

            QLineEdit, QComboBox, QTextEdit {
                background-color: #1e1e1e;
                color: #e6e6e6;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 12px 14px;
                selection-background-color: #58a6ff;
                font-size: 13px;
                line-height: 1.6;
            }

            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 2px solid #58a6ff;
                padding: 11px 13px;
                background-color: #222222;
                outline: none;
            }

            QLineEdit[error="true"], QTextEdit[error="true"] {
                border: 2px solid #f85149;
                padding: 11px 13px;
                background-color: #2a1a1a;
            }

            QComboBox::drop-down {
                border: none;
                width: 30px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #8b8b8b;
                margin-right: 10px;
            }

            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #e6e6e6;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                selection-background-color: #58a6ff;
                padding: 4px;
            }

            QPushButton {
                background-color: #58a6ff;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 11px 24px;
                font-weight: 600;
                font-size: 13px;
            }

            QPushButton:hover {
                background-color: #4a95e8;
            }

            QPushButton:pressed {
                background-color: #3a85d8;
            }

            QPushButton:focus {
                outline: 2px solid #58a6ff;
                outline-offset: 2px;
            }

            QPushButton#btn_primary {
                background-color: #58a6ff;
                min-width: 100px;
            }

            QPushButton#btn_primary:hover {
                background-color: #4a95e8;
            }

            QPushButton#btn_success {
                background-color: #3fb950;
                min-width: 100px;
            }

            QPushButton#btn_success:hover {
                background-color: #2ea043;
            }

            QPushButton#btn_danger {
                background-color: #f85149;
                padding: 9px 18px;
            }

            QPushButton#btn_danger:hover {
                background-color: #da3633;
            }

            QPushButton#btn_warning {
                background-color: #d29922;
                color: #000;
            }

            QPushButton#btn_warning:hover {
                background-color: #c08919;
            }

            QPushButton#btn_secondary {
                background-color: #2a2a2a;
                color: #e6e6e6;
            }

            QPushButton#btn_secondary:hover {
                background-color: #3a3a3a;
            }

            QPushButton#btn_ghost {
                background-color: transparent;
                color: #8b8b8b;
                border: 1px solid #3a3a3a;
            }

            QPushButton#btn_ghost:hover {
                background-color: #1e1e1e;
                color: #e6e6e6;
                border-color: #58a6ff;
            }

            #preset_card {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 12px;
                padding: 20px;
                min-height: 120px;
            }

            #preset_card:hover {
                border-color: #58a6ff;
                background-color: #1e1e1e;
            }

            #preset_header {
                font-weight: 600;
                font-size: 16px;
                color: #e6e6e6;
                line-height: 1.4;
            }

            #preset_meta {
                font-size: 12px;
                color: #6c757d;
            }

            #preset_prompt {
                font-size: 13px;
                color: #8b8b8b;
                line-height: 1.6;
            }

            #toast {
                background-color: #1e1e1e;
                color: #e6e6e6;
                border-radius: 8px;
                padding: 14px 24px;
                border: 1px solid #3a3a3a;
                font-size: 13px;
                font-weight: 500;
            }

            #error_label {
                color: #f85149;
                font-size: 12px;
                margin-top: 6px;
                padding: 8px 12px;
                background-color: rgba(248, 81, 73, 0.1);
                border-radius: 6px;
            }

            #hint_text {
                color: #8b8b8b;
                font-size: 12px;
                line-height: 1.5;
            }

            #loading_label {
                color: #58a6ff;
                font-size: 12px;
            }

            #empty_state {
                color: #6c757d;
                font-size: 14px;
                padding: 80px 40px;
                text-align: center;
            }

            #result_panel {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 12px;
                padding: 20px;
                min-height: 300px;
            }

            #result_panel QTextEdit {
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                font-size: 12px;
                line-height: 1.6;
            }

            #shortcut_card {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 10px;
            }

            #shortcut_item {
                background-color: transparent;
                border-radius: 6px;
            }

            #shortcut_item:hover {
                background-color: #1e1e1e;
            }

            #shortcut_key {
                background-color: #2a2a2a;
                color: #58a6ff;
                padding: 6px 14px;
                border-radius: 6px;
                min-width: 100px;
                font-weight: 600;
            }

            #shortcut_arrow {
                color: #4a4a4a;
                font-size: 16px;
            }

            #shortcut_desc {
                color: #b0b0b0;
                line-height: 1.5;
            }

            #card_title {
                color: #e6e6e6;
                margin-bottom: 8px;
            }

            #dialog_title {
                color: #e6e6e6;
            }

            QProgressBar {
                background-color: #2a2a2a;
                border: none;
                border-radius: 3px;
                text-align: center;
                height: 6px;
            }

            QProgressBar::chunk {
                background-color: #58a6ff;
                border-radius: 3px;
            }

            QScrollArea {
                border: none;
                background-color: transparent;
            }

            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 4px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #58a6ff;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            QMessageBox {
                background-color: #1a1a1a;
            }

            QMessageBox QLabel {
                color: #e6e6e6;
                font-size: 13px;
                line-height: 1.6;
            }

            QMessageBox QPushButton {
                min-width: 90px;
                padding: 10px 20px;
            }

            QDialog {
                background-color: #1a1a1a;
                color: #e6e6e6;
            }
            
            QSplitter::handle {
                background-color: #2a2a2a;
                width: 2px;
            }
            
            QSplitter::handle:hover {
                background-color: #58a6ff;
            }
        """)

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
    def __init__(self, parent):
        super().__init__(parent)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT SIDE
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

        # Search
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

        # Presets List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("scroll_area")

        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(16)
        self.presets_layout.setContentsMargins(0, 0, 10, 0)

        scroll.setWidget(self.presets_container)
        left_layout.addWidget(scroll, 1)

        self.main_splitter.addWidget(left_widget)

        # RIGHT SIDE
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(20)

        # CREATE FORM
        form_card = QWidget()
        form_card.setObjectName("content_card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(18)

        form_title = QLabel("Neues Preset erstellen")
        form_title.setObjectName("section_title")
        form_title.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        form_layout.addWidget(form_title)

        # Name
        name_label = QLabel("Preset-Name")
        name_label.setObjectName("input_label")
        form_layout.addWidget(name_label)

        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("z.B. Text Zusammenfassung")
        self.preset_name_input.textChanged.connect(self.validate_form)
        form_layout.addWidget(self.preset_name_input)

        self.name_error_label = QLabel("")
        self.name_error_label.setObjectName("error_label")
        self.name_error_label.hide()
        form_layout.addWidget(self.name_error_label)

        # Prompt
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

        # API Type
        api_label = QLabel("API-Typ")
        api_label.setObjectName("input_label")
        form_layout.addWidget(api_label)

        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["ChatGPT", "GPT-4", "GPT-3.5-Turbo"])
        form_layout.addWidget(self.api_type_combo)

        form_layout.addSpacing(12)

        # BUTTONS
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

        # RESULT PANEL
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

    def validate_form(self):
        name = self.preset_name_input.text().strip()
        prompt = self.preset_prompt_input.toPlainText().strip()

        # Name validieren
        if not name:
            self.name_error_label.setText("Name ist erforderlich")
            self.name_error_label.show()
            self.preset_name_input.setProperty("error", True)
        elif len(name) < 3:
            self.name_error_label.setText("Name muss mindestens 3 Zeichen haben")
            self.name_error_label.show()
            self.preset_name_input.setProperty("error", True)
        elif any(p["name"] == name for p in self.controller.presets):
            self.name_error_label.setText("Preset mit diesem Namen existiert bereits")
            self.name_error_label.show()
            self.preset_name_input.setProperty("error", True)
        else:
            self.name_error_label.hide()
            self.preset_name_input.setProperty("error", False)

        # Prompt validieren
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

        # Style aktualisieren
        self.preset_name_input.style().unpolish(self.preset_name_input)
        self.preset_name_input.style().polish(self.preset_name_input)
        self.preset_prompt_input.style().unpolish(self.preset_prompt_input)
        self.preset_prompt_input.style().polish(self.preset_prompt_input)

    def show_loading(self):
        self.result_card.show()
        self.result_content.setPlainText("Verarbeite Anfrage...\n\nBitte warten...")

    def show_result(self, preset_name, input_text, result):
        self.result_card.show()
        output = f"PRESET\n{preset_name}\n\n"
        output += f"EINGABE\n{input_text}\n\n"
        output += f"ERGEBNIS\n{result}"
        self.result_content.setPlainText(output)

    def show_error(self, error_msg):
        self.result_card.show()
        self.result_content.setPlainText(f"FEHLER\n\n{error_msg}")

    def copy_result(self):
        text = self.result_content.toPlainText()
        if text:
            pyperclip.copy(text)
            self.controller.show_toast("In Zwischenablage kopiert")

    def clear_result(self):
        self.result_content.clear()
        self.result_card.hide()

    def update_presets_list(self):
        for i in reversed(range(self.presets_layout.count())):
            w = self.presets_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        presets = self.controller.presets
        filtered = [p for p in presets if not self.current_search or
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

        for idx, preset in enumerate(filtered):
            self.presets_layout.addWidget(self.create_preset_widget(idx, preset))

        self.presets_layout.addStretch()

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
        shortcut_btn.clicked.connect(lambda: self.set_shortcut(index))
        btn_layout_h.addWidget(shortcut_btn)

        # Edit Button
        edit_btn = QPushButton("Bearbeiten")
        edit_btn.setObjectName("btn_warning")
        edit_btn.setToolTip("Preset bearbeiten")
        edit_btn.setMinimumWidth(110)
        edit_btn.setFixedHeight(40)
        edit_btn.clicked.connect(lambda: self.edit_preset(index))
        btn_layout_h.addWidget(edit_btn)

        # Execute Button
        use_btn = QPushButton("Ausführen")
        use_btn.setObjectName("btn_primary")
        use_btn.setMinimumWidth(120)
        use_btn.setFixedHeight(40)
        use_btn.setToolTip("Preset mit Zwischenablage ausführen")
        use_btn.clicked.connect(lambda: self.controller.execute_preset_by_index(index))
        btn_layout_h.addWidget(use_btn)

        # Delete Button
        delete_btn = QPushButton("Löschen")
        delete_btn.setObjectName("btn_danger")
        delete_btn.setMinimumWidth(95)
        delete_btn.setFixedHeight(40)
        delete_btn.setToolTip("Preset entfernen")
        delete_btn.clicked.connect(lambda: self.delete_preset(index))
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
                self.controller.register_preset_shortcut(shortcut, index)

    def edit_preset(self, index):
        if 0 <= index < len(self.controller.presets):
            preset = self.controller.presets[index]
            dialog = EditPresetDialog(self, preset)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()

                if not data["name"] or not data["prompt"]:
                    self.controller.show_toast("Name und Prompt erforderlich")
                    return

                if self.controller.backend.update_preset_by_index(
                        index, data["name"], data["prompt"], data["api_type"]
                ):
                    self.controller.show_toast(f"Preset '{data['name']}' aktualisiert")
                    self.update_presets_list()
                else:
                    self.controller.show_toast("Fehler beim Aktualisieren")

    def filter_presets(self):
        self.current_search = self.search_input.text().strip()
        self.update_presets_list()

    def save_new_preset(self):
        name = self.preset_name_input.text().strip()
        prompt = self.preset_prompt_input.toPlainText().strip()
        api_type = self.api_type_combo.currentText()

        if not name or not prompt:
            self.controller.show_toast("Name und Prompt erforderlich")
            self.validate_form()
            return

        if len(name) < 3:
            self.controller.show_toast("Name muss mindestens 3 Zeichen haben")
            self.validate_form()
            return

        if len(prompt) < 10:
            self.controller.show_toast("Prompt sollte mindestens 10 Zeichen haben")
            self.validate_form()
            return

        if self.controller.backend.save_preset(name, prompt, api_type):
            self.controller.show_toast(f"Preset '{name}' gespeichert")
            self.update_presets_list()
            self.clear_form()
        else:
            self.controller.show_toast("Preset existiert bereits")
            self.validate_form()

    def delete_preset(self, index):
        if 0 <= index < len(self.controller.presets):
            p = self.controller.presets[index]
            reply = QMessageBox.question(
                self,
                "Preset löschen",
                f"Möchtest du das Preset '{p['name']}' wirklich löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.controller.backend.delete_preset_by_index(index):
                    self.controller.show_toast(f"'{p['name']}' gelöscht")
                    self.update_presets_list()
                else:
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
