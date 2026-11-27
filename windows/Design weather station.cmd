@echo off
setlocal
cd /d "%~dp0.."
set "WETTERSTATION_DESIGNER_PYTHONW="
if exist "%LOCALAPPDATA%\Wetterstation\venv\Scripts\pythonw.exe" set "WETTERSTATION_DESIGNER_PYTHONW=%LOCALAPPDATA%\Wetterstation\venv\Scripts\pythonw.exe"
if not defined WETTERSTATION_DESIGNER_PYTHONW if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe" set "WETTERSTATION_DESIGNER_PYTHONW=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if defined WETTERSTATION_DESIGNER_PYTHONW goto graphical
call "%~dp0run_python.cmd" tools/windows/designer.py %*
exit /b %ERRORLEVEL%
:graphical
start "" "%WETTERSTATION_DESIGNER_PYTHONW%" tools/windows/designer.py %*
exit /b 0
