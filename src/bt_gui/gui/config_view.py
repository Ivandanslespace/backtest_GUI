"""Vue de configuration principale."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bt_gui.config import (
    create_profile_from_settings,
    list_available_profiles,
    load_settings,
    rename_profile_from_settings,
    save_settings,
)
from bt_gui.config.settings import AppSettings
from bt_gui.core.backtest_runner import BacktestService


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


def _format_compact_lines(items: list[str], items_per_line: int) -> str:
    """Formate une liste sur plusieurs lignes compactes."""

    if not items:
        return ""
    return "\n".join(
        " | ".join(items[index : index + items_per_line])
        for index in range(0, len(items), items_per_line)
    )


class ConfigView(QWidget):
    """Page de configuration et d'inspection des donnees."""

    settings_changed = Signal(object)

    def __init__(self, service: BacktestService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._current_profile_name = "user1"
        self._settings = load_settings("user1")
        self._build_ui()
        self.apply_settings(self._settings, profile_name=self._current_profile_name)
        self.refresh_inspection()

    def _build_ui(self) -> None:
        """Construit l'interface."""

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        root_layout.addLayout(content_layout)

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
        self.create_button = QPushButton("Nouveau")
        self.create_button.setObjectName("SecondaryButton")
        self.rename_button = QPushButton("Renommer")
        self.rename_button.setObjectName("SecondaryButton")
        self.inspect_button = QPushButton("Actualiser l'inspection")
        self.inspect_button.setObjectName("SecondaryButton")
        controls_box.addWidget(self.profile_combo)
        controls_box.addWidget(self.load_button)
        controls_box.addWidget(self.save_button)
        controls_box.addWidget(self.create_button)
        controls_box.addWidget(self.rename_button)
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
        self.create_button.clicked.connect(self.create_profile)
        self.rename_button.clicked.connect(self.rename_profile)
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
        general_grid = QGridLayout(general_card)
        general_grid.setHorizontalSpacing(14)
        general_grid.setVerticalSpacing(10)
        general_grid.setColumnStretch(1, 1)
        general_grid.setColumnStretch(3, 1)
        general_grid.setColumnStretch(5, 1)

        self.ptf_name_edit = QLineEdit()
        self.bench_combo = QComboBox()
        self.bench_combo.setEditable(True)
        self.metrics_list = QListWidget()
        self.metrics_list.setObjectName("MetricsList")
        self.metrics_list.setSelectionMode(QListWidget.MultiSelection)
        self.metrics_list.setViewMode(QListView.IconMode)
        self.metrics_list.setFlow(QListView.LeftToRight)
        self.metrics_list.setWrapping(True)
        self.metrics_list.setResizeMode(QListView.Adjust)
        self.metrics_list.setMovement(QListView.Static)
        self.metrics_list.setUniformItemSizes(True)
        self.metrics_list.setSpacing(4)
        self.metrics_list.setGridSize(QSize(200, 34))
        self.metrics_list.setMinimumHeight(118)
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

        def add_triplet(
            row: int,
            first_label: str,
            first_widget: QWidget,
            second_label: str,
            second_widget: QWidget,
            third_label: str,
            third_widget: QWidget,
        ) -> int:
            general_grid.addWidget(QLabel(first_label), row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
            general_grid.addWidget(first_widget, row, 1)
            general_grid.addWidget(QLabel(second_label), row, 2, alignment=Qt.AlignRight | Qt.AlignVCenter)
            general_grid.addWidget(second_widget, row, 3)
            general_grid.addWidget(QLabel(third_label), row, 4, alignment=Qt.AlignRight | Qt.AlignVCenter)
            general_grid.addWidget(third_widget, row, 5)
            return row + 1

        row = 0
        row = add_triplet(
            row,
            "Nom du portefeuille",
            self.ptf_name_edit,
            "Benchmark",
            self.bench_combo,
            "Percentile",
            self.percentile_edit,
        )

        general_grid.addWidget(QLabel("Metrics detectees"), row, 0, alignment=Qt.AlignRight | Qt.AlignTop)
        general_grid.addWidget(self.metrics_list, row, 1, 1, 5)
        row += 1

        row = add_triplet(
            row,
            "Metrics manuelles",
            self.custom_metrics_edit,
            "Ponderation",
            self.ponderation_combo,
            "Cut market cap",
            self.cut_mkt_cap_edit,
        )
        row = add_triplet(
            row,
            "ESG exclusion",
            self.esg_exclusion_edit,
            "Score pivot ESG",
            self.score_pivot_esg_edit,
            "Max weight",
            self.max_weight_edit,
        )
        row = add_triplet(
            row,
            "Score neutral",
            self.score_neutral_combo,
            "Weight neutral",
            self.weight_neutral_combo,
            "Date de debut",
            self.start_date_edit,
        )
        row = add_triplet(
            row,
            "Top mandatory",
            self.top_mandatory_edit,
            "Cap weight threshold",
            self.cap_weight_threshold_edit,
            "Frequence rebalancement",
            self.freq_rebal_edit,
        )
        row = add_triplet(
            row,
            "Screen start date",
            self.screen_start_date_combo,
            "Fill method",
            self.fill_method_combo,
            "Reco facto",
            self.reco_facto_edit,
        )

        general_grid.addWidget(self.top_checkbox, row, 0, 1, 2)
        general_grid.addWidget(self.mode_monthly_prod_checkbox, row, 2, 1, 2)
        general_grid.addWidget(self.sector_neutral_checkbox, row, 4, 1, 2)
        row += 1

        general_grid.addWidget(QLabel("Reco secto"), row, 0, alignment=Qt.AlignRight | Qt.AlignTop)
        general_grid.addWidget(self.reco_secto_edit, row, 1, 1, 5)

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
        card_layout = QGridLayout(card)
        card_layout.setHorizontalSpacing(14)
        card_layout.setVerticalSpacing(10)
        card_layout.setColumnStretch(0, 1)
        card_layout.setColumnStretch(1, 1)

        self.inspection_summary = QLabel("Aucune inspection disponible.")
        self.inspection_summary.setWordWrap(True)
        self.inspection_summary.setObjectName("MutedLabel")

        self.detected_benchmarks = QPlainTextEdit()
        self.detected_benchmarks.setReadOnly(True)
        self.detected_benchmarks.setMaximumHeight(110)
        self.detected_metrics = QPlainTextEdit()
        self.detected_metrics.setReadOnly(True)
        self.detected_metrics.setMaximumHeight(110)
        self.detected_columns = QPlainTextEdit()
        self.detected_columns.setReadOnly(True)
        self.detected_columns.setMaximumHeight(160)

        card_layout.addWidget(QLabel("Resume"), 0, 0, 1, 2)
        card_layout.addWidget(self.inspection_summary, 1, 0, 1, 2)
        card_layout.addWidget(QLabel("Benchmarks detectes"), 2, 0)
        card_layout.addWidget(QLabel("Metrics candidates"), 2, 1)
        card_layout.addWidget(self.detected_benchmarks, 3, 0)
        card_layout.addWidget(self.detected_metrics, 3, 1)
        card_layout.addWidget(QLabel("Colonnes du screen"), 4, 0, 1, 2)
        card_layout.addWidget(self.detected_columns, 5, 0, 1, 2)

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

    def _refresh_profile_combo(self, profile_name: str) -> None:
        """Recharge la liste des profils et selectionne le profil actif."""

        available_profiles = list_available_profiles()
        self.profile_combo.clear()
        self.profile_combo.addItems(available_profiles)
        if profile_name and profile_name not in available_profiles:
            self.profile_combo.addItem(profile_name)
        self.profile_combo.setCurrentText(profile_name)

    @staticmethod
    def _validate_profile_name(profile_name: str) -> str:
        """Valide un nom de profil utilisateur."""

        normalized_name = profile_name.strip()
        if not normalized_name:
            raise ValueError("Le nom du profil ne peut pas etre vide.")
        if normalized_name.lower() == "default":
            raise ValueError("Le nom 'default' est reserve.")
        return normalized_name

    def _suggest_profile_name(self) -> str:
        """Construit une proposition de nom pour un nouveau profil."""

        current_name = self._current_profile_name or self.user_name_edit.text().strip() or "user1"
        if current_name == "default":
            return "user1_copy"
        return f"{current_name}_copy"

    def _create_profile_copy(self, profile_name: str) -> Path:
        """Cree un profil a partir du formulaire courant."""

        normalized_name = self._validate_profile_name(profile_name)
        settings = self.build_settings().copy()
        target = create_profile_from_settings(settings, normalized_name)
        settings.user.name = normalized_name
        self.apply_settings(settings, profile_name=normalized_name)
        self.settings_changed.emit(settings)
        return target

    def _rename_current_profile(self, profile_name: str) -> Path:
        """Renomme le profil actif en conservant le formulaire courant."""

        source_name = self._current_profile_name or self.profile_combo.currentText().strip()
        if not source_name:
            raise ValueError("Aucun profil courant a renommer.")
        if source_name == "default":
            raise ValueError("Le profil 'default' ne peut pas etre renomme.")

        normalized_name = self._validate_profile_name(profile_name)
        if normalized_name == source_name:
            raise ValueError("Le nouveau nom doit etre different du nom courant.")

        settings = self.build_settings().copy()
        target = rename_profile_from_settings(source_name, normalized_name, settings)
        settings.user.name = normalized_name
        self.apply_settings(settings, profile_name=normalized_name)
        self.settings_changed.emit(settings)
        return target

    def apply_settings(self, settings: AppSettings, profile_name: str | None = None) -> None:
        """Injecte une configuration dans le formulaire."""

        self._settings = settings.copy()
        current_profile_name = profile_name or settings.user.name
        self._current_profile_name = current_profile_name
        self._refresh_profile_combo(current_profile_name)

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
            self.apply_settings(settings, profile_name=profile_name)
            self.refresh_inspection()
            self.settings_changed.emit(self.build_settings())
        except Exception as exc:  # pragma: no cover - interaction utilisateur
            QMessageBox.critical(self, "Chargement impossible", str(exc))

    def save_profile(self) -> None:
        """Sauvegarde le profil courant."""

        try:
            settings = self.build_settings()
            profile_name = self._current_profile_name or self.profile_combo.currentText().strip() or settings.user.name or "user1"
            profile_name = self._validate_profile_name(profile_name)
            settings.user.name = profile_name
            target = save_settings(settings, profile_name=profile_name)
            self.apply_settings(settings, profile_name=profile_name)
            QMessageBox.information(self, "Configuration enregistree", f"Configuration sauvegardee dans :\n{target}")
            self.settings_changed.emit(settings)
        except Exception as exc:  # pragma: no cover - interaction utilisateur
            QMessageBox.critical(self, "Sauvegarde impossible", str(exc))

    def create_profile(self) -> None:
        """Demande un nom puis cree un nouveau profil utilisateur."""

        profile_name, accepted = QInputDialog.getText(
            self,
            "Nouveau profil",
            "Nom du nouveau profil :",
            text=self._suggest_profile_name(),
        )
        if not accepted:
            return

        try:
            target = self._create_profile_copy(profile_name)
            QMessageBox.information(self, "Profil cree", f"Nouveau profil cree dans :\n{target}")
        except Exception as exc:  # pragma: no cover - interaction utilisateur
            QMessageBox.critical(self, "Creation impossible", str(exc))

    def rename_profile(self) -> None:
        """Demande un nom puis renomme le profil actif."""

        current_name = self._current_profile_name or self.profile_combo.currentText().strip()
        profile_name, accepted = QInputDialog.getText(
            self,
            "Renommer le profil",
            "Nouveau nom du profil :",
            text=current_name,
        )
        if not accepted:
            return

        try:
            target = self._rename_current_profile(profile_name)
            QMessageBox.information(self, "Profil renomme", f"Profil renomme dans :\n{target}")
        except Exception as exc:  # pragma: no cover - interaction utilisateur
            QMessageBox.critical(self, "Renommage impossible", str(exc))

    def refresh_inspection(self) -> None:
        """Recharge l'inspection des fichiers de donnees."""

        settings = self.build_settings()
        payload, report = self._service.inspect_inputs(
            settings.paths.screen,
            settings.paths.returns,
        )

        self.detected_benchmarks.setPlainText("\n".join(payload.get("screen_benchmarks", [])))
        self.detected_metrics.setPlainText("\n".join(payload.get("screen_metrics", [])))
        self.detected_columns.setPlainText(_format_compact_lines(payload.get("screen_columns", []), items_per_line=4))
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
