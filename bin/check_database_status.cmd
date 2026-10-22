@echo off
setlocal

cd /d "%~dp0.."

set VENV_DIR=.venv
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe
set SCRIPT_PATH=src\oregon_processing\execute.py
set ARG1=check_database_status

echo Using virtual environment: %VENV_DIR%


REM --- Check if virtual environment exists ---
if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found at %VENV_DIR%.
    echo Please run setup.cmd first to create the virtual environment.
    pause
    exit /b 1
)

REM --- Activate the virtual environment ---
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Environment ready. Running the script.
echo.

REM --- Run the Python script ---
"%VENV_PYTHON%" "%SCRIPT_PATH%" %ARG1%

set ERR=%ERRORLEVEL%

if %ERR% NEQ 0 (
    echo.
    echo ERROR: The program exited with code %ERR%.
    echo Please read the messages above.
)

echo.
echo ----
echo Script finished.
pause
