# PromptPilot

PromptPilot ist eine Desktop-App zum Ausführen wiederverwendbarer LLM-Prompts mit nur einem Shortcut. Presets, API-Keys und Einstellungen werden lokal gespeichert und können direkt über eine PySide6-Oberfläche gepflegt werden.

## Features
- Preset-Verwaltung mit Provider-/Modell-Auswahl
- Globale Shortcuts und Zwischenablage-Workflow
- OpenAI-Integration out of the box (weitere Provider vorbereitet)
- Dark-Theme-UI, lokale JSON-Datenspeicherung

## Voraussetzungen
- Python 3.10 oder neuer
- macOS, Linux oder Windows (Windows via PowerShell-Skripte)
- Ein OpenAI API-Key für echte Requests

## Installation & Start
```bash
# Abhängigkeiten installieren (.venv wird automatisch angelegt)
./scripts/install.sh

# Anwendung starten
./scripts/start.sh
```

## Proof of Concept
Das Konzept ist in `docs/Konzept.md` dokumentiert. Ein nachspielbares Proof-of-Concept findest du in `docs/POC.md` – damit kannst du mit dem Standard-Preset und einem OpenAI-Key den End-to-End-Fluss verifizieren.

## App bauen (PyInstaller)
Das Build-Skript erzeugt ein lauffähiges Bundle im `dist/`-Ordner und kümmert sich um alle Abhängigkeiten:
```bash
./scripts/build_app.sh
```
Danach findest du die ausführbare Anwendung in `dist/` (unter macOS als `.app`, unter Linux/Windows als ausführbare Datei). Standard-JSON-Dateien werden bei Bedarf automatisch erzeugt.

## Projektstruktur
```
backend.py           # Backend-Logik und API-Integration
frontend.py          # PySide6-Oberfläche
scripts/             # install-, start- und build-Skripte
docs/                # Konzept, POC und ausführliche Doku
requirements.txt     # Python-Abhängigkeiten
promptpilot.spec     # PyInstaller-Konfiguration
```

## Weiterführende Infos
Eine ausführliche Bedienungsanleitung inkl. Workflows findest du in [docs/README.md](docs/README.md).
