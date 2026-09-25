@echo off
set "SAMUEL_STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Samuel Assistant.bat"
echo @echo off>"%SAMUEL_STARTUP%"
echo start "" "%~dp0start_samuel.bat">>"%SAMUEL_STARTUP%"
echo Samuel will now start when you sign in to Windows.
pause
