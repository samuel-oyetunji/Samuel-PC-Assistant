@echo off
setlocal
cd /d "%~dp0"

set "SAMUEL_PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 --version >nul 2>nul
  if not errorlevel 1 set "SAMUEL_PYTHON=py -3.11"
)

if not defined SAMUEL_PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 set "SAMUEL_PYTHON=python"
)

if not defined SAMUEL_PYTHON goto :python_missing

echo Using Python:
%SAMUEL_PYTHON% --version
%SAMUEL_PYTHON% -m venv .venv
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install --timeout 120 --retries 10 --upgrade pip
.venv\Scripts\python.exe -m pip install --timeout 120 --retries 10 -r requirements.txt
if errorlevel 1 goto :failed
echo.
echo Installation completed. Double-click start_samuel.bat.
pause
exit /b 0

:python_missing
echo.
echo Python was not found on this PC.
echo Install Python, then install runtime 3.11 with: py install 3.11
echo Then close this window and run setup_windows.bat again.
pause
exit /b 1

:failed
echo.
echo Installation failed. Copy the error and send it to me.
pause
exit /b 1
