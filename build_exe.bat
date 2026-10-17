@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3.10 ou mais novo em https://www.python.org/downloads/
    echo e marque a opcao "Add python.exe to PATH" na instalacao. Depois rode este arquivo de novo.
    pause
    exit /b 1
)

echo [1/3] Criando ambiente...
py -m venv .venv || goto :erro
call .venv\Scripts\activate || goto :erro
python -m pip install --upgrade pip || goto :erro

echo [2/3] Instalando dependencias...
pip install -e . pyinstaller || goto :erro

echo [3/3] Gerando o executavel...
pyinstaller --noconfirm --onefile --noconsole --name FireTVDesktop --paths src app.py || goto :erro

echo.
echo Pronto! O programa esta em: dist\FireTVDesktop.exe
pause
exit /b 0

:erro
echo.
echo Algo deu errado. Copie as mensagens acima e me envie.
pause
exit /b 1
