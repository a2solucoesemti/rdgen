@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0a2\local\Setup-LocalBuild.ps1" -Install %*
set "A2_RESULT=%ERRORLEVEL%"
if not "%A2_RESULT%"=="0" echo Falha na preparacao. Consulte C:\A2ConnectBuild\logs.
pause
exit /b %A2_RESULT%
