"""Vue de consultation des resultats."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bt_gui.core.artifacts import read_manifest
from bt_gui.core.backtest_runner import ServiceResult, SingleRunResult


class DataFrameTableModel(QAbstractTableModel):
    """Modele Qt minimal pour afficher un DataFrame."""

    def __init__(self, dataframe: pd.DataFrame | None = None) -> None:
        super().__init__()
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()

    def set_dataframe(self, dataframe: pd.DataFrame | None) -> None:
        """Remplace le contenu du modele."""

        self.beginResetModel()
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent and parent.isValid() else len(self._dataframe.index)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent and parent.isValid() else len(self._dataframe.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        value = self._dataframe.iat[index.row(), index.column()]
        return "" if pd.isna(value) else str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._dataframe.columns[section]) if section < len(self._dataframe.columns) else ""
        return str(self._dataframe.index[section]) if section < len(self._dataframe.index) else ""


class ResultsView(QWidget):
    """Vue des artefacts et apercus de donnees."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_result: ServiceResult | None = None
        self._current_run: SingleRunResult | None = None
        self._history_run_dir: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Construit l'interface."""

        root_layout = QVBoxLayout(self)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QVBoxLayout(header)

        title = QLabel("Resultats")
        title.setObjectName("SectionTitle")
        self.summary_label = QLabel("Aucun resultat charge.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("MutedLabel")

        selector_layout = QHBoxLayout()
        self.run_selector = QComboBox()
        self.run_selector.currentIndexChanged.connect(self._load_selected_run)
        self.open_folder_button = QPushButton("Ouvrir le dossier")
        self.open_plot_button = QPushButton("Ouvrir le plot")
        self.open_plot_button.setObjectName("SecondaryButton")
        self.open_log_button = QPushButton("Ouvrir le journal")
        self.open_log_button.setObjectName("SecondaryButton")
        selector_layout.addWidget(self.run_selector, 1)
        selector_layout.addWidget(self.open_folder_button)
        selector_layout.addWidget(self.open_plot_button)
        selector_layout.addWidget(self.open_log_button)

        header_layout.addWidget(title)
        header_layout.addWidget(self.summary_label)
        header_layout.addLayout(selector_layout)
        root_layout.addWidget(header)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, 1)

        self.sec_list_model = DataFrameTableModel()
        self.exclusions_model = DataFrameTableModel()
        self.perf_ptf_model = DataFrameTableModel()
        self.perf_bench_model = DataFrameTableModel()

        self.sec_list_table = QTableView()
        self.sec_list_table.setModel(self.sec_list_model)
        self.exclusions_table = QTableView()
        self.exclusions_table.setModel(self.exclusions_model)
        self.perf_ptf_table = QTableView()
        self.perf_ptf_table.setModel(self.perf_ptf_model)
        self.perf_bench_table = QTableView()
        self.perf_bench_table.setModel(self.perf_bench_model)

        self.tabs.addTab(self.sec_list_table, "Sec list")
        self.tabs.addTab(self.exclusions_table, "Exclusions")
        self.tabs.addTab(self.perf_ptf_table, "Perf PTF")
        self.tabs.addTab(self.perf_bench_table, "Perf Bench")

        self.open_folder_button.clicked.connect(lambda: self._open_current_path("run_dir"))
        self.open_plot_button.clicked.connect(lambda: self._open_current_path("plot"))
        self.open_log_button.clicked.connect(lambda: self._open_current_path("run_log"))

    def load_service_result(self, result: ServiceResult) -> None:
        """Charge un resultat simple ou batch."""

        self._current_result = result
        self._history_run_dir = None
        self.run_selector.clear()
        for run in result.runs:
            self.run_selector.addItem(run.name, userData=run)
        if result.runs:
            self._set_current_run(result.runs[0])

    def load_run_directory(self, run_dir: str | Path) -> None:
        """Charge un run a partir de son dossier."""

        path = Path(run_dir)
        self._history_run_dir = path
        self._current_run = None
        manifest = read_manifest(path)
        summary = manifest.get("message", "Run charge depuis l'historique")
        self.summary_label.setText(summary)

        self._load_dataframe_into_model(path / "sec_list.xlsx", self.sec_list_model)
        self._load_dataframe_into_model(path / "exclusions.xlsx", self.exclusions_model)
        self._load_dataframe_into_model(path / "perf_ptf.csv", self.perf_ptf_model)
        self._load_dataframe_into_model(path / "perf_bench.csv", self.perf_bench_model)

    def _set_current_run(self, run: SingleRunResult) -> None:
        """Met a jour la vue avec un run choisi."""

        self._current_run = run
        self.summary_label.setText(
            "\n".join(
                [
                    f"Nom : {run.name}",
                    f"Statut : {run.status}",
                    f"Mode : {run.mode}",
                    f"Message : {run.message}",
                ]
            )
        )

        self._load_dataframe_into_model(run.artifacts.sec_list, self.sec_list_model)
        self._load_dataframe_into_model(run.artifacts.exclusions, self.exclusions_model)
        self._load_dataframe_into_model(run.artifacts.perf_ptf, self.perf_ptf_model)
        self._load_dataframe_into_model(run.artifacts.perf_bench, self.perf_bench_model)

    def _load_selected_run(self) -> None:
        """Charge le run selectionne dans la liste."""

        run = self.run_selector.currentData()
        if isinstance(run, SingleRunResult):
            self._set_current_run(run)

    def _load_dataframe_into_model(self, file_path: Path | None, model: DataFrameTableModel) -> None:
        """Charge un artefact tabulaire dans un modele."""

        if file_path is None or not Path(file_path).exists():
            model.set_dataframe(pd.DataFrame())
            return

        suffix = Path(file_path).suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            dataframe = pd.read_excel(file_path)
        else:
            dataframe = pd.read_csv(file_path)
        model.set_dataframe(dataframe.head(500))

    def _open_current_path(self, attribute_name: str) -> None:
        """Ouvre un chemin associe au run courant."""

        path = None
        if self._current_run is not None:
            if attribute_name == "run_dir":
                path = self._current_run.artifacts.run_dir
            else:
                path = getattr(self._current_run.artifacts, attribute_name, None)
        elif self._history_run_dir is not None:
            if attribute_name == "run_dir":
                path = self._history_run_dir
            elif attribute_name == "plot":
                path = self._history_run_dir / "plot.html"
            elif attribute_name == "run_log":
                path = self._history_run_dir / "run.log"

        if path is None:
            QMessageBox.information(self, "Aucun run", "Aucun run n'est actuellement charge.")
            return

        if path is None or not Path(path).exists():
            QMessageBox.information(self, "Fichier absent", "Le fichier demande n'est pas disponible.")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path))))
