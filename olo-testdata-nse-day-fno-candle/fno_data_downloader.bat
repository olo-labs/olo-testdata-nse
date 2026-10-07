@echo off
setlocal EnableExtensions
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0download_fno_data.ps1" %*
exit /b %ERRORLEVEL%
