@echo off
setlocal

set "GIT_EXE=git.exe"
where "%GIT_EXE%" >nul 2>&1
if errorlevel 1 (
    if exist "%ProgramFiles%\Git\bin\git.exe" (
        set "GIT_EXE=%ProgramFiles%\Git\bin\git.exe"
    ) else (
        echo ERROR: Git was not found on PATH or in "%ProgramFiles%\Git\bin".
        exit /b 1
    )
)

echo Updating Git submodules to their latest remote revisions...
"%GIT_EXE%" -C "%~dp0." submodule sync --recursive
if errorlevel 1 exit /b %ERRORLEVEL%

"%GIT_EXE%" -C "%~dp0." submodule update --init --remote --recursive
if errorlevel 1 exit /b %ERRORLEVEL%

echo Applying incremental Parquet changes...
call "%~dp0parquet_database\run.bat" -Profile local %*
exit /b %ERRORLEVEL%
