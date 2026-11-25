@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import tkinter, sqlite3" >nul 2>nul
    if not errorlevel 1 (
        py -3 main.py
        if errorlevel 1 pause
        exit /b
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import tkinter, sqlite3" >nul 2>nul
    if not errorlevel 1 (
        python main.py
        if errorlevel 1 pause
        exit /b
    )
)
echo Нужен Python 3.10 или новее с компонентом Tcl/Tk и модулем sqlite3.
echo Дополнительные пакеты pip не нужны.
pause
