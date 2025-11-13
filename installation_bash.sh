#!/bin/bash
# Script zur Installation von Python-Abhängigkeiten für Linux und macOS

# 1. Erstelle eine virtuelle Umgebung
echo "Erstelle virtuelle Umgebung 'venv'..."
python3 -m venv venv

# 2. Aktiviere die virtuelle Umgebung
echo "Aktiviere die virtuelle Umgebung..."
source venv/bin/activate

# 3. Installiere die Python-Pakete
echo "Installiere PySide6, pyperclip, openai und pynput..."
pip install PySide6 pyperclip openai pynput

# HINWEIS FÜR LINUX:
echo ""
echo "--- HINWEIS FÜR LINUX-Systeme ---"
echo "Für die volle Funktionalität der Zwischenablage (pyperclip) werden"
echo "zusätzliche System-Tools benötigt. Installiere diese bei Bedarf:"
echo "Für Debian/Ubuntu: sudo apt-get install xclip xsel -y"
echo "--------------------------------"

echo ""
echo "Installation abgeschlossen."
echo "Die virtuelle Umgebung ist jetzt aktiv. Zum Beenden tippen Sie: deactivate"