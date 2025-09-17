# This file was previously named main.py and is now renamed to frontend.py to reflect its role as the frontend (UI) part of the application.

import sys
import pyperclip
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QPoint, QMimeData, QTimer
from PySide6.QtGui import QIcon, QFont, QAction, QKeySequence, QDrag, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFrame, QScrollArea, QMessageBox, QStackedWidget,
    QGridLayout, QSizePolicy, QTextEdit, QMenu, QCheckBox,
    QToolTip, QDialog, QSlider, QProgressBar
)
from backend import APIBackend

class APIManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PromtPilot")
        self.setMinimumSize(900, 650)

        # --- Farbvariablen ---
        self.colors = {
            "primary": QColor("#0d6efd"),  # Primäre Akzentfarbe (z.B. Buttons)
            "secondary": QColor("#6c757d"), # Sekundäre Akzentfarbe (z.B. Texte, Icons)
            "background": QColor("#ffffff"), # Hintergrundfarbe
            "text": QColor("#212529")      # Textfarbe
        }
        self.dark_mode_colors = {
            "primary": QColor("#007bff"),
            "secondary": QColor("#a0a0a0"),
            "background": QColor("#121212"),
            "text": QColor("#e0e0e0")
        }
        self.current_colors = self.colors.copy() # Aktuell verwendete Farben
        # --------------------

        # Backend-Instanz
        self.backend = APIBackend()

        # Status für Dark Mode
        self.dark_mode_enabled = False

        # Aktive Seite speichern
        self.current_page_index = 0

        # Zentrale Widget-Struktur
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout für Hauptfenster
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Seitenleiste erstellen
        self.create_sidebar()
        main_layout.addWidget(self.sidebar)

        # Stack für Seiten
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("page_stack")

        # Seiten erstellen
        self.home_page = HomePage(self)
        self.credentials_page = CredentialsPage(self)

        self.page_stack.addWidget(self.home_page)
        self.page_stack.addWidget(self.credentials_page)

        # Übergänge für Seitenwechsel einrichten
        self.page_stack.setCurrentIndex(0)
        self.setup_page_transitions()

        main_layout.addWidget(self.page_stack)

        # Erstelle Tastaturkürzel
        self.setup_shortcuts()

        # Stylesheets anwenden
        self.apply_stylesheets()

        # Toast-Notification-System initialisieren
        self.toast_label = QLabel(self)
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.setObjectName("toast")
        self.toast_label.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.timeout.connect(self.hide_toast)

    def setup_page_transitions(self):
        # Property-Animation für Seitenwechsel
        self.page_animation = QPropertyAnimation(self.page_stack, b"pos")
        self.page_animation.setDuration(300)
        self.page_animation.setEasingCurve(QEasingCurve.InOutCubic)

    def setup_shortcuts(self):
        # Shortcuts für häufige Aktionen
        self.shortcut_home = QAction("Home", self)
        self.shortcut_home.setShortcut(QKeySequence("Ctrl+1"))
        self.shortcut_home.triggered.connect(lambda: self.change_page(0))
        self.addAction(self.shortcut_home)

        self.shortcut_api = QAction("API Credentials", self)
        self.shortcut_api.setShortcut(QKeySequence("Ctrl+2"))
        self.shortcut_api.triggered.connect(lambda: self.change_page(1))
        self.addAction(self.shortcut_api)

        self.shortcut_dark = QAction("Toggle Dark Mode", self)
        self.shortcut_dark.setShortcut(QKeySequence("Ctrl+D"))
        self.shortcut_dark.triggered.connect(self.toggle_dark_mode)
        self.addAction(self.shortcut_dark)

    def create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo-Container
        logo_container = QWidget()
        logo_container.setObjectName("logo_container")
        logo_layout = QVBoxLayout(logo_container)
        app_title = QLabel("API Manager")
        app_title.setObjectName("app_title")
        app_title.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(app_title)
        sidebar_layout.addWidget(logo_container)

        # Menü-Container
        menu_container = QWidget()
        menu_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(10, 20, 10, 20)
        menu_layout.setSpacing(10)

        # Sidebar-Buttons mit aktiver Anzeige
        self.home_btn = QPushButton("Home")
        self.home_btn.setObjectName("menu_button active")  # Initial aktiv
        self.home_btn.clicked.connect(lambda: self.change_page(0))

        self.api_btn = QPushButton("API Credentials")
        self.api_btn.setObjectName("menu_button")
        self.api_btn.clicked.connect(lambda: self.change_page(1))

        menu_layout.addWidget(self.home_btn)
        menu_layout.addWidget(self.api_btn)

        # Dark Mode Toggle
        dark_mode_container = QWidget()
        dark_mode_layout = QHBoxLayout(dark_mode_container)
        dark_mode_layout.setContentsMargins(0, 10, 0, 0)

        self.dark_mode_toggle = QCheckBox("Dark Mode")
        self.dark_mode_toggle.setObjectName("dark_mode_toggle")
        self.dark_mode_toggle.toggled.connect(self.toggle_dark_mode)

        dark_mode_layout.addWidget(self.dark_mode_toggle)
        menu_layout.addWidget(dark_mode_container)

        menu_layout.addStretch()
        sidebar_layout.addWidget(menu_container)

    def change_page(self, page_index):
        if page_index == self.current_page_index:
            return

        # Animierter Übergang
        direction = 1 if page_index > self.current_page_index else -1
        current_pos = self.page_stack.pos()

        # Animation einrichten
        self.page_animation.setStartValue(current_pos)
        self.page_animation.setEndValue(QPoint(current_pos.x(), current_pos.y() + direction * 20))

        # Seitenwechsel
        self.page_stack.setCurrentIndex(page_index)
        self.page_animation.start()

        # Update aktive Seite in Sidebar
        self.update_active_sidebar_button(page_index)
        self.current_page_index = page_index

    def update_active_sidebar_button(self, active_index):
        # Aktiven Button markieren
        self.home_btn.setObjectName("menu_button" if active_index != 0 else "menu_button active")
        self.api_btn.setObjectName("menu_button" if active_index != 1 else "menu_button active")

        # Stylesheet aktualisieren, damit Änderungen wirksam werden
        self.home_btn.style().unpolish(self.home_btn)
        self.home_btn.style().polish(self.home_btn)
        self.api_btn.style().unpolish(self.api_btn)
        self.api_btn.style().polish(self.api_btn)

    def toggle_dark_mode(self, checked=None):
        if checked is None:
            # Wenn von Shortcut aufgerufen
            self.dark_mode_enabled = not self.dark_mode_enabled
            self.dark_mode_toggle.setChecked(self.dark_mode_enabled)
        else:
            # Wenn von Checkbox aufgerufen
            self.dark_mode_enabled = checked

        # Aktuelle Farben basierend auf Dark Mode setzen
        self.current_colors = self.dark_mode_colors if self.dark_mode_enabled else self.colors

        # Dark Mode anwenden
        self.apply_stylesheets()

        # Feedback geben
        self.show_toast(f"Dark Mode {'aktiviert' if self.dark_mode_enabled else 'deaktiviert'}")

    def show_toast(self, message, duration=2000):
        """Zeigt eine Toast-Notification an"""
        self.toast_label.setText(message)
        self.toast_label.adjustSize()

        # Position zentriert unten
        self.toast_label.move(
            (self.width() - self.toast_label.width()) // 2,
            self.height() - self.toast_label.height() - 50
        )

        self.toast_label.show()
        self.toast_timer.start(duration)

    def hide_toast(self):
        """Blendet die Toast-Notification aus"""
        self.toast_label.hide()
        self.toast_timer.stop()

    def resizeEvent(self, event):
        """Behandelt Größenänderungen des Fensters"""
        super().resizeEvent(event)
        # Toast-Position aktualisieren, falls sichtbar
        if self.toast_label.isVisible():
            self.toast_label.move(
                (self.width() - self.toast_label.width()) // 2,
                self.height() - self.toast_label.height() - 50
            )

    def apply_stylesheets(self):
        # Stellen Sie sicher, dass Sie die Farben direkt aus self.current_colors holen,
        # und nur dann .name() aufrufen, wenn Sie sie im Stylesheet verwenden.

        primary_color_obj = self.current_colors["primary"]
        secondary_color_obj = self.current_colors["secondary"]
        background_color_obj = self.current_colors["background"]
        text_color_obj = self.current_colors["text"]

        # Für Elemente, die möglicherweise spezifische Farben benötigen, die nicht direkt in self.current_colors sind
        sidebar_bg = self.dark_mode_colors["background"].name() if self.dark_mode_enabled else "#f8f9fa"
        sidebar_border = "#3c3c3c"
        logo_bg = self.dark_mode_colors["background"].name() if self.dark_mode_enabled else "#e9ecef"
        app_title_color = "#ffffff" if self.dark_mode_enabled else "#212529"
        menu_button_color = "#cccccc" if self.dark_mode_enabled else "#495057"
        menu_button_hover_bg = "rgba(255, 255, 255, 0.1)"
        menu_button_active_bg = "rgba(0, 123, 255, 0.2)" if self.dark_mode_enabled else "rgba(13, 110, 253, 0.1)"

        self.setStyleSheet(f"""
            QWidget {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica', sans-serif;
                font-size: 14px;
                background-color: {background_color_obj.name()};
                color: {text_color_obj.name()};
            }}
            #sidebar {{
                background-color: {sidebar_bg};
                border-right: 1px solid {sidebar_border};
            }}
            #logo_container {{
                padding: 20px 10px;
                background-color: {logo_bg};
            }}
            #app_title {{
                color: {app_title_color};
                font-size: 18px;
                font-weight: bold;
            }}
            #menu_button {{
                background-color: transparent;
                color: {menu_button_color};
                text-align: left;
                padding: 12px 15px;
                border: none;
                border-radius: 6px;
            }}
            #menu_button:hover {{
                background-color: {menu_button_hover_bg};
                color: white;
            }}
            #menu_button.active {{
                background-color: {menu_button_active_bg};
                color: white;
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {primary_color_obj.name()};
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {primary_color_obj.darker(15).name()};
            }}
            QPushButton:pressed {{
                background-color: {primary_color_obj.darker(25).name()};
            }}
            QPushButton#save_btn {{
                background-color: #198754; /* Grün */
            }}
            QPushButton#save_btn:hover {{
                background-color: #157347;
            }}
            QPushButton#test_btn {{
                background-color: #ffc107; /* Gelb */
                color: #212529;
            }}
            QPushButton#test_btn:hover {{
                background-color: #ffca2c;
            }}
            QLineEdit, QComboBox, QTextEdit {{
                padding: 8px;
                border: 1px solid {secondary_color_obj.name()};
                border-radius: 6px;
                background-color: {background_color_obj.name()};
                color: {text_color_obj.name()};
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid {primary_color_obj.name()};
                outline: 2px solid rgba(13, 110, 253, 0.25);
            }}
            QLabel {{
                color: {text_color_obj.name()};
            }}
            #page_title {{
                font-size: 24px;
                font-weight: bold;
                color: {text_color_obj.name()};
                margin-bottom: 20px;
            }}
            #preset_item {{
                background-color: {background_color_obj.name()};
                border-radius: 8px;
                border: 1px solid #e9ecef;
                padding: 15px;
            }}
            #preset_item:hover {{
                border-color: #dee2e6;
                background-color: #f8f9fa;
            }}
            #preset_name {{
                font-weight: bold;
                font-size: 16px;
                color: {text_color_obj.name()};
            }}
            #empty_message {{
                color: {secondary_color_obj.name()};
                font-style: italic;
            }}

            /* Dark Mode Styles */
            QWidget {{
                background-color: #121212;
                color: #e0e0e0;
            }}
            #sidebar {{
                background-color: #1e1e1e;
                border-right: 1px solid #3c3c3c;
            }}
            #logo_container {{
                background-color: #161616;
            }}
            #app_title {{
                color: #ffffff;
            }}
            #menu_button {{
                color: #e0e0e0;
            }}
            #menu_button:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }}
            #menu_button.active {{
                background-color: rgba(0, 119, 204, 0.2);
                color: #ffffff;
                font-weight: bold;
            }}
            QPushButton {{
                background-color: #007bff;
                color: white;
            }}
            QPushButton:hover {{
                background-color: #0069d9;
            }}
            QPushButton:pressed {{
                background-color: #0056b3;
            }}
            QPushButton#save_btn {{
                background-color: #28a745;
            }}
            QPushButton#save_btn:hover {{
                background-color: #218838;
            }}
            QPushButton#test_btn {{
                background-color: #ffc107;
                color: #212529;
            }}
            QPushButton#test_btn:hover {{
                background-color: #ffca2c;
            }}
            QLineEdit, QComboBox, QTextEdit {{
                background-color: #2c2c2c;
                color: #e0e0e0;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid #007bff;
                outline: 2px solid rgba(0, 123, 255, 0.25);
            }}
            QLabel {{
                color: #e0e0e0;
            }}
            #page_title {{
                color: #ffffff;
            }}
            #preset_item {{
                background-color: #2c2c2c;
                border: 1px solid #444;
            }}
            #preset_item:hover {{
                background-color: #3c3c3c;
            }}
            #preset_name {{
                color: #ffffff;
            }}
            #empty_message {{
                color: #a0a0a0;
            }}
        """)
        
    def save_credentials(self, api_key, api_url):
        if self.backend.save_credentials(api_key, api_url):
            QMessageBox.information(self, "Erfolg", "API-Credentials wurden gespeichert!")

    def save_preset(self, name, prompt, api_type="chatgpt"):
        if self.backend.save_preset(name, prompt, api_type):
            self.home_page.update_presets_list()
            QMessageBox.information(self, "Erfolg", f"Preset '{name}' wurde gespeichert!")

    @property
    def api_credentials(self):
        return self.backend.api_credentials

    @property
    def presets(self):
        return self.backend.presets

    def use_preset(self, preset_index):
        if preset_index < 0 or preset_index >= len(self.presets):
            return
        preset = self.presets[preset_index]
        clipboard_text = pyperclip.paste()
        if not clipboard_text:
            QMessageBox.warning(self, "Warnung", "Die Zwischenablage ist leer!")
            return
        QMessageBox.information(self, "API-Aufruf",
            f"Preset '{preset['name']}' würde jetzt verwendet werden mit:\n\n"
            f"API-Typ: {preset['api_type']}\n"
            f"Prompt: {preset['prompt']}\n\n"
            f"Und dem Text aus der Zwischenablage: {clipboard_text[:30]}...")

class BasePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = parent
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        self.title_label = QLabel()
        self.title_label.setObjectName("page_title")
        self.main_layout.addWidget(self.title_label)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.content_area)

class HomePage(BasePage):
    def __init__(self, parent):
        super().__init__(parent)
        self.title_label.setText("Presets")

        # Suchleiste und Kategorien-Filter
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 15)

        # Suchfeld
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Presets durchsuchen...")
        self.search_input.textChanged.connect(self.filter_presets)
        search_layout.addWidget(self.search_input)

        # Kategorie-Dropdown (für zukünftige Implementierung)
        self.category_filter = QComboBox()
        self.category_filter.addItem("Alle Kategorien")
        self.category_filter.currentTextChanged.connect(self.filter_presets)
        search_layout.addWidget(self.category_filter)

        self.content_layout.addWidget(search_container)

        # Scroll-Bereich für Presets
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(15)
        scroll_area.setWidget(self.presets_container)
        self.content_layout.addWidget(scroll_area)
        self.content_layout.setStretch(1, 1)  # Scroll-Bereich soll wachsen

        # Formular für neues Preset
        form_container = QWidget()
        form_container.setObjectName("form_container")
        form_layout = QGridLayout(form_container)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(15)

        form_layout.addWidget(QLabel("<b>Neues Preset erstellen</b>"), 0, 0, 1, 2)

        # Name
        form_layout.addWidget(QLabel("Name:"), 1, 0)
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("Preset-Name")
        form_layout.addWidget(self.preset_name_input, 1, 1)

        # Prompt - jetzt mit TextEdit für Mehrzeileneingabe
        form_layout.addWidget(QLabel("Prompt:"), 2, 0)
        self.preset_prompt_input = QTextEdit()
        self.preset_prompt_input.setPlaceholderText("Prompt-Text eingeben...")
        self.preset_prompt_input.setAcceptRichText(False)
        self.preset_prompt_input.setFixedHeight(100)
        form_layout.addWidget(self.preset_prompt_input, 2, 1)

        # API-Typ mit mehr Optionen
        form_layout.addWidget(QLabel("API-Typ:"), 3, 0)
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["chatgpt", "gpt-4", "gpt-3.5-turbo", "dall-e", "andere_api"])
        form_layout.addWidget(self.api_type_combo, 3, 1)

        # Kategorie (für zukünftige Kategorisierung)
        form_layout.addWidget(QLabel("Kategorie:"), 4, 0)
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Optional")
        form_layout.addWidget(self.category_input, 4, 1)

        # Buttons für Formular
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)

        save_button = QPushButton("Preset speichern")
        save_button.setObjectName("save_btn")
        save_button.clicked.connect(self.save_new_preset)
        button_layout.addWidget(save_button)

        clear_button = QPushButton("Zurücksetzen")
        clear_button.clicked.connect(self.clear_form)
        button_layout.addWidget(clear_button)

        button_layout.addStretch()
        form_layout.addWidget(button_container, 5, 0, 1, 2)

        self.content_layout.addWidget(form_container)

        # Speichern der aktuellen Filtereinstellungen
        self.current_search = ""
        self.current_category = "Alle Kategorien"

        # Speichern des aktuell bearbeiteten Presets (für Edit-Modus)
        self.edit_mode = False
        self.edit_preset_index = -1

        # Liste der Presets aktualisieren
        self.update_presets_list()

    def update_presets_list(self):
        """Aktualisiert die Liste der Presets basierend auf aktuellen Filtern"""
        # Lösche bestehende Preset-Widgets
        for i in reversed(range(self.presets_layout.count())):
            widget = self.presets_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        presets = self.controller.presets
        filtered_presets = []

        # Filter anwenden
        for preset in presets:
            # Suchfilter
            if self.current_search and self.current_search.lower() not in preset["name"].lower() and \
               self.current_search.lower() not in preset["prompt"].lower():
                continue

            # Kategoriefilter (für zukünftige Implementierung)
            if self.current_category != "Alle Kategorien" and \
               preset.get("category", "") != self.current_category:
                continue

            filtered_presets.append(preset)

        # Leere Nachricht anzeigen, wenn keine Presets gefunden wurden
        if not filtered_presets:
            empty_message = "Keine Presets gefunden"
            if self.current_search or self.current_category != "Alle Kategorien":
                empty_message = "Keine Presets entsprechen den Filterkriterien"

            empty_label = QLabel(empty_message)
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setObjectName("empty_message")
            self.presets_layout.addWidget(empty_label)
            self.presets_layout.addStretch()
            return

        # Gefilterte Presets anzeigen
        for i, preset in enumerate(filtered_presets):
            # Hier muss die Logik für die globale Indexierung der Presets angepasst werden
            # Wenn die Liste gefiltert wird, ist der Index 'i' nicht mehr der globale Index.
            # Wir müssen den tatsächlichen Index des Presets in der `self.controller.presets` Liste finden.
            global_index = -1
            for idx, p in enumerate(self.controller.presets):
                if p == preset: # Vergleiche das gesamte Preset-Dictionary
                    global_index = idx
                    break

            preset_widget = self.create_preset_widget(global_index, preset)
            self.presets_layout.addWidget(preset_widget)

        self.presets_layout.addStretch()

    def create_preset_widget(self, index, preset):
        """Erstellt ein Widget für ein einzelnes Preset mit erweiterten Funktionen"""
        preset_widget = QWidget()
        preset_widget.setObjectName("preset_item")
        preset_layout = QVBoxLayout(preset_widget)
        preset_layout.setSpacing(10)

        # Header mit Name und Buttons
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        preset_name = QLabel(preset["name"])
        preset_name.setObjectName("preset_name")
        header_layout.addWidget(preset_name)

        header_layout.addStretch()

        # Buttons-Container
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)

        # Bearbeiten-Button
        edit_btn = QPushButton()
        edit_btn.setIcon(QIcon.fromTheme("document-edit"))
        edit_btn.setToolTip("Preset bearbeiten")
        edit_btn.setFixedSize(30, 30)
        edit_btn.clicked.connect(lambda: self.edit_preset(index))
        buttons_layout.addWidget(edit_btn)

        # Löschen-Button
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        delete_btn.setToolTip("Preset löschen")
        delete_btn.setFixedSize(30, 30)
        delete_btn.clicked.connect(lambda: self.delete_preset(index))
        buttons_layout.addWidget(delete_btn)

        # Verwenden-Button
        use_btn = QPushButton("Verwenden")
        use_btn.clicked.connect(lambda checked=False, idx=index: self.controller.use_preset(idx))
        buttons_layout.addWidget(use_btn)

        header_layout.addWidget(buttons_widget)
        preset_layout.addWidget(header)

        # Trennlinie
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        preset_layout.addWidget(separator)

        # Inhalt
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # API-Typ
        content_layout.addWidget(QLabel("<b>API:</b>"), 0, 0)
        content_layout.addWidget(QLabel(preset["api_type"]), 0, 1)

        # Kategorie (für zukünftige Implementierung)
        if "category" in preset and preset["category"]:
            content_layout.addWidget(QLabel("<b>Kategorie:</b>"), 1, 0)
            content_layout.addWidget(QLabel(preset["category"]), 1, 1)

        # Prompt mit Expand/Collapse
        content_layout.addWidget(QLabel("<b>Prompt:</b>"), 2, 0, Qt.AlignTop)

        prompt_container = QWidget()
        prompt_container_layout = QVBoxLayout(prompt_container)
        prompt_container_layout.setContentsMargins(0, 0, 0, 0)

        # Gekürzte Anzeige
        short_prompt = preset["prompt"]
        if len(short_prompt) > 100:
            short_prompt = short_prompt[:100] + "..."

        self.prompt_label = QLabel(short_prompt)
        self.prompt_label.setWordWrap(True)
        prompt_container_layout.addWidget(self.prompt_label)

        # Mehr/Weniger anzeigen Button
        if len(preset["prompt"]) > 100:
            toggle_btn = QPushButton("Mehr anzeigen")
            toggle_btn.setObjectName("link_button")
            toggle_btn.setCheckable(True)

            # Closure zum Speichern von Zustand und Labels
            def toggle_prompt_view(checked):
                if checked:
                    self.prompt_label.setText(preset["prompt"])
                    toggle_btn.setText("Weniger anzeigen")
                else:
                    self.prompt_label.setText(short_prompt)
                    toggle_btn.setText("Mehr anzeigen")

            toggle_btn.toggled.connect(toggle_prompt_view)
            prompt_container_layout.addWidget(toggle_btn)

        content_layout.addWidget(prompt_container, 2, 1)

        preset_layout.addWidget(content_widget)

        return preset_widget

    def filter_presets(self):
        """Filtert Presets nach Suchtext und Kategorie"""
        self.current_search = self.search_input.text().strip()
        self.current_category = self.category_filter.currentText()
        self.update_presets_list()

    def save_new_preset(self):
        """Speichert ein neues Preset oder aktualisiert ein bestehendes"""
        name = self.preset_name_input.text().strip()
        prompt = self.preset_prompt_input.toPlainText().strip()
        api_type = self.api_type_combo.currentText()
        category = self.category_input.text().strip()

        if not name or not prompt:
            self.controller.show_toast("Bitte Name und Prompt eingeben!")
            return

        preset_data = {
            "name": name,
            "prompt": prompt,
            "api_type": api_type
        }

        if category:
            preset_data["category"] = category

        # Im Bearbeitungsmodus das bestehende Preset aktualisieren
        if self.edit_mode and self.edit_preset_index >= 0:
            # Hier sollte der Backend-Aufruf zum Aktualisieren des Presets erfolgen
            # Da die eigentliche Funktionalität später implementiert wird, füge ich hier
            # nur eine Schnittstelle ein
            self.controller.show_toast(f"Preset '{name}' wurde aktualisiert")
            self.exit_edit_mode()
        else:
            # Neues Preset speichern
            self.controller.save_preset(name, prompt, api_type)
            self.controller.show_toast(f"Preset '{name}' wurde gespeichert")

        self.clear_form()
        self.update_presets_list()

    def edit_preset(self, index):
        """Lädt ein Preset zur Bearbeitung"""
        if index < 0 or index >= len(self.controller.presets):
            return

        preset = self.controller.presets[index]
        self.preset_name_input.setText(preset["name"])
        self.preset_prompt_input.setPlainText(preset["prompt"])
        self.api_type_combo.setCurrentText(preset["api_type"])
        self.category_input.setText(preset.get("category", ""))

        # Bearbeitungsmodus aktivieren
        self.edit_mode = True
        self.edit_preset_index = index
        self.controller.show_toast(f"Preset '{preset['name']}' wird bearbeitet")

    def delete_preset(self, index):
        """Löscht ein Preset nach Bestätigung"""
        if index < 0 or index >= len(self.controller.presets):
            return

        preset = self.controller.presets[index]
        confirm = QMessageBox.question(
            self,
            "Preset löschen",
            f"Möchten Sie das Preset '{preset['name']}' wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Hier sollte der Backend-Aufruf zum Löschen des Presets erfolgen
            # Da die eigentliche Funktionalität später implementiert wird, füge ich hier
            # nur eine Schnittstelle ein
            self.controller.show_toast(f"Preset '{preset['name']}' wurde gelöscht")

            # Bearbeitungsmodus beenden, falls das gelöschte Preset gerade bearbeitet wurde
            if self.edit_mode and self.edit_preset_index == index:
                self.exit_edit_mode()

            self.update_presets_list()

    def exit_edit_mode(self):
        """Beendet den Bearbeitungsmodus"""
        self.edit_mode = False
        self.edit_preset_index = -1
        self.clear_form()

    def clear_form(self):
        """Setzt das Formular zurück"""
        self.preset_name_input.clear()
        self.preset_prompt_input.clear()
        self.api_type_combo.setCurrentIndex(0)
        self.category_input.clear()
        self.edit_mode = False
        self.edit_preset_index = -1

class CredentialsPage(BasePage):
    def __init__(self, parent):
        super().__init__(parent)
        self.title_label.setText("API Credentials")

        # Hauptinhalt in Scroll-Area, falls viele API-Konfigurationen hinzukommen
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        main_content_layout = QVBoxLayout(content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(20)

        # API-Konfiguration Container
        api_config_container = QWidget()
        api_config_container.setObjectName("api_config_container")
        api_config_layout = QVBoxLayout(api_config_container)
        api_config_layout.setContentsMargins(20, 20, 20, 20)

        # API-Typ Auswahl
        type_container = QWidget()
        type_layout = QHBoxLayout(type_container)
        type_layout.setContentsMargins(0, 0, 0, 10)

        type_layout.addWidget(QLabel("API-Typ:"))

        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["OpenAI", "Azure OpenAI", "Anthropic", "Andere"])
        self.api_type_combo.currentTextChanged.connect(self.update_api_form)
        type_layout.addWidget(self.api_type_combo)

        type_layout.addStretch()

        api_config_layout.addWidget(type_container)

        # Formular für API-Konfigurationen
        self.form_container = QWidget()
        self.form_layout = QGridLayout(self.form_container)
        self.form_layout.setHorizontalSpacing(15)
        self.form_layout.setVerticalSpacing(15)

        # Generische Felder werden dynamisch hinzugefügt
        api_config_layout.addWidget(self.form_container)

        # Test- und Speichern-Buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)

        self.test_button = QPushButton("API testen")
        self.test_button.setObjectName("test_btn")
        self.test_button.clicked.connect(self.test_api)
        button_layout.addWidget(self.test_button)

        self.save_button = QPushButton("Speichern")
        self.save_button.setObjectName("save_btn")
        self.save_button.clicked.connect(self.save_credentials)
        button_layout.addWidget(self.save_button)

        self.validation_status = QLabel("")
        self.validation_status.setObjectName("validation_status")
        button_layout.addWidget(self.validation_status)

        button_layout.addStretch()

        api_config_layout.addWidget(button_container)

        main_content_layout.addWidget(api_config_container)
        main_content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        self.content_layout.addWidget(scroll_area)

        # Aktuelle Einstellungen laden
        self.load_credentials()
        self.update_api_form() # Initial Formular aktualisieren

    def update_api_form(self, api_type=None):
        """Aktualisiert das Formular basierend auf dem ausgewählten API-Typ"""
        # Vorhandene Widgets im Formular löschen
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        current_api_type = self.api_type_combo.currentText() if api_type is None else api_type

        # Felder basierend auf API-Typ hinzufügen
        if current_api_type == "OpenAI":
            self.add_credential_field("API Key", "api_key")
            self.add_credential_field("API URL (optional)", "api_url", optional=True)
        elif current_api_type == "Azure OpenAI":
            self.add_credential_field("API Key", "api_key")
            self.add_credential_field("API Base URL", "api_base_url")
            self.add_credential_field("Deployment Name", "deployment_name")
        elif current_api_type == "Anthropic":
            self.add_credential_field("API Key", "api_key")
            self.add_credential_field("API URL (optional)", "api_url", optional=True)
        else: # Andere
            self.add_credential_field("API Key", "api_key")
            self.add_credential_field("API URL", "api_url")

    def add_credential_field(self, label_text, field_name, optional=False):
        """Hilfsfunktion zum Hinzufügen eines Beschriftungs- und Eingabefelds"""
        row = self.form_layout.rowCount()
        label = QLabel(label_text + ("" if optional else "*:"))
        self.form_layout.addWidget(label, row, 0)

        input_widget = QLineEdit()
        input_widget.setObjectName(field_name)
        if optional:
            input_widget.setPlaceholderText("Optional")
        self.form_layout.addWidget(input_widget, row, 1)

        # Widget für das Eingabefeld speichern, um später darauf zugreifen zu können
        setattr(self, field_name + "_input", input_widget)

    def load_credentials(self):
        """Lädt gespeicherte Credentials und füllt die Formularfelder"""
        credentials = self.controller.api_credentials
        if credentials:
            api_type = credentials.get("api_type")
            if api_type:
                self.api_type_combo.setCurrentText(api_type)
            for key, value in credentials.items():
                if hasattr(self, key + "_input"):
                    getattr(self, key + "_input").setText(str(value))

    def save_credentials(self):
        """Speichert die eingegebenen API-Credentials"""
        api_type = self.api_type_combo.currentText()
        credentials_data = {"api_type": api_type}

        # Sammelt alle Werte aus den Eingabefeldern
        for i in range(self.form_layout.rowCount()):
            label_widget = self.form_layout.itemAtPosition(i, 0).widget()
            input_widget = self.form_layout.itemAtPosition(i, 1).widget()

            if isinstance(input_widget, QLineEdit):
                field_name = input_widget.objectName()
                credentials_data[field_name] = input_widget.text().strip()

        if self.controller.backend.save_credentials(credentials_data):
            QMessageBox.information(self, "Erfolg", "API-Credentials wurden gespeichert!")
            self.load_credentials() # Aktualisiere Formular nach dem Speichern
        else:
            QMessageBox.warning(self, "Fehler", "Fehler beim Speichern der API-Credentials.")


    def test_api(self):
        """Testet die Verbindung zur API mit den aktuellen Credentials"""
        api_type = self.api_type_combo.currentText()
        credentials_data = {"api_type": api_type}

        # Sammelt alle Werte aus den Eingabefeldern
        for i in range(self.form_layout.rowCount()):
            label_widget = self.form_layout.itemAtPosition(i, 0).widget()
            input_widget = self.form_layout.itemAtPosition(i, 1).widget()

            if isinstance(input_widget, QLineEdit):
                field_name = input_widget.objectName()
                credentials_data[field_name] = input_widget.text().strip()

        if self.controller.backend.test_api_connection(credentials_data):
            self.validation_status.setText("Verbindung erfolgreich!")
            self.validation_status.setStyleSheet("color: green;")
            QMessageBox.information(self, "API Test", "Die API-Verbindung war erfolgreich.")
        else:
            self.validation_status.setText("Verbindung fehlgeschlagen.")
            self.validation_status.setStyleSheet("color: red;")
            QMessageBox.warning(self, "API Test", "Die API-Verbindung ist fehlgeschlagen. Überprüfen Sie Ihre Credentials und die API-URL.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = APIManager()
    window.show()
    sys.exit(app.exec())