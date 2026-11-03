@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Preparando ambiente...
if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 python -m venv .venv
    if errorlevel 1 goto :erro
)
set "APP_PYTHON=.venv\Scripts\python.exe"
"%APP_PYTHON%" -m pip install --upgrade pip || goto :erro

echo [2/4] Instalando dependencias...
"%APP_PYTHON%" -m pip install -e . pyinstaller || goto :erro

echo [3/4] Gerando o executavel...
"%APP_PYTHON%" tools\build_windows.py || goto :erro

echo [4/4] Criando atalho na Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0criar_atalho.ps1"
if errorlevel 1 echo O executavel foi criado, mas o atalho nao. Rode criar_atalho.ps1 depois.

echo.
echo Pronto! O programa esta em: dist\FireTVDesktop.exe
echo Instalador: dist\FireTVDesktopSetup.exe
echo Abra pelo atalho Fire TV Desktop ou fixe o aplicativo na barra de tarefas.
pause
exit /b 0

:erro
echo.
echo Algo deu errado. Copie as mensagens acima e me envie.
pause
exit /b 1
