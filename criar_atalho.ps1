param(
    [string]$ExecutablePath = (Join-Path $PSScriptRoot 'dist\FireTVDesktop.exe')
)

$ErrorActionPreference = 'Stop'
$target = (Resolve-Path -LiteralPath $ExecutablePath).Path
$shortcutShell = New-Object -ComObject WScript.Shell
$desktopFolder = $shortcutShell.SpecialFolders.Item('Desktop')
$shortcutPath = Join-Path $desktopFolder 'Fire TV Desktop.lnk'
$shortcut = $shortcutShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = Split-Path -Parent $target
$shortcut.IconLocation = "$target,0"
$shortcut.Description = 'Controle do Fire TV Stick'
$shortcut.Save()
Write-Host "Atalho criado: $shortcutPath"
