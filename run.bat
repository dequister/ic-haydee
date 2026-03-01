@echo off
setlocal

REM ===== Ajuste aqui se necessário =====
set "PROJECT_DIR=C:\IC\ic-haydee"
set "VENV_DIR=%PROJECT_DIR%\venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "SCRIPT=%PROJECT_DIR%\main_2024.py"

cd /d "%PROJECT_DIR%"

if not exist "%PYTHON_EXE%" (
  echo [ERRO] Nao encontrei o Python da venv em: "%PYTHON_EXE%"
  echo Confirme o caminho da venv.
  pause
  exit /b 1
)

echo Usando: "%PYTHON_EXE%"
"%PYTHON_EXE%" "%SCRIPT%"

echo.
echo Finalizado. (Codigo de saida: %ERRORLEVEL%)
pause
exit /b %ERRORLEVEL%