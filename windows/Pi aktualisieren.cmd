@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0run_python.cmd" -m tools.windows.updater
exit /b %ERRORLEVEL%
