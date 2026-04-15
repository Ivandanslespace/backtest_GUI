"""Point d'entree de l'application."""

from __future__ import annotations

from ma_librairie.gui.app import run_app


def main() -> int:
    """Lance l'interface graphique."""

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
