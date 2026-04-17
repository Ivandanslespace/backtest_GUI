# Backtest GUI

Application desktop en `PySide6` pour lancer des backtests sans passer par Jupyter, en s'appuyant sur `BacktestEngine.py`.

## Objectif

Cette application permet de :

- charger les donnees `screen` et `returns` ;
- configurer un backtest via une interface graphique ;
- lancer un run simple ou un batch ;
- sauvegarder les configurations utilisateur en YAML ;
- centraliser les artefacts de run dans `runs/` ;
- consulter l'historique et les resultats sans notebook.

## Structure du projet

```text
Backtest_GUI/
├── BacktestEngine.py
├── Backtest_GUI_Cahier_des_charges.md
├── configs/
├── logs/
├── runs/
├── pyproject.toml
└── src/
    └── bt_gui/
```

## Installation

```bash
pip install -e .
```

## Lancement

```bash
backtest-gui
```

ou :

```bash
python -m bt_gui.runner
```

## Remarques
- Les configurations utilisateur sont stockees dans `configs/`.
- Les journaux applicatifs sont stockes dans `logs/`.
- Les artefacts de run sont stockes dans `runs/`.
