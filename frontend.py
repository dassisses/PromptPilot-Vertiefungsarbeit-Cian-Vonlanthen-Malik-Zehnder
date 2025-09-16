# This file was previously named main.py and is now renamed to frontend.py to reflect its role as the frontend (UI) part of the application.

import sys
import pyperclip
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFrame, QScrollArea, QMessageBox, QStackedWidget,
    QGridLayout, QSizePolicy
)
from backend import APIBackend

class APIManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("API Prompt Manager")
        self.setMinimumSize(900, 650)

        # Backend-Instanz
        self.backend = APIBackend()

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
        self.home_page = HomePage(self)
        self.credentials_page = CredentialsPage(self)

        self.page_stack.addWidget(self.home_page)
        self.page_stack.addWidget(self.credentials_page)

        main_layout.addWidget(self.page_stack)

        # Stylesheets anwenden
        self.apply_stylesheets()

        # Mit der Home-Seite starten
        self.page_stack.setCurrentIndex(0)

    def create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        logo_container = QWidget()
        logo_container.setObjectName("logo_container")
        logo_layout = QVBoxLayout(logo_container)
        app_title = QLabel("API Manager")
        app_title.setObjectName("app_title")
        app_title.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(app_title)
        sidebar_layout.addWidget(logo_container)
        menu_container = QWidget()
        menu_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(10, 20, 10, 20)
        menu_layout.setSpacing(10)
        home_btn = QPushButton("Home")
        home_btn.setObjectName("menu_button")
        home_btn.clicked.connect(lambda: self.page_stack.setCurrentIndex(0))
        api_btn = QPushButton("API Credentials")
        api_btn.setObjectName("menu_button")
        api_btn.clicked.connect(lambda: self.page_stack.setCurrentIndex(1))
        menu_layout.addWidget(home_btn)
        menu_layout.addWidget(api_btn)
        menu_layout.addStretch()
        sidebar_layout.addWidget(menu_container)

    def apply_stylesheets(self):
        self.setStyleSheet("""
            QWidget {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica', sans-serif;
                font-size: 14px;
            }
            #sidebar {
                background-color: #2c2c2c;
                border-right: 1px solid #3c3c3c;
            }
            #logo_container {
                padding: 20px 10px;
                background-color: #1e1e1e;
            }
            #app_title {
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            #menu_button {
                background-color: transparent;
                color: #cccccc;
                text-align: left;
                padding: 12px 15px;
                border: none;
                border-radius: 6px;
            }
            #menu_button:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QPushButton#save_btn {
                background-color: #198754;
            }
            QPushButton#save_btn:hover {
                background-color: #157347;
            }
            QPushButton#test_btn {
                background-color: #ffc107;
                color: #212529;
            }
            QPushButton#test_btn:hover {
                background-color: #ffca2c;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #86b7fe;
                outline: 2px solid rgba(13, 110, 253, 0.25);
            }
            QLabel {
                color: #212529;
            }
            #page_title {
                font-size: 24px;
                font-weight: bold;
                color: #212529;
                margin-bottom: 20px;
            }
            #preset_item {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e9ecef;
                padding: 15px;
            }
            #preset_item:hover {
                border-color: #dee2e6;
                background-color: #f8f9fa;
            }
            #preset_name {
                font-weight: bold;
                font-size: 16px;
            }
            #empty_message {
                color: #6c757d;
                font-style: italic;
            }
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
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(15)
        scroll_area.setWidget(self.presets_container)
        self.content_layout.addWidget(scroll_area)
        self.content_layout.setStretch(0, 1)
        form_container = QWidget()
        form_layout = QGridLayout(form_container)
        form_layout.setContentsMargins(0, 20, 0, 0)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(15)
        form_layout.addWidget(QLabel("<b>Neues Preset erstellen</b>"), 0, 0, 1, 2)
        form_layout.addWidget(QLabel("Name:"), 1, 0)
        self.preset_name_input = QLineEdit()
        form_layout.addWidget(self.preset_name_input, 1, 1)
        form_layout.addWidget(QLabel("Prompt:"), 2, 0)
        self.preset_prompt_input = QLineEdit()
        form_layout.addWidget(self.preset_prompt_input, 2, 1)
        form_layout.addWidget(QLabel("API-Typ:"), 3, 0)
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["chatgpt", "andere_api"])
        form_layout.addWidget(self.api_type_combo, 3, 1)
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        save_button = QPushButton("Preset speichern")
        save_button.setObjectName("save_btn")
        save_button.clicked.connect(self.save_new_preset)
        button_layout.addWidget(save_button)
        button_layout.addStretch()
        form_layout.addWidget(button_container, 4, 0, 1, 2)
        self.content_layout.addWidget(form_container)
        self.update_presets_list()
    def update_presets_list(self):
        for i in reversed(range(self.presets_layout.count())):
            self.presets_layout.itemAt(i).widget().deleteLater()
        if not self.controller.presets:
            empty_label = QLabel("Keine Presets vorhanden")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setObjectName("empty_message")
            self.presets_layout.addWidget(empty_label)
            self.presets_layout.addStretch()
            return
        for i, preset in enumerate(self.controller.presets):
            preset_widget = QWidget()
            preset_widget.setObjectName("preset_item")
            preset_layout = QHBoxLayout(preset_widget)
            preset_info = QVBoxLayout()
            preset_name = QLabel(preset["name"])
            preset_name.setObjectName("preset_name")
            preset_info.addWidget(preset_name)
            preset_desc = QLabel(f"API: {preset['api_type']} | Prompt: {preset['prompt'][:50]}...")
            preset_info.addWidget(preset_desc)
            preset_layout.addLayout(preset_info)
            preset_layout.addStretch()
            use_btn = QPushButton("Verwenden")
            use_btn.clicked.connect(lambda checked, idx=i: self.controller.use_preset(idx))
            preset_layout.addWidget(use_btn)
            self.presets_layout.addWidget(preset_widget)
        self.presets_layout.addStretch()
    def save_new_preset(self):
        name = self.preset_name_input.text().strip()
        prompt = self.preset_prompt_input.text().strip()
        api_type = self.api_type_combo.currentText()
        if not name or not prompt:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie einen Namen und einen Prompt ein!")
            return
        self.controller.save_preset(name, prompt, api_type)
        self.preset_name_input.clear()
        self.preset_prompt_input.clear()
        self.api_type_combo.setCurrentIndex(0)

class CredentialsPage(BasePage):
    def __init__(self, parent):
        super().__init__(parent)
        self.title_label.setText("API Credentials")
        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(15)
        form_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(self.controller.api_credentials.get("api_key", ""))
        form_layout.addWidget(self.api_key_input, 0, 1)
        form_layout.addWidget(QLabel("API URL:"), 1, 0)
        self.api_url_input = QLineEdit()
        self.api_url_input.setText(self.controller.api_credentials.get("api_url", "https://api.openai.com/v1"))
        form_layout.addWidget(self.api_url_input, 1, 1)
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        test_button = QPushButton("API testen")
        test_button.setObjectName("test_btn")
        test_button.clicked.connect(self.test_api)
        button_layout.addWidget(test_button)
        save_button = QPushButton("Speichern")
        save_button.setObjectName("save_btn")
        save_button.clicked.connect(self.save_credentials)
        button_layout.addWidget(save_button)
        button_layout.addStretch()
        form_layout.addWidget(button_container, 2, 0, 1, 2)
        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        self.content_layout.addWidget(form_widget)
        self.content_layout.addStretch()
    def test_api(self):
        api_key = self.api_key_input.text().strip()
        api_url = self.api_url_input.text().strip()
        if not api_key or not api_url:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie API-Key und API-URL ein!")
            return
        QMessageBox.information(self, "API-Test", "Dies ist ein Dummy-Test. In einer vollständigen Anwendung würde hier die API-Verbindung getestet werden.")
    def save_credentials(self):
        api_key = self.api_key_input.text().strip()
        api_url = self.api_url_input.text().strip()
        if not api_key or not api_url:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie API-Key und API-URL ein!")
            return
        self.controller.save_credentials(api_key, api_url)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = APIManager()
    window.show()
    sys.exit(app.exec())
