"""Vue d'historique des runs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ma_librairie.core.artifacts import list_run_directories, read_manifest


class HistoryView(QWidget):
    """Page de consultation de l'historique des runs."""

    run_selected = Signal(str)

    def __init__(self, user_provider, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._user_provider = user_provider
        self._build_ui()
        self.refresh_history()

    def _build_ui(self) -> None:
        """Construit l'interface."""

        root_layout = QVBoxLayout(self)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        title_box = QVBoxLayout()
        title = QLabel("Historique")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Consultez les runs sauvegardes dans le dossier runs/.")
        subtitle.setObjectName("MutedLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        self.refresh_button = QPushButton("Actualiser")
        self.refresh_button.setObjectName("SecondaryButton")
        self.open_button = QPushButton("Ouvrir le dossier")
        self.open_button.setObjectName("SecondaryButton")
        header_layout.addLayout(title_box, 1)
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.open_button)
        root_layout.addWidget(header)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.history_list = QListWidget()
        card_layout.addWidget(self.history_list)
        root_layout.addWidget(card, 1)

        self.refresh_button.clicked.connect(self.refresh_history)
        self.open_button.clicked.connect(self.open_selected_directory)
        self.history_list.itemDoubleClicked.connect(self._emit_selected_item)
        self.history_list.itemSelectionChanged.connect(self._emit_selected)

    def refresh_history(self) -> None:
        """Recharge la liste des runs disponibles."""

        user_name = self._user_provider()
        self.history_list.clear()
        for run_dir in list_run_directories(user_name):
            manifest = read_manifest(run_dir)
            status = manifest.get("status", "unknown")
            bench = manifest.get("bench", "-")
            message = manifest.get("message", "")
            text = f"{run_dir.name} | {status} | {bench} | {message}"
            item = QListWidgetItem(text)
            item.setData(256, str(run_dir))
            self.history_list.addItem(item)

    def _emit_selected_item(self, item: QListWidgetItem) -> None:
        """Emet le chemin du run lors d'un double clic."""

        run_dir = item.data(256)
        if run_dir:
            self.run_selected.emit(run_dir)

    def _emit_selected(self) -> None:
        """Emet le chemin du run selectionne."""

        item = self.history_list.currentItem()
        if item is None:
            return
        run_dir = item.data(256)
        if run_dir:
            self.run_selected.emit(run_dir)

    def open_selected_directory(self) -> None:
        """Ouvre le dossier du run selectionne."""

        item = self.history_list.currentItem()
        if item is None:
            return
        run_dir = item.data(256)
        if run_dir and Path(run_dir).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(run_dir))
