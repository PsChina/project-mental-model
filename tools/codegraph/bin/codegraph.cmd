@echo off
rem codegraph launcher (Windows). Runs cli.py, which self-bootstraps into .venv
rem (T2) when present, otherwise the regex T0 tier. Propagates cli.py's exit code.
setlocal
set "ROOT=%~dp0.."
where python >nul 2>nul
if %errorlevel%==0 (
  python "%ROOT%\cli.py" %*
  exit /b %errorlevel%
) else (
  py "%ROOT%\cli.py" %*
  exit /b %errorlevel%
)
