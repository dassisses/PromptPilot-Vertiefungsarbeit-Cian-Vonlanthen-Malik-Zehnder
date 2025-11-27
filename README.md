# PromptPilot

Modernes Desktop-Tool, um wiederverwendbare LLM-Prompts per Shortcut auszuführen. Presets, API-Keys und Einstellungen werden lokal als JSON gespeichert und lassen sich bequem in einer PySide6-Oberfläche pflegen.

Dieses Projekt entstand im Rahmen der Vertiefungsarbeit von **Malik Zehnder** und **Cian Vonlanthen**.

## Inhaltsverzeichnis
1. [Was macht die App?](#was-macht-die-app)
2. [Plattformen](#plattformen)
3. [Installation & Start](#installation--start)
4. [Packaged Build](#packaged-build)
5. [Datenablage (persistente JSONs)](#datenablage-persistente-jsons)
6. [GUI-Überblick & Screenshots](#gui-%C3%BCberblick--screenshots)
7. [Weiterführende Doku](#weiterf%C3%BChrende-doku)
8. [Projektstruktur](#projektstruktur)

## Was macht die App?
- Presets anlegen/bearbeiten und optional mit Shortcuts versehen
- Globale Shortcuts + Zwischenablage-Workflow: Text kopieren, Shortcut drücken, Ergebnis landet wieder in der Zwischenablage
- OpenAI out of the box, weitere Provider vorbereitet
- Modernes Dark-Theme, lokale JSON-Datenspeicherung

## Plattformen
Grundsätzlich **cross-platform** (macOS, Linux, Windows). Wir haben primär auf macOS getestet; unter Windows sollte es mit den mitgelieferten PowerShell-Skripten ebenfalls funktionieren.

## Installation & Start
**Option 1: Fertiges Release**  
- Lade das aktuelle Release (gepackte App) aus dem Releases-Bereich herunter und starte die Anwendung direkt.

**Option 2: Aus dem Repo**
```bash
# Abhängigkeiten installieren (.venv wird automatisch angelegt)
./scripts/install.sh   # macOS/Linux
./scripts/install.ps1  # Windows (PowerShell)

# Anwendung starten
./scripts/start.sh
./scripts/start.ps1    # Windows (PowerShell)
```

## Packaged Build
Eigenes Bundle erzeugen (PyInstaller onedir):
```bash
./scripts/build_app.sh
```
Das Ergebnis liegt in `dist/` (macOS: `.app`, Linux/Windows: ausführbare Datei). Onedir-Build vermeidet den doppelten Start.

## Datenablage (persistente JSONs)
- macOS: `~/Library/Application Support/PromptPilot/`
- Windows: `%APPDATA%\\PromptPilot\\`
- Linux: `~/.config/promptpilot/`

Beim ersten Start werden `presets.json`, `credentials.json` und `settings.json` aus den gebündelten Defaults kopiert und danach dauerhaft dort gepflegt.

## GUI-Überblick & Screenshots
Screenshots (bitte ergänzen):
- Preset-Übersicht mit Liste + Formular zum Bearbeiten/Anlegen
- API-Einstellungen mit Eingabefeld und “Verbindung testen”
- Shortcut-Dialog zur Vergabe individueller Tastenkombinationen
- Statusbar/Tray-Menü mit Preset-Auswahl

Kurzer Flow: App starten → API-Key setzen → Preset anlegen → Shortcut vergeben → Text kopieren → Shortcut drücken → Ergebnis aus Zwischenablage einfügen.

## Weiterführende Doku
- Konzept: `docs/Konzept.md`
- Durchspielbarer POC: `docs/POC.md`
- Ausführliche Anleitung: `docs/README.md`

## Projektstruktur
```
backend.py           # Backend-Logik und API-Integration
frontend.py          # PySide6-Oberfläche
mac_statusbar.py     # macOS Statusbar-Integration
scripts/             # Install-, Start- und Build-Skripte
docs/                # Konzept, POC, Anleitungen
requirements.txt     # Python-Abhängigkeiten
promptpilot.spec     # PyInstaller-Konfiguration
```
