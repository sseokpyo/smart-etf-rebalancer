param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

& $Python -m pip install --upgrade pyinstaller
& $Python -m PyInstaller --noconfirm --clean --onefile --name "차곡 투자 대시보드" --add-data "invest_bot\static;invest_bot\static" invest_bot\desktop.py

Write-Host "완료: dist\차곡 투자 대시보드.exe"
