@echo off
set "PYTHONUTF8=1"
rem Resolve an installed runtime without embedding a personal account name.
set "WETTERSTATION_PYTHON="
if exist "%LOCALAPPDATA%\Smarthome_Weather\venv\Scripts\python.exe" set "WETTERSTATION_PYTHON=%LOCALAPPDATA%\Smarthome_Weather\venv\Scripts\python.exe"
if not defined WETTERSTATION_PYTHON if exist "%LOCALAPPDATA%\Wetterstation\venv\Scripts\python.exe" set "WETTERSTATION_PYTHON=%LOCALAPPDATA%\Wetterstation\venv\Scripts\python.exe"
if not defined WETTERSTATION_PYTHON if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "WETTERSTATION_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if defined WETTERSTATION_PYTHON goto run
where.exe py.exe >nul 2>nul
if not errorlevel 1 goto pylauncher
where.exe python.exe >nul 2>nul
if not errorlevel 1 goto pythonpath
echo Python 3.11 oder neuer mit Tkinter und Projektbibliotheken fehlt.
pause
exit /b 1
:run
"%WETTERSTATION_PYTHON%" %*
exit /b %ERRORLEVEL%
:pylauncher
py.exe -3 %*
exit /b %ERRORLEVEL%
:pythonpath
python.exe %*
exit /b %ERRORLEVEL%
