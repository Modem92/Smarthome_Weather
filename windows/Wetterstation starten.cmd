@echo off
setlocal
cd /d "%~dp0.."
set "WETTERSTATION_BUDGET_ROOT=%USERPROFILE%\AppData\Local\Wetterstation\openweather-budget"
call "%~dp0run_python.cmd" -m wetterstation %*
set "WETTERSTATION_EXIT_CODE=%ERRORLEVEL%"
if "%WETTERSTATION_EXIT_CODE%"=="0" exit /b 0
echo.
echo Wetterstation wurde mit Fehler beendet (Code %WETTERSTATION_EXIT_CODE%).
echo Die Fehlermeldung steht oben. Dieses Fenster bleibt zum Lesen offen.
pause
exit /b %WETTERSTATION_EXIT_CODE%
