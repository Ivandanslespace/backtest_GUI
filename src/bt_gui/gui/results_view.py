"""Vue de consultation des resultats."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - depend de l'environnement Qt
    QWebEngineView = None

from bt_gui.core.artifacts import get_latest_run_directory, read_manifest
from bt_gui.core.backtest_runner import ServiceResult, SingleRunResult

RAW_VALUE_ROLE = Qt.UserRole + 1


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
        if not index.isValid():
            return None
        value = self._dataframe.iat[index.row(), index.column()]
        if role == Qt.DisplayRole:
            return "" if pd.isna(value) else str(value)
        if role == RAW_VALUE_ROLE:
            return None if pd.isna(value) else value
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._dataframe.columns[section]) if section < len(self._dataframe.columns) else ""
        return str(self._dataframe.index[section]) if section < len(self._dataframe.index) else ""


class DataFrameFilterProxyModel(QSortFilterProxyModel):
    """Proxy de tri et filtrage pour les tables pandas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filter_text = ""
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    def set_filter_text(self, text: str) -> None:
        self._filter_text = text.strip().casefold()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._filter_text:
            return True
        model = self.sourceModel()
        if model is None:
            return True
        for column in range(model.columnCount(source_parent)):
            index = model.index(source_row, column, source_parent)
            value = index.data(Qt.DisplayRole)
            if value is not None and self._filter_text in str(value).casefold():
                return True
        return False

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_value = left.data(RAW_VALUE_ROLE)
        right_value = right.data(RAW_VALUE_ROLE)
        if left_value is None:
            return right_value is not None
        if right_value is None:
            return False
        try:
            return bool(left_value < right_value)
        except TypeError:
            return str(left.data(Qt.DisplayRole)).casefold() < str(right.data(Qt.DisplayRole)).casefold()


class ArtifactLoadWorker(QObject):
    """Charge les artefacts tabulaires hors du thread UI."""

    finished = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, token: int, artifact_paths: dict[str, Path | None]) -> None:
        super().__init__()
        self._token = token
        self._artifact_paths = artifact_paths

    def run(self) -> None:
        """Lit les artefacts dans un thread secondaire."""

        try:
            payload = {
                "sec_list": self._load_dataframe(self._artifact_paths.get("sec_list")),
                "exclusions": self._load_dataframe(self._artifact_paths.get("exclusions")),
                "perf_ptf": self._load_dataframe(self._artifact_paths.get("perf_ptf")),
                "perf_bench": self._load_dataframe(self._artifact_paths.get("perf_bench")),
                "plot": self._resolve_plot(self._artifact_paths.get("plot")),
            }
        except Exception as exc:  # pragma: no cover - depend du filesystem
            self.failed.emit(self._token, f"{type(exc).__name__}: {exc}")
            return
        self.finished.emit(self._token, payload)

    @staticmethod
    def _load_dataframe(file_path: Path | None) -> pd.DataFrame:
        """Charge un artefact tabulaire en DataFrame."""

        if file_path is None or not file_path.exists():
            return pd.DataFrame()
        return pd.read_parquet(file_path)

    @staticmethod
    def _resolve_plot(file_path: Path | None) -> Path | None:
        """Retourne le chemin du plot s'il existe."""

        if file_path is None or not file_path.exists():
            return None
        return file_path


