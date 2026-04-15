"""Vue de configuration principale."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ma_librairie.config import list_available_profiles, load_settings, save_settings
from ma_librairie.config.settings import AppSettings
from ma_librairie.core.backtest_runner import BacktestService


def _make_path_row(button_text: str) -> tuple[QWidget, QLineEdit, QPushButton]:
    """Construit une ligne chemin + bouton."""

    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    line_edit = QLineEdit()
    button = QPushButton(button_text)
    button.setObjectName("SecondaryButton")
    layout.addWidget(line_edit)
    layout.addWidget(button)
    return container, line_edit, button


class ConfigView(QWidget):
    """Page de configuration et d'inspection des donnees."""

    settings_changed = Signal(object)

    def __init__(self, service: BacktestService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._settings = load_settings("user1")
        self._build_ui()
        self.apply_settings(self._settings)
        self.refresh_inspection()

    def _build_ui(self) -> None:
        """Construit l'interface."""

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        root_layout.addWidget(scroll_area)

        content = QWidget()
        scroll_area.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        header_layout.setSpacing(12)

        title_box = QVBoxLayout()
        title = QLabel("Configuration du backtest")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Chargez un profil, ajustez les parametres puis lancez un run ou un batch.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        controls_box = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.setEditable(True)
        self.profile_combo.addItems(list_available_profiles())
        self.load_button = QPushButton("Charger")
        self.save_button = QPushButton("Enregistrer")
        self.inspect_button = QPushButton("Actualiser l'inspection")
        self.inspect_button.setObjectName("SecondaryButton")
        controls_box.addWidget(self.profile_combo)
        controls_box.addWidget(self.load_button)
        controls_box.addWidget(self.save_button)
        controls_box.addWidget(self.inspect_button)

        header_layout.addLayout(title_box, 1)
        header_layout.addLayout(controls_box)
        content_layout.addWidget(header)

        self.tabs = QTabWidget()
        content_layout.addWidget(self.tabs)

        self._build_data_tab()
        self._build_run_tab()
        self._build_batch_tab()
        self._build_inspection_tab()

        content_layout.addStretch(1)

        self.load_button.clicked.connect(self.load_profile)
        self.save_button.clicked.connect(self.save_profile)
        self.inspect_button.clicked.connect(self.refresh_inspection)

    def _build_data_tab(self) -> None:
        """Construit l'onglet donnees."""

        tab = QWidget()
        layout = QVBoxLayout(tab)

        card = QFrame()
        card.setObjectName("Card")
        form = QFormLayout(card)

        self.user_name_edit = QLineEdit()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["research", "production", "batch"])

        screen_row, self.screen_path_edit, screen_button = _make_path_row("Parcourir")
        returns_row, self.returns_path_edit, returns_button = _make_path_row("Parcourir")
        blacklist_row, self.blacklist_path_edit, blacklist_button = _make_path_row("Parcourir")
        output_row, self.output_dir_edit, output_button = _make_path_row("Parcourir")
        pivot_row, self.score_pivot_dir_edit, pivot_button = _make_path_row("Parcourir")

        form.addRow("Profil utilisateur", self.user_name_edit)
        form.addRow("Mode", self.mode_combo)
        form.addRow("Fichier screen", screen_row)
        form.addRow("Fichier returns", returns_row)
        form.addRow("Liste noire", blacklist_row)
        form.addRow("Repertoire de sortie", output_row)
        form.addRow("Dossier ESG pivot", pivot_row)

        layout.addWidget(card)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Donnees")

        screen_button.clicked.connect(lambda: self._pick_file(self.screen_path_edit, "Choisir un screen"))
        returns_button.clicked.connect(lambda: self._pick_file(self.returns_path_edit, "Choisir un fichier returns"))
        blacklist_button.clicked.connect(lambda: self._pick_file(self.blacklist_path_edit, "Choisir une blacklist"))
        output_button.clicked.connect(lambda: self._pick_directory(self.output_dir_edit, "Choisir un dossier de sortie"))
        pivot_button.clicked.connect(lambda: self._pick_directory(self.score_pivot_dir_edit, "Choisir un dossier ESG pivot"))

    def _build_run_tab(self) -> None:
        """Construit l'onglet de parametres de run."""

        tab = QWidget()
        layout = QVBoxLayout(tab)

        general_card = QFrame()
        general_card.setObjectName("Card")
        general_form = QFormLayout(general_card)

        self.ptf_name_edit = QLineEdit()
        self.bench_combo = QComboBox()
        self.bench_combo.setEditable(True)
        self.metrics_list = QListWidget()
        self.metrics_list.setSelectionMode(QListWidget.MultiSelection)
        self.metrics_list.setMinimumHeight(160)
        self.custom_metrics_edit = QLineEdit()
        self.custom_metrics_edit.setPlaceholderText("MetricA, MetricB")
        self.percentile_edit = QLineEdit()
        self.top_checkbox = QCheckBox("Selection des meilleurs titres")
        self.ponderation_combo = QComboBox()
        self.ponderation_combo.addItems(["Racine cube", "Racine carrée", "Market cap", "Log", "Equalweight"])
        self.esg_exclusion_edit = QLineEdit()
        self.cut_mkt_cap_edit = QLineEdit()
        self.score_pivot_esg_edit = QLineEdit()
        self.score_neutral_combo = QComboBox()
        self.score_neutral_combo.addItems(["ICB 19", "ICB 11"])
        self.weight_neutral_combo = QComboBox()
        self.weight_neutral_combo.addItems(["ICB 19", "ICB 11"])
        self.top_mandatory_edit = QLineEdit()
        self.cap_weight_threshold_edit = QLineEdit()
        self.mode_monthly_prod_checkbox = QCheckBox("Activer le mode production mensuelle")
        self.start_date_edit = QLineEdit()
        self.start_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.freq_rebal_edit = QLineEdit()
        self.screen_start_date_combo = QComboBox()
        self.screen_start_date_combo.addItems(["mois_impair", "mois_pair"])
        self.fill_method_combo = QComboBox()
        self.fill_method_combo.addItems(["drift", "copy"])
        self.max_weight_edit = QLineEdit()
        self.sector_neutral_checkbox = QCheckBox("Neutralisation sectorielle dans le backtest benchmark")
        self.reco_secto_edit = QPlainTextEdit()
        self.reco_secto_edit.setPlaceholderText("19 valeurs separees par des virgules")
        self.reco_secto_edit.setFixedHeight(80)
        self.reco_facto_edit = QPlainTextEdit()
        self.reco_facto_edit.setPlaceholderText("5 valeurs separees par des virgules")
        self.reco_facto_edit.setFixedHeight(60)

        general_form.addRow("Nom du portefeuille", self.ptf_name_edit)
        general_form.addRow("Benchmark", self.bench_combo)
        general_form.addRow("Metrics detectees", self.metrics_list)
        general_form.addRow("Metrics manuelles", self.custom_metrics_edit)
        general_form.addRow("Percentile", self.percentile_edit)
        general_form.addRow("", self.top_checkbox)
        general_form.addRow("Ponderation", self.ponderation_combo)
        general_form.addRow("ESG exclusion", self.esg_exclusion_edit)
        general_form.addRow("Cut market cap", self.cut_mkt_cap_edit)
        general_form.addRow("Score pivot ESG", self.score_pivot_esg_edit)
        general_form.addRow("Score neutral", self.score_neutral_combo)
        general_form.addRow("Weight neutral", self.weight_neutral_combo)
        general_form.addRow("Top mandatory", self.top_mandatory_edit)
        general_form.addRow("Cap weight threshold", self.cap_weight_threshold_edit)
        general_form.addRow("", self.mode_monthly_prod_checkbox)
        general_form.addRow("Date de debut", self.start_date_edit)
        general_form.addRow("Frequence rebalancement", self.freq_rebal_edit)
        general_form.addRow("Screen start date", self.screen_start_date_combo)
        general_form.addRow("Fill method", self.fill_method_combo)
        general_form.addRow("Max weight", self.max_weight_edit)
        general_form.addRow("", self.sector_neutral_checkbox)
        general_form.addRow("Reco secto", self.reco_secto_edit)
        general_form.addRow("Reco facto", self.reco_facto_edit)

        layout.addWidget(general_card)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Parametres")

    def _build_batch_tab(self) -> None:
        """Construit l'onglet batch."""

        tab = QWidget()
        layout = QVBoxLayout(tab)

        card = QFrame()
        card.setObjectName("Card")
        form = QFormLayout(card)

        self.batch_benches_edit = QLineEdit()
        self.batch_benches_edit.setPlaceholderText("SP500, MSCI US")
        self.batch_metrics_edit = QLineEdit()
        self.batch_metrics_edit.setPlaceholderText("Quality Avg Percentile, Value Avg Percentile")
        self.batch_percentiles_edit = QLineEdit()
        self.batch_percentiles_edit.setPlaceholderText("0.2, 0.25")
        self.batch_start_dates_edit = QLineEdit()
        self.batch_start_dates_edit.setPlaceholderText("2020-01-01, 2021-01-01")
        self.batch_top_values_edit = QLineEdit()
        self.batch_top_values_edit.setPlaceholderText("true, false")

        form.addRow("Benchmarks", self.batch_benches_edit)
        form.addRow("Metrics", self.batch_metrics_edit)
        form.addRow("Percentiles", self.batch_percentiles_edit)
        form.addRow("Dates de debut", self.batch_start_dates_edit)
        form.addRow("Valeurs Top", self.batch_top_values_edit)

        help_label = QLabel(
            "Le batch genere un produit cartesien sur les listes renseignees. "
            "Laissez un champ vide pour reutiliser la valeur simple du run."
        )
        help_label.setWordWrap(True)
        help_label.setObjectName("MutedLabel")

        layout.addWidget(card)
        layout.addWidget(help_label)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Batch")

    def _build_inspection_tab(self) -> None:
        """Construit l'onglet d'inspection."""

        tab = QWidget()
        layout = QVBoxLayout(tab)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)

        self.inspection_summary = QLabel("Aucune inspection disponible.")
        self.inspection_summary.setWordWrap(True)
        self.inspection_summary.setObjectName("MutedLabel")

        self.detected_benchmarks = QPlainTextEdit()
        self.detected_benchmarks.setReadOnly(True)
        self.detected_metrics = QPlainTextEdit()
        self.detected_metrics.setReadOnly(True)
        self.detected_columns = QPlainTextEdit()
        self.detected_columns.setReadOnly(True)

        card_layout.addWidget(QLabel("Resume"))
        card_layout.addWidget(self.inspection_summary)
        card_layout.addWidget(QLabel("Benchmarks detectes"))
        card_layout.addWidget(self.detected_benchmarks)
        card_layout.addWidget(QLabel("Metrics candidates"))
        card_layout.addWidget(self.detected_metrics)
        card_layout.addWidget(QLabel("Colonnes du screen"))
        card_layout.addWidget(self.detected_columns)

        layout.addWidget(card)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Inspection")

    def _pick_file(self, target: QLineEdit, title: str) -> None:
        """Ouvre un selecteur de fichier."""

        file_path, _ = QFileDialog.getOpenFileName(self, title, str(Path.home()))
        if file_path:
            target.setText(file_path)

    def _pick_directory(self, target: QLineEdit, title: str) -> None:
        """Ouvre un selecteur de dossier."""

        directory = QFileDialog.getExistingDirectory(self, title, str(Path.home()))
        if directory:
            target.setText(directory)

    def _parse_csv_strings(self, raw_text: str) -> list[str]:
        """Parse une liste separee par virgules."""

        return [item.strip() for item in raw_text.split(",") if item.strip()]

    def _parse_float_list(self, raw_text: str, expected_length: int) -> list[float]:
        """Parse une liste de flottants en la ramenant a une taille fixe."""

        values: list[float] = []
        for item in self._parse_csv_strings(raw_text):
            try:
                values.append(float(item))
            except ValueError:
                values.append(0.0)
        if len(values) < expected_length:
            values.extend([0.0] * (expected_length - len(values)))
        return values[:expected_length]

    def _parse_optional_float(self, raw_text: str) -> float | None:
        """Convertit une chaine en float optionnel."""

        text = raw_text.strip()
        if not text:
            return None
        return float(text)

    def _parse_optional_int(self, raw_text: str) -> int | None:
        """Convertit une chaine en entier optionnel."""

        text = raw_text.strip()
        if not text:
            return None
        return int(float(text))

    def _selected_metrics(self) -> list[str]:
        """Retourne les metrics selectionnees dans la liste ou dans le champ manuel."""

        selected = [item.text() for item in self.metrics_list.selectedItems()]
        if selected:
            return selected
        return self._parse_csv_strings(self.custom_metrics_edit.text())

    def build_settings(self) -> AppSettings:
        """Construit l'objet de configuration a partir du formulaire."""

        settings = self._settings.copy()
        settings.user.name = self.user_name_edit.text().strip() or "user1"
        settings.run.mode = self.mode_combo.currentText()
        settings.paths.screen = self.screen_path_edit.text().strip()
        settings.paths.returns = self.returns_path_edit.text().strip()
        settings.paths.liste_noire = self.blacklist_path_edit.text().strip()
        settings.paths.output_dir = self.output_dir_edit.text().strip()
        settings.paths.score_pivot_esg_path = self.score_pivot_dir_edit.text().strip()

        settings.run.ptf_name = self.ptf_name_edit.text().strip() or "PTF TEST"
        settings.run.bench = self.bench_combo.currentText().strip()
        settings.run.metrics = self._selected_metrics()
        settings.run.percentile = float(self.percentile_edit.text().strip() or "0.2")
        settings.run.top = self.top_checkbox.isChecked()
        settings.run.ponderation = self.ponderation_combo.currentText()
        settings.run.esg_exclusion = float(self.esg_exclusion_edit.text().strip() or "0")
        settings.run.cut_mkt_cap = float(self.cut_mkt_cap_edit.text().strip() or "0")
        settings.run.score_pivot_esg = self.score_pivot_esg_edit.text().strip() or None
        settings.run.score_neutral = self.score_neutral_combo.currentText()
        settings.run.weight_neutral = self.weight_neutral_combo.currentText()
        settings.run.top_mandatory = self._parse_optional_int(self.top_mandatory_edit.text())
        settings.run.cap_weight_threshold = self._parse_optional_float(self.cap_weight_threshold_edit.text())
        settings.run.mode_monthly_prod = self.mode_monthly_prod_checkbox.isChecked()
        settings.run.start_date = self.start_date_edit.text().strip()
        settings.run.freq_rebal = self._parse_optional_int(self.freq_rebal_edit.text())
        settings.run.screen_start_date = self.screen_start_date_combo.currentText()
        settings.run.fill_method = self.fill_method_combo.currentText()
        settings.run.max_weight = float(self.max_weight_edit.text().strip() or "1")
        settings.run.sector_neutral = self.sector_neutral_checkbox.isChecked()
        settings.run.reco_secto = self._parse_float_list(self.reco_secto_edit.toPlainText(), 19)
        settings.run.reco_facto = self._parse_float_list(self.reco_facto_edit.toPlainText(), 5)

        settings.batch.benches = self._parse_csv_strings(self.batch_benches_edit.text())
        settings.batch.metrics = self._parse_csv_strings(self.batch_metrics_edit.text())
        settings.batch.percentiles = [float(item) for item in self._parse_csv_strings(self.batch_percentiles_edit.text())]
        settings.batch.start_dates = self._parse_csv_strings(self.batch_start_dates_edit.text())
        settings.batch.top_values = [item.lower() in {"1", "true", "oui", "yes"} for item in self._parse_csv_strings(self.batch_top_values_edit.text())]

        self._settings = settings
        return settings

    def apply_settings(self, settings: AppSettings) -> None:
        """Injecte une configuration dans le formulaire."""

        self._settings = settings.copy()
        available_profiles = list_available_profiles()
        self.profile_combo.clear()
        self.profile_combo.addItems(available_profiles)
        if settings.user.name and settings.user.name not in available_profiles:
            self.profile_combo.addItem(settings.user.name)
        self.profile_combo.setCurrentText(settings.user.name)

        self.user_name_edit.setText(settings.user.name)
        self.mode_combo.setCurrentText(settings.run.mode)
        self.screen_path_edit.setText(settings.paths.screen)
        self.returns_path_edit.setText(settings.paths.returns)
        self.blacklist_path_edit.setText(settings.paths.liste_noire)
        self.output_dir_edit.setText(settings.paths.output_dir)
        self.score_pivot_dir_edit.setText(settings.paths.score_pivot_esg_path)

        self.ptf_name_edit.setText(settings.run.ptf_name)
        self.bench_combo.setCurrentText(settings.run.bench)
        self.custom_metrics_edit.setText(", ".join(settings.run.metrics))
        self.percentile_edit.setText(str(settings.run.percentile))
        self.top_checkbox.setChecked(settings.run.top)
        self.ponderation_combo.setCurrentText(settings.run.ponderation)
        self.esg_exclusion_edit.setText(str(settings.run.esg_exclusion))
        self.cut_mkt_cap_edit.setText(str(settings.run.cut_mkt_cap))
        self.score_pivot_esg_edit.setText("" if settings.run.score_pivot_esg is None else str(settings.run.score_pivot_esg))
        self.score_neutral_combo.setCurrentText(settings.run.score_neutral)
        self.weight_neutral_combo.setCurrentText(settings.run.weight_neutral)
        self.top_mandatory_edit.setText("" if settings.run.top_mandatory is None else str(settings.run.top_mandatory))
        self.cap_weight_threshold_edit.setText("" if settings.run.cap_weight_threshold is None else str(settings.run.cap_weight_threshold))
        self.mode_monthly_prod_checkbox.setChecked(settings.run.mode_monthly_prod)
        self.start_date_edit.setText(settings.run.start_date)
        self.freq_rebal_edit.setText("" if settings.run.freq_rebal is None else str(settings.run.freq_rebal))
        self.screen_start_date_combo.setCurrentText(settings.run.screen_start_date)
        self.fill_method_combo.setCurrentText(settings.run.fill_method)
        self.max_weight_edit.setText(str(settings.run.max_weight))
        self.sector_neutral_checkbox.setChecked(settings.run.sector_neutral)
        self.reco_secto_edit.setPlainText(", ".join(str(value) for value in settings.run.reco_secto))
        self.reco_facto_edit.setPlainText(", ".join(str(value) for value in settings.run.reco_facto))

        self.batch_benches_edit.setText(", ".join(settings.batch.benches))
        self.batch_metrics_edit.setText(", ".join(settings.batch.metrics))
        self.batch_percentiles_edit.setText(", ".join(str(value) for value in settings.batch.percentiles))
        self.batch_start_dates_edit.setText(", ".join(settings.batch.start_dates))
        self.batch_top_values_edit.setText(", ".join("true" if value else "false" for value in settings.batch.top_values))

    def load_profile(self) -> None:
        """Charge un profil YAML existant."""

        profile_name = self.profile_combo.currentText().strip() or "default"
        try:
            settings = load_settings(profile_name)
            self.apply_settings(settings)
            self.refresh_inspection()
            self.settings_changed.emit(self.build_settings())
        except Exception as exc:  # pragma: no cover - interaction utilisateur
            QMessageBox.critical(self, "Chargement impossible", str(exc))

    def save_profile(self) -> None:
        """Sauvegarde le profil courant."""

        try:
            settings = self.build_settings()
            profile_name = settings.user.name or self.profile_combo.currentText().strip() or "user1"
            target = save_settings(settings, profile_name=profile_name)
            self.profile_combo.setCurrentText(profile_name)
            QMessageBox.information(self, "Configuration enregistree", f"Configuration sauvegardee dans :\n{target}")
            self.settings_changed.emit(settings)
        except Exception as exc:  # pragma: no cover - interaction utilisateur
            QMessageBox.critical(self, "Sauvegarde impossible", str(exc))

    def refresh_inspection(self) -> None:
        """Recharge l'inspection des fichiers de donnees."""

        settings = self.build_settings()
        payload, report = self._service.inspect_inputs(
            settings.paths.screen,
            settings.paths.returns,
        )

        self.detected_benchmarks.setPlainText("\n".join(payload.get("screen_benchmarks", [])))
        self.detected_metrics.setPlainText("\n".join(payload.get("screen_metrics", [])))
        self.detected_columns.setPlainText("\n".join(payload.get("screen_columns", [])))
        self.inspection_summary.setText(
            " | ".join(
                [
                    f"Rows screen: {payload.get('screen_rows', 0)}",
                    f"Rows returns: {payload.get('returns_rows', 0)}",
                    f"Benchmarks: {len(payload.get('screen_benchmarks', []))}",
                    f"Metrics candidates: {len(payload.get('screen_metrics', []))}",
                ]
            )
        )

        current_bench = self.bench_combo.currentText()
        self.bench_combo.clear()
        self.bench_combo.addItems(payload.get("screen_benchmarks", []))
        self.bench_combo.setCurrentText(current_bench or self._settings.run.bench)

        selected_metrics = set(self._selected_metrics())
        self.metrics_list.clear()
        for metric in payload.get("screen_metrics", []):
            item = QListWidgetItem(metric)
            self.metrics_list.addItem(item)
            if metric in selected_metrics or metric in self._settings.run.metrics:
                item.setSelected(True)

        if report.errors or report.warnings:
            details = []
            details.extend(message.text for message in report.errors)
            details.extend(message.text for message in report.warnings)
            self.inspection_summary.setText(self.inspection_summary.text() + "\n" + "\n".join(details))

        self.settings_changed.emit(settings)
