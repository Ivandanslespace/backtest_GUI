"""Fenetre principale de l'application."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bt_gui.core.backtest_runner import BacktestService, ServiceResult

from .config_view import ConfigView
from .history_view import HistoryView
from .results_view import ResultsView
from .run_view import RunView


class MainWindow(QMainWindow):
    """Fenetre principale avec navigation laterale."""

    def __init__(self) -> None:
        super().__init__()
        self._service = BacktestService()
        self._build_ui()

    def _build_ui(self) -> None:
        """Construit la fenetre principale."""

        self.setWindowTitle("Backtest GUI")
        self.resize(1480, 960)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(18)

        navigation_card = QFrame()
        navigation_card.setObjectName("NavigationCard")
        navigation_layout = QVBoxLayout(navigation_card)
        navigation_layout.setContentsMargins(18, 18, 18, 18)
        navigation_layout.setSpacing(16)

        app_title = QLabel("Backtest GUI")
        app_title.setObjectName("AppTitle")
        app_subtitle = QLabel("Pilotage recherche / production")
        app_subtitle.setObjectName("MutedLabel")
        navigation_layout.addWidget(app_title)
        navigation_layout.addWidget(app_subtitle)

        self.navigation_list = QListWidget()
        for label in ["Configuration", "Execution", "Resultats", "Historique"]:
            self.navigation_list.addItem(QListWidgetItem(label))
        self.navigation_list.setCurrentRow(0)
        navigation_layout.addWidget(self.navigation_list, 1)

        root_layout.addWidget(navigation_card, 0)

        content_layout = QVBoxLayout()
        header_card = QFrame()
        header_card.setObjectName("HeroCard")
        header_layout = QVBoxLayout(header_card)
        header_title = QLabel("Application desktop pour lancer les backtests")
        header_title.setObjectName("HeroTitle")
        header_subtitle = QLabel(
            "Chargez les donnees, configurez le moteur BacktestEngine, lancez un run, puis consultez l'historique et les artefacts."
        )
        header_subtitle.setWordWrap(True)
        header_subtitle.setObjectName("MutedLabel")
        header_layout.addWidget(header_title)
        header_layout.addWidget(header_subtitle)
        content_layout.addWidget(header_card, 0)

        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget, 1)
        root_layout.addLayout(content_layout, 1)

        self.config_view = ConfigView(self._service)
        self.run_view = RunView(self._service, settings_provider=self.config_view.build_settings)
        self.results_view = ResultsView()
        self.history_view = HistoryView()

        self.stacked_widget.addWidget(self.config_view)
        self.stacked_widget.addWidget(self.run_view)
        self.stacked_widget.addWidget(self.results_view)
        self.stacked_widget.addWidget(self.history_view)

        self.navigation_list.currentRowChanged.connect(self._handle_navigation_change)
        self.config_view.settings_changed.connect(lambda _settings: self.run_view.refresh_summary())
        self.config_view.settings_changed.connect(lambda _settings: self.history_view.refresh_history())
        self.run_view.result_ready.connect(self._handle_run_result)
        self.history_view.run_selected.connect(self._handle_history_selection)

    def _handle_navigation_change(self, index: int) -> None:
        """处理侧边导航切换。"""

        self.stacked_widget.setCurrentIndex(index)

    def _handle_run_result(self, result: ServiceResult) -> None:
        """Affiche les resultats a la fin d'un run."""

        self.results_view.load_service_result(result)
        self.history_view.refresh_history()
        self.navigation_list.setCurrentRow(2)

    def _handle_history_selection(self, run_dir: str) -> None:
        """Charge un run existant dans la vue de resultats."""

        self.results_view.load_run_directory(run_dir)
        self.navigation_list.setCurrentRow(2)