class ResultsView(QWidget):
    """Vue des artefacts et apercus de donnees."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_result: ServiceResult | None = None
        self._current_run: SingleRunResult | None = None
        self._history_run_dir: Path | None = None
        self._load_token = 0
        self._is_loading = False
        self._load_tasks: dict[int, tuple[QThread, ArtifactLoadWorker]] = {}
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
        self.load_history_button = QPushButton("Charger l'historique")
        self.load_history_button.setObjectName("SecondaryButton")
        self.enable_sort_button = QPushButton("Activer le tri")
        self.enable_sort_button.setObjectName("SecondaryButton")
        self.open_folder_button = QPushButton("Ouvrir le dossier")
        self.open_log_button = QPushButton("Ouvrir le journal")
        self.open_log_button.setObjectName("SecondaryButton")
        selector_layout.addWidget(self.run_selector, 1)
        selector_layout.addWidget(self.load_history_button)
        selector_layout.addWidget(self.enable_sort_button)
        selector_layout.addWidget(self.open_folder_button)
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

        self.sec_list_proxy = DataFrameFilterProxyModel(self)
        self.sec_list_proxy.setSourceModel(self.sec_list_model)
        self.exclusions_proxy = DataFrameFilterProxyModel(self)
        self.exclusions_proxy.setSourceModel(self.exclusions_model)

        self.sec_list_filter = QLineEdit()
        self.sec_list_filter.setPlaceholderText("Filtrer la sec list...")
        self.sec_list_filter.textChanged.connect(self.sec_list_proxy.set_filter_text)
        self.exclusions_filter = QLineEdit()
        self.exclusions_filter.setPlaceholderText("Filtrer les exclusions...")
        self.exclusions_filter.textChanged.connect(self.exclusions_proxy.set_filter_text)

        self.sec_list_table = QTableView()
        self.sec_list_table.setModel(self.sec_list_proxy)
        self.sec_list_table.setSortingEnabled(False)
        self.exclusions_table = QTableView()
        self.exclusions_table.setModel(self.exclusions_proxy)
        self.exclusions_table.setSortingEnabled(False)
        self.perf_ptf_table = QTableView()
        self.perf_ptf_table.setModel(self.perf_ptf_model)
        self.perf_bench_table = QTableView()
        self.perf_bench_table.setModel(self.perf_bench_model)
        self.plot_tab = QWidget()
        plot_layout = QVBoxLayout(self.plot_tab)
        self.plot_message_label = QLabel("Aucun plot charge.")
        self.plot_message_label.setObjectName("MutedLabel")
        self.plot_message_label.setAlignment(Qt.AlignCenter)
        self.plot_message_label.setWordWrap(True)
        plot_layout.addWidget(self.plot_message_label)
        self.plot_view = QWebEngineView(self.plot_tab) if QWebEngineView is not None else None
        if self.plot_view is not None:
            self.plot_view.hide()
            plot_layout.addWidget(self.plot_view, 1)

        sec_list_tab = QWidget()
        sec_list_layout = QVBoxLayout(sec_list_tab)
        sec_list_layout.addWidget(self.sec_list_filter)
        sec_list_layout.addWidget(self.sec_list_table)

        exclusions_tab = QWidget()
        exclusions_layout = QVBoxLayout(exclusions_tab)
        exclusions_layout.addWidget(self.exclusions_filter)
        exclusions_layout.addWidget(self.exclusions_table)

        self.tabs.addTab(sec_list_tab, "Sec list")
        self.tabs.addTab(exclusions_tab, "Exclusions")
        self.tabs.addTab(self.perf_ptf_table, "Perf PTF")
        self.tabs.addTab(self.perf_bench_table, "Perf Bench")
        self.tabs.addTab(self.plot_tab, "Plot")

        self.load_history_button.clicked.connect(self._load_latest_history_result)
        self.enable_sort_button.clicked.connect(self._enable_sorting)
        self.open_folder_button.clicked.connect(lambda: self._open_current_path("run_dir"))
        self.open_log_button.clicked.connect(lambda: self._open_current_path("run_log"))
        self._reset_artifact_views()

    def load_service_result(self, result: ServiceResult) -> None:
        """Charge un resultat simple ou batch."""

        self._current_result = result
        self._history_run_dir = None
        self._reset_filters()
        self.run_selector.blockSignals(True)
        self.run_selector.clear()
        for run in result.runs:
            self.run_selector.addItem(run.name, userData=run)
        self.run_selector.blockSignals(False)
        if result.runs:
            self._set_current_run(result.runs[0])
        else:
            self._reset_artifact_views()

    def load_run_directory(self, run_dir: str | Path) -> None:
        """Charge un run a partir de son dossier."""

        path = Path(run_dir)
        self._history_run_dir = path
        self._current_result = None
        self._current_run = None
        self._reset_filters()
        manifest = read_manifest(path)
        history_message = manifest.get("message", "Run charge depuis l'historique")
        self.run_selector.blockSignals(True)
        self.run_selector.clear()
        self.run_selector.addItem(f"{path.parent.name} / {path.name}")
        self.run_selector.blockSignals(False)
        self.summary_label.setText(
            "\n".join(
                [
                    f"Nom : {path.name}",
                    f"Utilisateur : {path.parent.name}",
                    f"Statut : {manifest.get('status', 'unknown')}",
                    f"Benchmark : {manifest.get('bench', '-')}",
                    f"Message : {history_message}",
                ]
            )
        )
        self._start_artifact_load(
            {
                "sec_list": path / "sec_list.parquet",
                "exclusions": path / "exclusions.parquet",
                "perf_ptf": path / "perf_ptf.parquet",
                "perf_bench": path / "perf_bench.parquet",
                "plot": path / "plot.html",
            }
        )

    def has_loaded_result(self) -> bool:
        """Indique si la vue des resultats a deja charge un contenu."""

        return self._current_result is not None or self._history_run_dir is not None or self._is_loading

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
        self._start_artifact_load(
            {
                "sec_list": run.artifacts.sec_list,
                "exclusions": run.artifacts.exclusions,
                "perf_ptf": run.artifacts.perf_ptf,
                "perf_bench": run.artifacts.perf_bench,
                "plot": run.artifacts.plot,
            }
        )

    def _load_selected_run(self) -> None:
        """Charge le run selectionne dans la liste."""

        run = self.run_selector.currentData()
        if isinstance(run, SingleRunResult):
            self._reset_filters()
            self._set_current_run(run)

    def _load_latest_history_result(self) -> None:
        """Charge a la demande le run historique global le plus recent."""

        latest_run = get_latest_run_directory()
        if latest_run is None:
            QMessageBox.information(self, "Aucun historique", "Aucun run historique n'est disponible.")
            return
        self.load_run_directory(latest_run)

    def _enable_sorting(self) -> None:
        """Active le tri manuel pour les tables qui le supportent."""

        self.sec_list_table.setSortingEnabled(True)
        self.exclusions_table.setSortingEnabled(True)
        self.enable_sort_button.setText("Tri active")
        self.enable_sort_button.setEnabled(False)

    def _start_artifact_load(self, artifact_paths: dict[str, Path | None]) -> None:
        """Charge en arriere-plan les artefacts du resultat courant."""

        self._load_token += 1
        token = self._load_token
        self._is_loading = True
        self._reset_artifact_views()
        thread = QThread(self)
        worker = ArtifactLoadWorker(token, artifact_paths)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_artifact_load_finished)
        worker.failed.connect(self._handle_artifact_load_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda finished_token=token: self._cleanup_load_task(finished_token))
        self._load_tasks[token] = (thread, worker)
        thread.start()

    def _handle_artifact_load_finished(self, token: int, payload: object) -> None:
        """Applique a l'interface les donnees chargees en arriere-plan."""

        if token != self._load_token:
            return
        self._is_loading = False
        if not isinstance(payload, dict):
            return
        self.sec_list_model.set_dataframe(payload.get("sec_list"))
        self.exclusions_model.set_dataframe(payload.get("exclusions"))
        self.perf_ptf_model.set_dataframe(payload.get("perf_ptf"))
        self.perf_bench_model.set_dataframe(payload.get("perf_bench"))
        self._set_plot_content(payload.get("plot"))

    def _handle_artifact_load_failed(self, token: int, message: str) -> None:
        """Gere un echec de chargement des artefacts en arriere-plan."""

        if token != self._load_token:
            return
        self._is_loading = False
        self._reset_artifact_views(message=f"Chargement impossible : {message}")

    def _cleanup_load_task(self, token: int) -> None:
        """Nettoie une tache de chargement terminee."""

        self._load_tasks.pop(token, None)

    def _reset_filters(self) -> None:
        """Reinitialise les filtres de table."""

        self.sec_list_filter.clear()
        self.exclusions_filter.clear()

    def _reset_artifact_views(self, message: str = "Chargement des artefacts...") -> None:
        """Reinitialise la zone de resultats en attendant le chargement."""

        self.sec_list_model.set_dataframe(pd.DataFrame())
        self.exclusions_model.set_dataframe(pd.DataFrame())
        self.perf_ptf_model.set_dataframe(pd.DataFrame())
        self.perf_bench_model.set_dataframe(pd.DataFrame())
        self._set_plot_content(None, message=message)

    def _set_plot_content(self, plot_path: Path | None, message: str | None = None) -> None:
        """Met a jour le contenu de l'onglet du plot."""

        if self.plot_view is None:
            self.plot_message_label.setText("Qt WebEngine n'est pas disponible sur cette machine.")
            self.plot_message_label.show()
            return
        if plot_path is None:
            self.plot_view.hide()
            self.plot_view.setHtml("")
            self.plot_message_label.setText(message or "Le plot n'est pas disponible.")
            self.plot_message_label.show()
            return
        self.plot_message_label.hide()
        self.plot_view.show()
        self.plot_view.load(QUrl.fromLocalFile(str(plot_path.resolve())))

    def _resolve_current_path(self, attribute_name: str) -> Path | None:
        """Retourne le chemin associe au run courant."""

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
        return Path(path) if path is not None else None

    def _open_current_path(self, attribute_name: str) -> None:
        """Ouvre un chemin associe au run courant."""

        path = self._resolve_current_path(attribute_name)
        if path is None:
            QMessageBox.information(self, "Aucun run", "Aucun run n'est actuellement charge.")
            return

        if not path.exists():
            QMessageBox.information(self, "Fichier absent", "Le fichier demande n'est pas disponible.")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
