@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0UTWORZ_SKROT_START.ps1"
if errorlevel 1 (
  echo Nie udalo sie utworzyc skrotu. Sprawdz polityke IT.
  pause
  exit /b 1
)
pause
