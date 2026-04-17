"""Vue d'historique des runs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bt_gui.core.artifacts import list_run_directories, list_run_users, read_manifest


class HistoryView(QWidget):
    """Page de consultation de l'historique des runs."""

    run_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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
        self.user_filter_label = QLabel("Utilisateur")
        self.user_filter_label.setObjectName("MutedLabel")
        self.user_filter = QComboBox()
        self.user_filter.setMinimumWidth(220)
        self.refresh_button = QPushButton("Actualiser")
        self.refresh_button.setObjectName("SecondaryButton")
        self.open_result_button = QPushButton("Afficher le resultat")
        self.open_result_button.setObjectName("SecondaryButton")
        self.open_button = QPushButton("Ouvrir le dossier")
        self.open_button.setObjectName("SecondaryButton")
        header_layout.addLayout(title_box, 1)
        header_layout.addWidget(self.user_filter_label)
        header_layout.addWidget(self.user_filter)
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.open_result_button)
        header_layout.addWidget(self.open_button)
        root_layout.addWidget(header)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.history_list = QListWidget()
        card_layout.addWidget(self.history_list)
        root_layout.addWidget(card, 1)

        self.refresh_button.clicked.connect(self.refresh_history)
        self.user_filter.currentIndexChanged.connect(self._reload_history_list)
        self.open_result_button.clicked.connect(self._emit_selected)
        self.open_button.clicked.connect(self.open_selected_directory)
        self.history_list.itemDoubleClicked.connect(self._emit_selected_item)

    def refresh_history(self) -> None:
        """Recharge la liste des runs disponibles."""

        selected_user = self._selected_user()
        self.user_filter.blockSignals(True)
        self.user_filter.clear()
        self.user_filter.addItem("Tous les utilisateurs", None)
        for user_name in list_run_users():
            self.user_filter.addItem(user_name, userData=user_name)
        index = self.user_filter.findData(selected_user, role=Qt.UserRole)
        self.user_filter.setCurrentIndex(index if index >= 0 else 0)
        self.user_filter.blockSignals(False)
        self._reload_history_list()

    def _reload_history_list(self) -> None:
        """Recharge la liste d'historique selon l'utilisateur selectionne."""

        user_name = self._selected_user()
        self.history_list.clear()
        for run_dir in list_run_directories(user_name):
            manifest = read_manifest(run_dir)
            status = manifest.get("status", "unknown")
            bench = manifest.get("bench", "-")
            message = manifest.get("message", "")
            text = f"{run_dir.parent.name} | {run_dir.name} | {status} | {bench} | {message}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, str(run_dir))
            self.history_list.addItem(item)

    def _selected_user(self) -> str | None:
        """Retourne le filtre utilisateur actuellement selectionne."""

        if self.user_filter.count() == 0:
            return None
        return self.user_filter.currentData(Qt.UserRole)

    def _selected_run_dir(self) -> str | None:
        """Retourne le dossier du run actuellement selectionne."""

        item = self.history_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _emit_selected_item(self, item: QListWidgetItem) -> None:
        """Emet le chemin du run lors d'un double clic."""

        run_dir = item.data(Qt.UserRole)
        if run_dir:
            self.run_selected.emit(run_dir)

    def _emit_selected(self) -> None:
        """Emet le chemin du run selectionne."""

        run_dir = self._selected_run_dir()
        if run_dir:
            self.run_selected.emit(run_dir)

    def open_selected_directory(self) -> None:
        """Ouvre le dossier du run selectionne."""

        run_dir = self._selected_run_dir()
        if run_dir and Path(run_dir).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(run_dir).resolve())))
