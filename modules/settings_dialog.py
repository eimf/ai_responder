"""
settings_dialog.py
------------------
A settings dialog where the user can enter their Azure OpenAI credentials
and select the AI provider/model.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QFrame,
    QFormLayout, QTabWidget, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from modules.settings_manager import SettingsManager


class SettingsDialog(QDialog):
    """Settings dialog for configuring AI credentials."""

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("AI Responder — Settings")
        self.setFixedWidth(480)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self._build_ui()
        self._load_values()

    # ------------------------------------------------------------------ #
    #  UI                                                                   #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #cccccc;
                font-family: 'Segoe UI';
                font-size: 10px;
            }
            QLineEdit, QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px 8px;
                font-family: 'Segoe UI';
                font-size: 10px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #0078D4;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #888;
                padding: 6px 16px;
                border: none;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: white;
                border-bottom: 2px solid #0078D4;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        main_layout.addWidget(title)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._azure_tab(), "Azure OpenAI")
        tabs.addTab(self._openai_tab(), "OpenAI / Custom")
        main_layout.addWidget(tabs)

        # Provider selector
        provider_row = QHBoxLayout()
        provider_lbl = QLabel("Active Provider:")
        provider_lbl.setStyleSheet("color: #888;")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["azure", "openai"])
        provider_row.addWidget(provider_lbl)
        provider_row.addWidget(self.provider_combo)
        provider_row.addStretch()
        main_layout.addLayout(provider_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #888;
                border: 1px solid #444; border-radius: 6px; padding: 0 16px;
            }
            QPushButton:hover { color: white; border-color: #888; }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(32)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4; color: white;
                border: none; border-radius: 6px; padding: 0 20px;
            }
            QPushButton:hover { background-color: #106EBE; }
        """)
        save_btn.clicked.connect(self._save)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        main_layout.addLayout(btn_row)

    def _azure_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.azure_endpoint = QLineEdit()
        self.azure_endpoint.setPlaceholderText("https://YOUR_RESOURCE.openai.azure.com/")

        self.azure_key = QLineEdit()
        self.azure_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_key.setPlaceholderText("Your Azure OpenAI API key")

        self.azure_deployment = QLineEdit()
        self.azure_deployment.setPlaceholderText("e.g. gpt-4o")

        self.azure_api_version = QLineEdit()
        self.azure_api_version.setPlaceholderText("e.g. 2024-02-01")

        form.addRow("Endpoint:", self.azure_endpoint)
        form.addRow("API Key:", self.azure_key)
        form.addRow("Deployment:", self.azure_deployment)
        form.addRow("API Version:", self.azure_api_version)

        note = QLabel(
            "Find these values in Azure Portal → Azure OpenAI → Keys and Endpoint."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #666; font-size: 9px;")
        form.addRow("", note)

        return tab

    def _openai_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.openai_base_url = QLineEdit()
        self.openai_base_url.setPlaceholderText(
            "Leave blank for api.openai.com  |  or e.g. http://localhost:11434/v1 for Ollama"
        )

        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setPlaceholderText("sk-...")

        self.openai_model = QLineEdit()
        self.openai_model.setPlaceholderText("e.g. gpt-4o-mini  or  llama3")

        form.addRow("Base URL:", self.openai_base_url)
        form.addRow("API Key:", self.openai_key)
        form.addRow("Model:", self.openai_model)

        note = QLabel(
            "Use this tab for standard OpenAI, or a local Ollama/LM Studio endpoint."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #666; font-size: 9px;")
        form.addRow("", note)

        return tab

    # ------------------------------------------------------------------ #
    #  Load / Save                                                          #
    # ------------------------------------------------------------------ #

    def _load_values(self):
        self.azure_endpoint.setText(self.settings.get("azure_endpoint"))
        self.azure_key.setText(self.settings.get("azure_api_key"))
        self.azure_deployment.setText(self.settings.get("azure_deployment"))
        self.azure_api_version.setText(self.settings.get("azure_api_version"))

        self.openai_base_url.setText(self.settings.get("openai_base_url"))
        self.openai_key.setText(self.settings.get("openai_api_key"))
        self.openai_model.setText(self.settings.get("openai_model"))

        provider = self.settings.get("provider", "azure")
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

    def _save(self):
        self.settings.update({
            "azure_endpoint": self.azure_endpoint.text().strip(),
            "azure_api_key": self.azure_key.text().strip(),
            "azure_deployment": self.azure_deployment.text().strip(),
            "azure_api_version": self.azure_api_version.text().strip(),
            "openai_base_url": self.openai_base_url.text().strip(),
            "openai_api_key": self.openai_key.text().strip(),
            "openai_model": self.openai_model.text().strip(),
            "provider": self.provider_combo.currentText(),
        })
        self.settings.save()
        self.accept()
