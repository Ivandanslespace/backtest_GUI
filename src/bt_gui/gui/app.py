"""Point d'entree graphique de l'application."""

from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


LIGHT_STYLESHEET = """
QWidget {
    background: #f5f7fb;
    color: #243040;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QMainWindow {
    background: #f5f7fb;
}
QFrame#NavigationCard {
    background: #ffffff;
    border: 1px solid #e4e9f2;
    border-radius: 20px;
    min-width: 240px;
}
QFrame#HeroCard, QFrame#Card {
    background: #ffffff;
    border: 1px solid #e4e9f2;
    border-radius: 20px;
}
QLabel#AppTitle {
    font-size: 22px;
    font-weight: 700;
}
QLabel#HeroTitle {
    font-size: 24px;
    font-weight: 700;
}
QLabel#SectionTitle {
    font-size: 18px;
    font-weight: 700;
}
QLabel#MutedLabel {
    color: #667085;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5b8dee, stop:1 #6f6bff);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4b7fe6, stop:1 #615ef8);
}
QPushButton#SecondaryButton {
    background: #eef3ff;
    color: #3658a7;
    border: 1px solid #d9e3fb;
}
QPushButton#SecondaryButton:hover {
    background: #e4ecff;
}
QLineEdit, QPlainTextEdit, QListWidget, QTableView, QTabWidget::pane {
    background: #fbfcfe;
    border: 1px solid #dbe3ef;
    border-radius: 12px;
    padding: 6px;
}
QComboBox {
    background: #fbfcfe;
    border: 1px solid #dbe3ef;
    border-radius: 12px;
    padding: 6px 34px 6px 8px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    border-left: 1px solid #dbe3ef;
    background: #f1f5fb;
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
}
QComboBox::down-arrow {
    width: 12px;
    height: 12px;
    margin-right: 8px;
}
QListWidget {
    padding: 8px;
}
QListWidget::item {
    border-radius: 10px;
    padding: 10px;
    margin: 3px 0;
}
QListWidget::item:selected {
    background: #edf2ff;
    color: #1f3f8e;
}
QListWidget#MetricsList {
    padding: 6px;
}
QListWidget#MetricsList::item {
    border-radius: 8px;
    padding: 6px 10px;
    margin: 2px;
}
QTabBar::tab {
    background: #eef3ff;
    border: 1px solid #dbe3ef;
    border-bottom: none;
    padding: 10px 18px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #244599;
}
QHeaderView::section {
    background: #eef3ff;
    border: none;
    padding: 8px;
    color: #3658a7;
    font-weight: 600;
}
QScrollArea {
    border: none;
}
QCheckBox {
    spacing: 8px;
}
"""


def create_application() -> QApplication:
    """Initialise l'application Qt."""

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Backtest GUI")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(LIGHT_STYLESHEET)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f5f7fb"))
    palette.setColor(QPalette.Base, QColor("#fbfcfe"))
    palette.setColor(QPalette.Button, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#5b8dee"))
    app.setPalette(palette)
    return app


def run_app() -> int:
    """Lance la fenetre principale."""

    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
