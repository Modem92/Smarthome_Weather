@echo off
cd /d "%~dp0"
call "%~dp0windows\run_python.cmd" -m tools.pi.update build --keep-layout
pause
exit /b %ERRORLEVEL%
