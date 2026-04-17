"""Vue de lancement des runs et des batches."""

from __future__ import annotations

from pathlib import Path
import traceback

from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from bt_gui.config.settings import AppSettings
from bt_gui.core.backtest_runner import BacktestService, ServiceResult


class RunWorker(QThread):
    """Thread de lancement des calculs lourds."""

    progress = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, service: BacktestService, settings: AppSettings, force_batch: bool) -> None:
        super().__init__()
        self._service = service
        self._settings = settings.copy()
        self._force_batch = force_batch

    def run(self) -> None:
        """Execute le service et renvoie le resultat."""

        try:
            result = self._service.run(
                self._settings,
                force_batch=self._force_batch,
                progress_callback=self.progress.emit,
            )
            self.completed.emit(result)
        except Exception as exc:  # pragma: no cover - depend du runtime
            summary = f"{type(exc).__name__}: {exc}"
            details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
            self.failed.emit(f"{summary}\n\nTraceback complet :\n{details}")


class RunView(QWidget):
    """Page de lancement des runs."""

    result_ready = Signal(object)

    def __init__(
        self,
        service: BacktestService,
        settings_provider,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._settings_provider = settings_provider
        self._worker: RunWorker | None = None
        self._last_result: ServiceResult | None = None
        self._build_ui()
        self.refresh_summary()

    def _build_ui(self) -> None:
        """Construit l'interface."""

        root_layout = QVBoxLayout(self)

        summary_card = QFrame()
        summary_card.setObjectName("Card")
        summary_layout = QVBoxLayout(summary_card)
        title = QLabel("Execution")
        title.setObjectName("SectionTitle")
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("MutedLabel")
        summary_layout.addWidget(title)
        summary_layout.addWidget(self.summary_label)
        root_layout.addWidget(summary_card)

        actions_card = QFrame()
        actions_card.setObjectName("Card")
        actions_layout = QHBoxLayout(actions_card)
        self.run_button = QPushButton("Lancer un run")
        self.batch_button = QPushButton("Lancer un batch")
        self.batch_button.setObjectName("SecondaryButton")
        self.open_last_button = QPushButton("Ouvrir le dernier dossier")
        self.open_last_button.setObjectName("SecondaryButton")
        actions_layout.addWidget(self.run_button)
        actions_layout.addWidget(self.batch_button)
        actions_layout.addWidget(self.open_last_button)
        actions_layout.addStretch(1)
        root_layout.addWidget(actions_card)

        log_card = QFrame()
        log_card.setObjectName("Card")
        log_layout = QVBoxLayout(log_card)
        log_title = QLabel("Journal d'execution")
        log_title.setObjectName("SectionTitle")
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(380)
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.log_output)
        root_layout.addWidget(log_card, 1)

        self.run_button.clicked.connect(lambda: self._start(force_batch=False))
        self.batch_button.clicked.connect(lambda: self._start(force_batch=True))
        self.open_last_button.clicked.connect(self.open_last_run_directory)

    def refresh_summary(self) -> None:
        """Actualise le resume des parametres courants."""

        settings = self._settings_provider()
        self.summary_label.setText(
            "\n".join(
                [
                    f"Utilisateur : {settings.user.name}",
                    f"Mode : {settings.run.mode}",
                    f"Benchmark : {settings.run.bench or '-'}",
                    f"Metrics : {', '.join(settings.run.metrics) if settings.run.metrics else '-'}",
                    f"Date de debut : {settings.run.start_date or '-'}",
                    f"Fill method : {settings.run.fill_method}",
                    f"Production mensuelle : {'oui' if settings.run.mode_monthly_prod else 'non'}",
                ]
            )
        )

    def _append_log(self, message: str) -> None:
        """Ajoute une ligne dans le journal de la vue."""

        self.log_output.appendPlainText(message)

    def _start(self, *, force_batch: bool) -> None:
        """Demarre un run ou un batch."""

        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "Execution en cours", "Un calcul est deja en cours.")
            return

        settings = self._settings_provider()
        self.log_output.clear()
        self._append_log("Preparation de l'execution...")

        self._worker = RunWorker(self._service, settings, force_batch=force_batch)
        self._worker.progress.connect(self._append_log)
        self._worker.completed.connect(self._handle_completed)
        self._worker.failed.connect(self._handle_failed)
        self._worker.start()

    def _handle_completed(self, result: ServiceResult) -> None:
        """Traite la fin normale de l'execution."""

        self._last_result = result
        if result.is_batch:
            self._append_log(f"Batch termine : {len(result.runs)} runs.")
        else:
            latest_run = result.latest_run
            if latest_run is not None and latest_run.status != "success":
                self._append_log(f"Run termine en echec : {latest_run.message}")
            else:
                self._append_log("Run termine.")
        self.result_ready.emit(result)

    def _handle_failed(self, message: str) -> None:
        """Traite la fin en erreur du worker."""

        summary = message.splitlines()[0] if message else "Erreur inconnue"
        self._append_log("Erreur critique :")
        self._append_log(message)
        QMessageBox.critical(
            self,
            "Execution impossible",
            f"{summary}\n\nConsultez le journal d'execution pour le traceback complet.",
        )

    def open_last_run_directory(self) -> None:
        """Ouvre le dossier du dernier run disponible."""

        if self._last_result is None or self._last_result.latest_run is None:
            QMessageBox.information(self, "Aucun run", "Aucun run n'a encore ete execute.")
            return
        run_dir = self._last_result.latest_run.artifacts.run_dir
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(run_dir))))
