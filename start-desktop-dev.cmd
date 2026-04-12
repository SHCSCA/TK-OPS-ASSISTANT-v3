@echo off
setlocal

cd /d "%~dp0"
npm run app:dev
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo start-desktop-dev.cmd failed with exit code %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
