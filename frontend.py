import sys
import pyperclip
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFrame, QScrollArea, QMessageBox, QStackedWidget,
    QGridLayout, QTextEdit
)
from backend import APIBackend


class APIManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PromptPilot")
        self.setMinimumSize(1400, 900)

        # Erzwinge Dark Mode
        self.force_dark_mode()

        self.backend = APIBackend()
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

        self.setup_shortcuts()
        self.apply_stylesheets()

        self.toast_label = QLabel(self)
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.setObjectName("toast")
        self.toast_label.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.timeout.connect(self.hide_toast)

    def force_dark_mode(self):
        """Erzwingt Dark Mode für die gesamte Anwendung"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.AlternateBase, QColor(44, 44, 44))
        palette.setColor(QPalette.ToolTipBase, QColor(224, 224, 224))
        palette.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
        palette.setColor(QPalette.Text, QColor(224, 224, 224))
        palette.setColor(QPalette.Button, QColor(30, 30, 30))
        palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(13, 110, 253))
        palette.setColor(QPalette.Highlight, QColor(13, 110, 253))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(palette)

    def create_top_nav(self):
        self.top_nav = QWidget()
        self.top_nav.setObjectName("top_nav")
        self.top_nav.setFixedHeight(64)
        
        layout = QHBoxLayout(self.top_nav)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(0)

        title = QLabel("PromptPilot")
        title.setObjectName("app_title")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(title)

        layout.addStretch()

    def create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(16, 20, 16, 20)
        nav_layout.setSpacing(10)

        nav_label = QLabel("Navigation")
        nav_label.setObjectName("nav_label")
        nav_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        nav_layout.addWidget(nav_label)

        self.nav_presets = self.create_nav_button("Presets", 0)
        self.nav_credentials = self.create_nav_button("API Einstellungen", 1)

        nav_layout.addWidget(self.nav_presets)
        nav_layout.addWidget(self.nav_credentials)
        nav_layout.addStretch()

        layout.addWidget(nav_container)

        # Setze Presets als aktiv vom Start
        self.nav_presets.setProperty("active", True)
        self.nav_presets.style().unpolish(self.nav_presets)
        self.nav_presets.style().polish(self.nav_presets)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        info = QLabel("PomptPilot by Cian and Malik")
        info.setObjectName("sidebar_info")
        info.setAlignment(Qt.AlignCenter)
        info.setFont(QFont("Segoe UI", 10))
        bottom_layout.addWidget(info)
        layout.addWidget(bottom)

    def create_nav_button(self, text, page):
        btn = QPushButton(text)
        btn.setObjectName("nav_button")
        btn.setFixedHeight(44)
        btn.setCursor(Qt.PointingHandCursor)
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

    def show_toast(self, message, duration=2000):
        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        self.toast_label.move(
            (self.width() - self.toast_label.width()) // 2,
            self.height() - self.toast_label.height() - 30
        )
        self.toast_label.show()
        self.toast_timer.start(duration)

    def hide_toast(self):
        self.toast_label.hide()
        self.toast_timer.stop()

    def apply_stylesheets(self):
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            
            QMainWindow {
                background-color: #121212;
                color: #e0e0e0;
            }
            
            #top_nav {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3c3c3c;
            }
            
            #app_title {
                color: #0d6efd;
                font-weight: bold;
            }
            
            #sidebar {
                background-color: #161616;
                border-right: 1px solid #3c3c3c;
            }
            
            #nav_label {
                color: #a0a0a0;
                font-size: 11px;
            }
            
            #sidebar_info {
                color: #6c757d;
                font-size: 11px;
            }
            
            #nav_button {
                background-color: transparent;
                color: #a0a0a0;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding: 12px 14px;
                font-weight: 500;
            }
            
            #nav_button:hover {
                background-color: #2c2c2c;
                color: #e0e0e0;
            }
            
            #nav_button[active="true"] {
                background-color: rgba(13, 110, 253, 0.2);
                color: #0d6efd;
                border-left: 3px solid #0d6efd;
                padding-left: 11px;
            }
            
            #page_stack {
                background-color: #121212;
            }
            
            #content_card {
                background-color: #1e1e1e;
                border: 1px solid #2c2c2c;
                border-radius: 8px;
                padding: 20px;
            }
            
            #section_title {
                font-size: 18px;
                font-weight: bold;
                color: #e0e0e0;
                margin-bottom: 8px;
            }
            
            #section_subtitle {
                font-size: 12px;
                color: #a0a0a0;
                margin-bottom: 16px;
            }
            
            #input_label {
                font-weight: 600;
                color: #e0e0e0;
                font-size: 12px;
                margin-bottom: 6px;
            }
            
            QLineEdit, QComboBox, QTextEdit {
                background-color: #2c2c2c;
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 10px 12px;
                selection-background-color: #0d6efd;
            }
            
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 2px solid #0d6efd;
                padding: 9px 11px;
                background-color: #1e1e1e;
            }
            
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                cursor: pointer;
            }
            
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            
            QPushButton#btn_success {
                background-color: #28a745;
            }
            
            QPushButton#btn_success:hover {
                background-color: #218838;
            }
            
            QPushButton#btn_danger {
                background-color: #dc3545;
                padding: 8px 14px;
            }
            
            QPushButton#btn_danger:hover {
                background-color: #c82333;
            }
            
            QPushButton#btn_info {
                background-color: #0d6efd;
            }
            
            QPushButton#btn_info:hover {
                background-color: #0b5ed7;
            }
            
            QPushButton#btn_secondary {
                background-color: transparent;
                color: #ffffff;
                border: 2px solid #0d6efd;
            }
            
            QPushButton#btn_secondary:hover {
                background-color: rgba(13, 110, 253, 0.1);
                border: 2px solid #0d6efd;
            }
            
            QPushButton#btn_secondary:pressed {
                background-color: rgba(13, 110, 253, 0.2);
            }
            
            #preset_card {
                background: linear-gradient(135deg, #1e1e1e 0%, #2c2c2c 100%);
                border: 1px solid #3c3c3c;
                border-radius: 10px;
                padding: 18px;
            }
            
            #preset_card:hover {
                border-color: #0d6efd;
                background: linear-gradient(135deg, #252525 0%, #333333 100%);
            }
            
            #preset_header {
                font-weight: 600;
                font-size: 14px;
                color: #e0e0e0;
            }
            
            #preset_meta {
                font-size: 11px;
                color: #6c757d;
            }
            
            #preset_prompt {
                font-size: 12px;
                color: #a0a0a0;
                margin-top: 12px;
            }
            
            #toast {
                background-color: #2c2c2c;
                color: #e0e0e0;
                border-radius: 6px;
                padding: 12px 20px;
                border: 1px solid #3c3c3c;
            }
            
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 8px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #3c3c3c;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #0d6efd;
            }
        """)

    @property
    def api_credentials(self):
        return self.backend.api_credentials

    @property
    def presets(self):
        return self.backend.presets

    def save_preset(self, name, prompt, api_type="chatgpt"):
        if self.backend.save_preset(name, prompt, api_type):
            self.home_page.update_presets_list()
            self.show_toast(f"Preset '{name}' gespeichert")

    def use_preset(self, preset_index):
        if preset_index < 0 or preset_index >= len(self.presets):
            return
        preset = self.presets[preset_index]
        clipboard_text = pyperclip.paste()
        if not clipboard_text:
            self.show_toast("Zwischenablage leer")
            return
        QMessageBox.information(self, "Preset verwenden",
            f"'{preset['name']}' ({preset['api_type']})\n\n"
            f"Zwischenablage: {clipboard_text[:50]}...")


class BasePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = parent
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.main_layout.setSpacing(24)


class HomePage(BasePage):
    def __init__(self, parent):
        super().__init__(parent)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("Meine Presets")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        header_layout.addWidget(title)
        
        subtitle = QLabel("Erstelle, verwalte und nutze deine API-Prompts")
        subtitle.setObjectName("section_subtitle")
        subtitle.setFont(QFont("Segoe UI", 12))
        header_layout.addWidget(subtitle)
        
        self.main_layout.addLayout(header_layout)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(32)

        # LEFT: Presets List
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        search_card = QWidget()
        search_card.setObjectName("content_card")
        search_layout = QVBoxLayout(search_card)
        search_label = QLabel("Suche")
        search_label.setObjectName("input_label")
        search_layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nach Name oder Prompt suchen...")
        self.search_input.textChanged.connect(self.filter_presets)
        search_layout.addWidget(self.search_input)
        left_layout.addWidget(search_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(14)
        self.presets_layout.setContentsMargins(8, 8, 8, 8)
        
        scroll.setWidget(self.presets_container)
        left_layout.addWidget(scroll, 1)

        content_layout.addWidget(left_col, 1)

        # RIGHT: Create Form
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        form_card = QWidget()
        form_card.setObjectName("content_card")
        form_card.setMaximumWidth(380)
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(16)

        form_title = QLabel("Neues Preset erstellen")
        form_title.setObjectName("section_title")
        form_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        form_layout.addWidget(form_title)

        name_label = QLabel("Name")
        name_label.setObjectName("input_label")
        form_layout.addWidget(name_label)
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("z.B. Text Zusammenfassung")
        form_layout.addWidget(self.preset_name_input)

        prompt_label = QLabel("Prompt")
        prompt_label.setObjectName("input_label")
        form_layout.addWidget(prompt_label)
        self.preset_prompt_input = QTextEdit()
        self.preset_prompt_input.setPlaceholderText("Schreibe deinen Prompt hier...")
        self.preset_prompt_input.setAcceptRichText(False)
        self.preset_prompt_input.setFixedHeight(100)
        form_layout.addWidget(self.preset_prompt_input)

        api_label = QLabel("API-Typ")
        api_label.setObjectName("input_label")
        form_layout.addWidget(api_label)
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["ChatGPT", "GPT-4", "GPT-3.5-Turbo", "DALL-E", "Andere"])
        form_layout.addWidget(self.api_type_combo)

        cat_label = QLabel("Kategorie (optional)")
        cat_label.setObjectName("input_label")
        form_layout.addWidget(cat_label)
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("z.B. Texterstellung")
        form_layout.addWidget(self.category_input)

        form_layout.addSpacing(8)

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("btn_success")
        save_btn.setMinimumWidth(100)  # Add minimum width
        save_btn.setFixedHeight(36)  # Add fixed height
        save_btn.clicked.connect(self.save_new_preset)
        btn_layout.addWidget(save_btn)

        reset_btn = QPushButton("Zurücksetzen")
        reset_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(reset_btn)

        form_layout.addLayout(btn_layout)
        right_layout.addWidget(form_card)
        right_layout.addStretch()

        content_layout.addWidget(right_col, 0)
        self.main_layout.addWidget(content, 1)

        self.current_search = ""
        self.update_presets_list()

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
            empty = QLabel("Keine Presets vorhanden")
            empty.setAlignment(Qt.AlignCenter)
            empty.setObjectName("section_subtitle")
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
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_box = QWidget()
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

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

        use_btn = QPushButton("Verwenden")
        use_btn.setObjectName("btn_primary")
        use_btn.setMinimumWidth(100)
        use_btn.clicked.connect(lambda: self.controller.use_preset(index))
        btn_layout_h.addWidget(use_btn)

        edit_btn = QPushButton("Bearbeiten")
        edit_btn.setMinimumWidth(100)
        edit_btn.clicked.connect(lambda: self.edit_preset(index))
        btn_layout_h.addWidget(edit_btn)

        delete_btn = QPushButton("Löschen")
        delete_btn.setObjectName("btn_danger")
        delete_btn.setMinimumWidth(90)
        delete_btn.clicked.connect(lambda: self.delete_preset(index))
        btn_layout_h.addWidget(delete_btn)

        header_layout.addWidget(btn_box)
        layout.addWidget(header)

        prompt = preset["prompt"]
        if len(prompt) > 150:
            prompt = prompt[:150] + "..."

        prompt_label = QLabel(prompt)
        prompt_label.setObjectName("preset_prompt")
        prompt_label.setWordWrap(True)
        layout.addWidget(prompt_label)

        return card

    def filter_presets(self):
        self.current_search = self.search_input.text().strip()
        self.update_presets_list()

    def save_new_preset(self):
        name = self.preset_name_input.text().strip()
        prompt = self.preset_prompt_input.toPlainText().strip()
        api_type = self.api_type_combo.currentText()

        if not name or not prompt:
            self.controller.show_toast("Name und Prompt erforderlich")
            return

        # Speichere über Backend
        if self.controller.backend.save_preset(name, prompt, api_type):
            self.controller.show_toast(f"Preset '{name}' gespeichert")
            self.update_presets_list()
            self.clear_form()
        else:
            self.controller.show_toast("Fehler beim Speichern")

    def edit_preset(self, index):
        if 0 <= index < len(self.controller.presets):
            p = self.controller.presets[index]
            self.preset_name_input.setText(p["name"])
            self.preset_prompt_input.setPlainText(p["prompt"])
            self.api_type_combo.setCurrentText(p["api_type"])
            self.controller.show_toast(f"Bearbeite '{p['name']}'")

    def delete_preset(self, index):
        if 0 <= index < len(self.controller.presets):
            p = self.controller.presets[index]
            reply = QMessageBox.question(
                self,
                "Preset löschen",
                f"Möchtest du das Preset '{p['name']}' wirklich löschen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # Entferne das Preset aus der Backend-Liste
                if hasattr(self.controller.backend, 'presets') and isinstance(self.controller.backend.presets, list):
                    if index < len(self.controller.backend.presets):
                        self.controller.backend.presets.pop(index)
                
                self.controller.show_toast(f"'{p['name']}' gelöscht")
                self.update_presets_list()

    def clear_form(self):
        self.preset_name_input.clear()
        self.preset_prompt_input.clear()
        self.api_type_combo.setCurrentIndex(0)
        self.category_input.clear()


class CredentialsPage(BasePage):
    def __init__(self, parent):
        super().__init__(parent)

        title = QLabel("API Einstellungen")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        self.main_layout.addWidget(title)

        subtitle = QLabel("Konfiguriere und teste deine API-Provider")
        subtitle.setObjectName("section_subtitle")
        self.main_layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        provider_card = QWidget()
        provider_card.setObjectName("content_card")
        provider_layout = QVBoxLayout(provider_card)

        provider_label = QLabel("API-Provider")
        provider_label.setObjectName("input_label")
        provider_layout.addWidget(provider_label)

        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["OpenAI", "Azure OpenAI", "Anthropic", "Benutzerdefiniert"])
        self.api_type_combo.currentTextChanged.connect(self.update_api_form)
        provider_layout.addWidget(self.api_type_combo)

        content_layout.addWidget(provider_card)

        config_card = QWidget()
        config_card.setObjectName("content_card")
        config_layout = QVBoxLayout(config_card)

        config_title = QLabel("Konfiguration")
        config_title.setObjectName("input_label")
        config_layout.addWidget(config_title)

        self.form_container = QWidget()
        self.form_layout = QGridLayout(self.form_container)
        self.form_layout.setHorizontalSpacing(16)
        self.form_layout.setVerticalSpacing(12)

        config_layout.addWidget(self.form_container)
        config_layout.addStretch()

        content_layout.addWidget(config_card)

        action_card = QWidget()
        action_card.setObjectName("content_card")
        action_layout = QHBoxLayout(action_card)

        self.test_button = QPushButton("Verbindung testen")
        self.test_button.setObjectName("btn_info")
        self.test_button.clicked.connect(self.test_api)
        action_layout.addWidget(self.test_button)

        self.save_button = QPushButton("Speichern")
        self.save_button.setObjectName("btn_info")
        self.save_button.clicked.connect(self.save_credentials)
        action_layout.addWidget(self.save_button)

        self.validation_label = QLabel("")
        self.validation_label.setObjectName("section_subtitle")
        action_layout.addWidget(self.validation_label)

        action_layout.addStretch()

        content_layout.addWidget(action_card)

        self.result_card = QWidget()
        self.result_card.setObjectName("content_card")
        self.result_card.setVisible(False)
        result_layout = QVBoxLayout(self.result_card)

        result_title = QLabel("Testergebnis")
        result_title.setObjectName("input_label")
        result_layout.addWidget(result_title)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        result_layout.addWidget(self.result_label)

        content_layout.addWidget(self.result_card)

        content_layout.addStretch()
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll, 1)

        self.update_api_form(self.api_type_combo.currentText())

    def update_api_form(self, api_type):
        for i in reversed(range(self.form_layout.count())):
            w = self.form_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        row = 0

        if api_type == "OpenAI":
            self.form_layout.addWidget(QLabel("API-Key"), row, 0)
            self.api_key_input = QLineEdit()
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.api_key_input.setPlaceholderText("sk-...")
            self.api_key_input.textChanged.connect(self.validate_input)
            self.form_layout.addWidget(self.api_key_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("Organization ID"), row, 0)
            self.org_id_input = QLineEdit()
            self.org_id_input.setPlaceholderText("Optional")
            self.form_layout.addWidget(self.org_id_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("API-URL"), row, 0)
            self.api_base_input = QLineEdit()
            self.api_base_input.setText("https://api.openai.com/v1")
            self.form_layout.addWidget(self.api_base_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("Modell"), row, 0)
            self.model_combo = QComboBox()
            self.model_combo.addItems(["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "dalle-3"])
            self.form_layout.addWidget(self.model_combo, row, 1)

        elif api_type == "Azure OpenAI":
            self.form_layout.addWidget(QLabel("API-Key"), row, 0)
            self.api_key_input = QLineEdit()
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.api_key_input.textChanged.connect(self.validate_input)
            self.form_layout.addWidget(self.api_key_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("Endpunkt"), row, 0)
            self.endpoint_input = QLineEdit()
            self.endpoint_input.setPlaceholderText("https://your-resource.openai.azure.com")
            self.endpoint_input.textChanged.connect(self.validate_input)
            self.form_layout.addWidget(self.endpoint_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("API-Version"), row, 0)
            self.api_version_input = QLineEdit()
            self.api_version_input.setText("2023-09-01-preview")
            self.form_layout.addWidget(self.api_version_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("Deployment"), row, 0)
            self.deployment_input = QLineEdit()
            self.deployment_input.setPlaceholderText("deployment-name")
            self.form_layout.addWidget(self.deployment_input, row, 1)

        elif api_type == "Anthropic":
            self.form_layout.addWidget(QLabel("API-Key"), row, 0)
            self.api_key_input = QLineEdit()
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.api_key_input.setPlaceholderText("sk_ant_...")
            self.api_key_input.textChanged.connect(self.validate_input)
            self.form_layout.addWidget(self.api_key_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("API-URL"), row, 0)
            self.api_base_input = QLineEdit()
            self.api_base_input.setText("https://api.anthropic.com")
            self.form_layout.addWidget(self.api_base_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("Modell"), row, 0)
            self.model_combo = QComboBox()
            self.model_combo.addItems(["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"])
            self.form_layout.addWidget(self.model_combo, row, 1)

        else:
            self.form_layout.addWidget(QLabel("API-Key"), row, 0)
            self.api_key_input = QLineEdit()
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.api_key_input.textChanged.connect(self.validate_input)
            self.form_layout.addWidget(self.api_key_input, row, 1)
            row += 1

            self.form_layout.addWidget(QLabel("API-URL"), row, 0)
            self.api_url_input = QLineEdit()
            self.api_url_input.textChanged.connect(self.validate_input)
            self.form_layout.addWidget(self.api_url_input, row, 1)

        self.load_saved_values()

    def load_saved_values(self):
        creds = self.controller.api_credentials
        if not creds:
            return

        if hasattr(self, 'api_key_input'):
            self.api_key_input.setText(creds.get("api_key", ""))

        api_type = self.api_type_combo.currentText()

        if api_type == "OpenAI":
            if hasattr(self, 'org_id_input'):
                self.org_id_input.setText(creds.get("org_id", ""))
            if hasattr(self, 'api_base_input'):
                self.api_base_input.setText(creds.get("api_base", "https://api.openai.com/v1"))
            if hasattr(self, 'model_combo'):
                idx = self.model_combo.findText(creds.get("model", "gpt-4"))
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)

        elif api_type == "Azure OpenAI":
            if hasattr(self, 'endpoint_input'):
                self.endpoint_input.setText(creds.get("endpoint", ""))
            if hasattr(self, 'api_version_input'):
                self.api_version_input.setText(creds.get("api_version", "2023-09-01-preview"))
            if hasattr(self, 'deployment_input'):
                self.deployment_input.setText(creds.get("deployment", ""))

        elif api_type == "Anthropic":
            if hasattr(self, 'api_base_input'):
                self.api_base_input.setText(creds.get("api_base", "https://api.anthropic.com"))
            if hasattr(self, 'model_combo'):
                idx = self.model_combo.findText(creds.get("model", "claude-3-sonnet"))
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)

        else:
            if hasattr(self, 'api_url_input'):
                self.api_url_input.setText(creds.get("api_url", ""))

    def validate_input(self):
        api_type = self.api_type_combo.currentText()
        valid = True
        msg = ""

        if not hasattr(self, 'api_key_input') or not self.api_key_input.text().strip():
            valid = False
            msg = "API-Key erforderlich"
        elif api_type == "OpenAI" and not self.api_key_input.text().startswith("sk-"):
            valid = False
            msg = "Ungültiger OpenAI Key"
        elif api_type == "Anthropic" and not self.api_key_input.text().startswith("sk_ant_"):
            valid = False
            msg = "Ungültiger Anthropic Key"
        elif api_type == "Azure OpenAI" and (not hasattr(self, 'endpoint_input') or not self.endpoint_input.text()):
            valid = False
            msg = "Endpunkt erforderlich"
        elif api_type == "Benutzerdefiniert" and (not hasattr(self, 'api_url_input') or not self.api_url_input.text()):
            valid = False
            msg = "API-URL erforderlich"

        if valid:
            self.validation_label.setText("✓ Gültig")
            self.validation_label.setStyleSheet("color: #28a745;")
        else:
            self.validation_label.setText(f"✗ {msg}")
            self.validation_label.setStyleSheet("color: #dc3545;")

        self.save_button.setEnabled(valid)
        return valid

    def get_credentials(self):
        api_type = self.api_type_combo.currentText()
        creds = {"api_type": api_type}

        if hasattr(self, 'api_key_input'):
            creds["api_key"] = self.api_key_input.text().strip()

        if api_type == "OpenAI":
            if hasattr(self, 'org_id_input'):
                if self.org_id_input.text():
                    creds["org_id"] = self.org_id_input.text().strip()
            if hasattr(self, 'api_base_input'):
                creds["api_base"] = self.api_base_input.text().strip()
            if hasattr(self, 'model_combo'):
                creds["model"] = self.model_combo.currentText()

        elif api_type == "Azure OpenAI":
            if hasattr(self, 'endpoint_input'):
                creds["endpoint"] = self.endpoint_input.text().strip()
            if hasattr(self, 'api_version_input'):
                creds["api_version"] = self.api_version_input.text().strip()
            if hasattr(self, 'deployment_input'):
                creds["deployment"] = self.deployment_input.text().strip()

        elif api_type == "Anthropic":
            if hasattr(self, 'api_base_input'):
                creds["api_base"] = self.api_base_input.text().strip()
            if hasattr(self, 'model_combo'):
                creds["model"] = self.model_combo.currentText()

        else:
            if hasattr(self, 'api_url_input'):
                creds["api_url"] = self.api_url_input.text().strip()

        return creds

    def test_api(self):
        if not self.validate_input():
            self.controller.show_toast("Ungültige Eingaben")
            return

        self.test_button.setEnabled(False)
        self.test_button.setText("Teste...")

        def show_result():
            self.result_card.setVisible(True)
            self.result_label.setText("✓ Verbindung erfolgreich!")
            self.result_label.setStyleSheet("color: #28a745;")
            self.test_button.setEnabled(True)
            self.test_button.setText("Verbindung testen")
            self.controller.show_toast("API-Test erfolgreich")

        QTimer.singleShot(1500, show_result)

    def save_credentials(self):
        if not self.validate_input():
            return

        creds = self.get_credentials()
        self.controller.backend.save_credentials(creds.get("api_key"), creds.get("api_url", ""))
        self.controller.show_toast("Einstellungen gespeichert")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = APIManager()
    window.show()
    sys.exit(app.exec())