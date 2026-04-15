@echo off
setlocal

REM Se placer dans le dossier du projet.
cd /d "%~dp0"

REM Ajouter le dossier source au PYTHONPATH pour permettre un lancement direct.
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

REM Detecter un interpreteur Python disponible.
set "PY_CMD="
set "PY_GUI_CMD="

REM Priorite 1 : interpreteur force par variable d'environnement locale.
if defined BACKTEST_GUI_PYTHON (
    if exist "%BACKTEST_GUI_PYTHON%" (
        set "PY_CMD=%BACKTEST_GUI_PYTHON%"
    )
)

if defined PY_CMD (
    set "PY_GUI_CMD=%PY_CMD:python.exe=pythonw.exe%"
    if not exist "%PY_GUI_CMD%" set "PY_GUI_CMD="
)

REM Priorite 2 : chemins courants Anaconda / Miniconda.
if not defined PY_CMD (
    for %%P in (
        "%USERPROFILE%\anaconda3\python.exe"
        "%LOCALAPPDATA%\anaconda3\python.exe"
        "%ProgramData%\anaconda3\python.exe"
        "%USERPROFILE%\miniconda3\python.exe"
        "%LOCALAPPDATA%\miniconda3\python.exe"
        "%ProgramData%\miniconda3\python.exe"
    ) do (
        if not defined PY_CMD (
            if exist %%~P (
                set "PY_CMD=%%~P"
            )
        )
    )
)

if defined PY_CMD if not defined PY_GUI_CMD (
    set "PY_GUI_CMD=%PY_CMD:python.exe=pythonw.exe%"
    if not exist "%PY_GUI_CMD%" set "PY_GUI_CMD="
)

REM Priorite 3 : interpreteur Python accessible via le PATH.
if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    where py >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py"
)

if not defined PY_CMD (
    echo.
    echo Python est introuvable sur cette machine.
    echo Installez Python puis relancez ce fichier.
    echo.
    pause
    exit /b 1
)

REM Verifier que les dependances minimales sont disponibles.
"%PY_CMD%" -c "import PySide6, pandas, plotly, yaml; import ma_librairie" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Les dependances du projet ne sont pas installees.
    echo Lancez la commande suivante dans ce dossier :
    echo     "%PY_CMD%" -m pip install -e .
    echo.
    pause
    exit /b 1
)

REM Lancer l'application sans garder une console ouverte si possible.
if defined PY_GUI_CMD (
    start "" "%PY_GUI_CMD%" -m ma_librairie.runner
    exit /b 0
)

where pythonw >nul 2>&1
if not errorlevel 1 (
    start "" pythonw -m ma_librairie.runner
    exit /b 0
)

where pyw >nul 2>&1
if not errorlevel 1 (
    start "" pyw -m ma_librairie.runner
    exit /b 0
)

REM Repli sur le mode console standard.
"%PY_CMD%" -m ma_librairie.runner
if errorlevel 1 (
    echo.
    echo Le lancement de Backtest GUI a echoue.
    pause
    exit /b 1
)

exit /b 0
