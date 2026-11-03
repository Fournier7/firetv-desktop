"""Instalação por usuário, atalhos e desinstalação sem apagar os dados pessoais."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable


def default_install_dir() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "Programs" / "FireTVDesktop"


def _literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def shell_script(target: Path) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$folder = {_literal(target)}
$exe = Join-Path $folder 'FireTVDesktop.exe'
$uninstaller = Join-Path $folder 'desinstalar.ps1'
$shell = New-Object -ComObject WScript.Shell
foreach ($location in @($shell.SpecialFolders.Item('Desktop'), [Environment]::GetFolderPath('Programs'))) {{
    $shortcut = $shell.CreateShortcut((Join-Path $location 'Fire TV Desktop.lnk'))
    $shortcut.TargetPath = $exe
    $shortcut.WorkingDirectory = $folder
    $shortcut.IconLocation = "$exe,0"
    $shortcut.Description = 'Controle do Fire TV Stick'
    $shortcut.Save()
}}
$key = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\FireTVDesktop'
New-Item -Path $key -Force | Out-Null
$powershell = Join-Path $env:SystemRoot 'System32\\WindowsPowerShell\\v1.0\\powershell.exe'
$uninstallCommand = '"' + $powershell + '" -NoProfile -ExecutionPolicy Bypass -File "' + $uninstaller + '"'
$values = @{{ DisplayName='Fire TV Desktop'; DisplayVersion='0.1.0'; InstallLocation=$folder;
    DisplayIcon="$exe,0"; UninstallString=$uninstallCommand }}
foreach ($name in $values.Keys) {{ New-ItemProperty -Path $key -Name $name -Value $values[$name] -PropertyType String -Force | Out-Null }}
foreach ($name in @('NoModify', 'NoRepair')) {{ New-ItemProperty -Path $key -Name $name -Value 1 -PropertyType DWord -Force | Out-Null }}
"""


def uninstall_script(target: Path) -> str:
    return f"""$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$folder = {_literal(target)}
$expected = Join-Path $env:LOCALAPPDATA 'Programs\\FireTVDesktop'
if ([IO.Path]::GetFullPath($folder) -ne [IO.Path]::GetFullPath($expected)) {{ throw 'Pasta de instalação inesperada.' }}
$exe = Join-Path $folder 'FireTVDesktop.exe'
$answer = [System.Windows.Forms.MessageBox]::Show('Desinstalar Fire TV Desktop? Configurações e histórico serão preservados.', 'Fire TV Desktop', 'YesNo', 'Question')
if ($answer -ne 'Yes') {{ exit 0 }}
if (Get-Process -Name FireTVDesktop -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq $exe }}) {{
    [System.Windows.Forms.MessageBox]::Show('Feche o Fire TV Desktop antes de desinstalar.', 'Fire TV Desktop') | Out-Null
    exit 1
}}
$shell = New-Object -ComObject WScript.Shell
foreach ($location in @($shell.SpecialFolders.Item('Desktop'), [Environment]::GetFolderPath('Programs'))) {{
    $link = Join-Path $location 'Fire TV Desktop.lnk'
    if (Test-Path -LiteralPath $link) {{
        if ($shell.CreateShortcut($link).TargetPath -eq $exe) {{ Remove-Item -LiteralPath $link }}
    }}
}}
foreach ($name in @('FireTVDesktop.exe', 'desinstalar.ps1')) {{
    $file = Join-Path $folder $name
    if (Test-Path -LiteralPath $file) {{ Remove-Item -LiteralPath $file }}
}}
if (-not (Get-ChildItem -LiteralPath $folder -Force)) {{ Remove-Item -LiteralPath $folder }}
$key = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\FireTVDesktop'
if (Test-Path -LiteralPath $key) {{ Remove-Item -LiteralPath $key }}
[System.Windows.Forms.MessageBox]::Show('Aplicativo desinstalado. Seus dados foram preservados.', 'Fire TV Desktop') | Out-Null
"""


def integrate_shell(target: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="firetv-setup-") as directory:
        script = Path(directory) / "atalhos.ps1"
        script.write_text(shell_script(target), encoding="utf-8-sig")
        powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        subprocess.run([
            str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


def install_payload(
    payload: Path, target: Path,
    integrate: Callable[[Path], None] = integrate_shell,
) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
        shutil.copyfile(payload, temporary)
        temporary.replace(target / "FireTVDesktop.exe")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    (target / "desinstalar.ps1").write_text(uninstall_script(target), encoding="utf-8-sig")
    integrate(target)
    return target / "FireTVDesktop.exe"
