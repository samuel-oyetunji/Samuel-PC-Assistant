@echo off
echo Create an API key at https://platform.openai.com/api-keys
set /p "SAMUEL_KEY=Paste your OpenAI API key: "
if "%SAMUEL_KEY%"=="" exit /b 1
setx OPENAI_API_KEY "%SAMUEL_KEY%" >nul
set "SAMUEL_KEY="
echo API key saved to your Windows user environment. Restart Samuel.
pause
