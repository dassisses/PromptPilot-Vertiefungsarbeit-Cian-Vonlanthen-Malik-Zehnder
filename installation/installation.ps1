# Script zur Installation von Python-Abhängigkeiten für Windows (PowerShell)

# 1. Erstelle eine virtuelle Umgebung
Write-Host "Erstelle virtuelle Umgebung 'venv'..."
python -m venv venv

# 2. Aktiviere die virtuelle Umgebung
Write-Host "Aktiviere die virtuelle Umgebung..."
# Achtung: Das Aktivierungsskript muss mit '.' ausgeführt werden
$activation_script = ".\venv\Scripts\Activate.ps1"
if (Test-Path $activation_script) {
    . $activation_script
    Write-Host "Virtuelle Umgebung aktiviert."

    # 3. Installiere die Python-Pakete
    Write-Host "Installiere PySide6, pyperclip, openai und pynput..."
    pip install PySide6 pyperclip openai pynput

    Write-Host ""
    Write-Host "Installation abgeschlossen."
    Write-Host "Die Umgebung ist jetzt aktiv. Zum Beenden tippen Sie: deactivate"
} else {
    Write-Host "FEHLER: Aktivierungsskript nicht gefunden. Stellen Sie sicher, dass Python und pip korrekt installiert sind."
}   