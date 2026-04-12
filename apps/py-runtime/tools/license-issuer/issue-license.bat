@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if exist "venv\Scripts\python.exe" (
  set "PYTHON_BIN=venv\Scripts\python.exe"
) else (
  set "PYTHON_BIN=python"
)

"%PYTHON_BIN%" "apps\py-runtime\tools\license-issuer\issue_license.py" --interactive
set "EXIT_CODE=%ERRORLEVEL%"

pause
exit /b %EXIT_CODE%
