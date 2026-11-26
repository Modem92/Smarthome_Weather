@echo off
cd /d "%~dp0"
call "%~dp0windows\run_python.cmd" -m tools.pi.desktop_icon --remote
pause
exit /b %ERRORLEVEL%
