@echo off
setlocal
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass ^
  -File "%SCRIPT_DIR%run_installed_extension_matrix.ps1" %*
set "MATRIX_EXIT_CODE=%ERRORLEVEL%"

exit /b %MATRIX_EXIT_CODE%
