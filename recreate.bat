@echo off
setlocal
call "%~dp0parquet_database\run.bat" -Profile local -Refresh %*
exit /b %ERRORLEVEL%
