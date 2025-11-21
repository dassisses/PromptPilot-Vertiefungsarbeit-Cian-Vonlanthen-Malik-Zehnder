# PromptPilot

Ein modernes Python-Tool zur Verwaltung und Automatisierung von LLM-Prompts mit grafischer Oberfläche und Keyboard-Shortcuts.

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.9+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-API-orange.svg)

## 🎯 Überblick

PromptPilot automatisiert repetitive Aufgaben mit Large Language Models (LLMs). Erstelle wiederverwendbare Prompt-Vorlagen (Presets) und führe sie mit benutzerdefinierten Keyboard-Shortcuts aus - direkt aus der Zwischenablage.

👉 Ein durchspielbares Proof-of-Concept findest du in [POC.md](POC.md).

### Hauptfunktionen

✅ **Preset-Verwaltung** - Erstelle, bearbeite und organisiere Prompt-Vorlagen  
✅ **Keyboard-Shortcuts** - Führe Presets mit individuellen Tastenkombinationen aus  
✅ **API-Integration** - Unterstützt OpenAI (ChatGPT, GPT-4, GPT-3.5-Turbo)  
✅ **Zwischenablage-Workflow** - Nahtlose Integration mit deinem Arbeitsablauf  
✅ **Modernes Dark-Theme** - Benutzerfreundliche grafische Oberfläche  
✅ **Lokale Datenspeicherung** - Alle Daten bleiben auf deinem Computer  

## Quick Start

### Installation

```bash
# 1. Repository klonen oder downloaden
git clone <repository-url>
cd PromptPilot-Vertiefungsarbeit-Cian-Vonlanthen-Malik-Zehnder

# 2. Abhängigkeiten installieren (legt automatisch .venv an)
./scripts/install.sh  # macOS/Linux
# oder
./scripts/install.ps1  # Windows (PowerShell)
```

### Anwendung starten

```bash
# Mit Startskript (empfohlen)
./scripts/start.sh

# Oder manuell
source .venv/bin/activate
python3 main.py
```

## Verwendung

### 1. API-Key konfigurieren

1. Starte die Anwendung
2. Navigiere zu **"API Einstellungen"** (oder drücke `Ctrl+2`)
3. Gib deinen OpenAI API-Key ein (erhältlich auf [platform.openai.com](https://platform.openai.com/api-keys))
4. Klicke auf **"Verbindung testen"**
5. Klicke auf **"Speichern"**

### 2. Preset erstellen

1. Navigiere zu **"Presets"** (oder drücke `Ctrl+1`)
2. Fülle das Formular rechts aus:
   - **Name**: z.B. "Rechtschreibung korrigieren"
   - **Prompt**: z.B. "Korrigiere folgenden Text auf Rechtschreibung und Grammatik:"
   - **API-Typ**: Wähle "ChatGPT" oder "GPT-4"
3. Klicke auf **"Preset Speichern"**

### 3. Keyboard-Shortcut einrichten

1. Klicke auf den **Button** bei deinem Preset
2. Gib eine Tastenkombination ein, z.B. `Ctrl+Shift+R`
3. Klicke **OK**

### 4. Preset verwenden

**Mit Shortcut:**
1. Kopiere Text in die Zwischenablage (z.B. markieren und `Ctrl+C`)
2. Drücke deine Tastenkombination (z.B. `Ctrl+Shift+R`)
3. Das Tool verarbeitet den Text automatisch
4. Das Ergebnis landet in der Zwischenablage
5. Füge es ein mit `Ctrl+V`

**Mit Button:**
1. Kopiere Text in die Zwischenablage
2. Klicke auf **"Ausführen"** bei deinem Preset
3. Das Ergebnis wird angezeigt und ist in der Zwischenablage

## ⌨️ Tastenkombinationen

| Shortcut | Aktion |
|----------|--------|
| `Ctrl+1` | Zur Presets-Seite wechseln |
| `Ctrl+2` | Zur API Einstellungen-Seite wechseln |
| _Benutzerdefiniert_ | Preset ausführen (selbst festgelegt) |

## Projektstruktur

```
PromptPilot/
├── backend.py              # Backend-Logik (API-Calls, Datenverwaltung)
├── frontend.py             # GUI-Anwendung (PySide6)
├── requirements.txt        # Python-Dependencies
├── scripts/                # Hilfsskripte (install/start/build/...)
├── README.md               # Kurzüberblick
├── docs/README.md          # Ausführliche Dokumentation (diese Datei)
└── .venv/                  # Virtuelle Python-Umgebung (auto erstellt)
```

## 🔧 Technologien

- **Python 3.13+** - Programmiersprache
- **PySide6 (Qt6)** - GUI-Framework für modernes Interface
- **OpenAI API** - LLM-Integration (ChatGPT, GPT-4)
- **PyperClip** - Zwischenablage-Integration

## Datenverwaltung

Alle Daten werden lokal in JSON-Dateien gespeichert:

- **`presets.json`** - Deine Preset-Vorlagen (wird automatisch erstellt)
- **`credentials.json`** - Deine API-Keys (vertraulich, lokal gespeichert!)
- **`settings.json`** - UI-Einstellungen wie Theme und Shortcut-Anzeige

Die Dateien befinden sich im Projektverzeichnis, sind aber in `.gitignore`
eingetragen. **Sicherheitshinweis**: Teile die `credentials.json` niemals öffentlich!

## 🐛 Problembehandlung

### Fehler beim Starten

```bash
# Dependencies neu installieren
source .venv/bin/activate
pip install --upgrade -r requirements.txt
```

### "No module named..." Fehler

```bash
# Stelle sicher, dass die virtuelle Umgebung aktiviert ist
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate      # Windows

# Dependencies installieren
pip install -r requirements.txt
```

### API-Test schlägt fehl

- ✓ Prüfe deinen API-Key auf [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- ✓ Stelle sicher, dass du Guthaben auf deinem OpenAI-Account hast
- ✓ Prüfe deine Internetverbindung
- ✓ Teste mit einem neuen API-Key

### GUI startet nicht

```bash
# Prüfe ob alle Dependencies installiert sind
source .venv/bin/activate
python3 -c "import PySide6; import openai; import pyperclip; print('✓ Alle OK')"
```

## Backend-Tests

Um das Backend direkt zu testen:

```bash
source .venv/bin/activate
python3 backend.py
```

Das führt automatische Tests aus und zeigt ob alles funktioniert.

## 🎓 Beispiel-Workflows

### Workflow 1: E-Mail professionalisieren

1. **Preset erstellen**:
   - Name: "E-Mail professionalisieren"
   - Prompt: "Formuliere folgende E-Mail professionell und höflich um:"
   - Shortcut: `Ctrl+Shift+E`

2. **Verwendung**:
   - Schreibe deine E-Mail
   - Markiere den Text und kopiere ihn
   - Drücke `Ctrl+Shift+E`
   - Füge die professionalisierte Version ein

### Workflow 2: Code dokumentieren

1. **Preset erstellen**:
   - Name: "Code dokumentieren"
   - Prompt: "Erkläre folgenden Code und füge Kommentare hinzu:"
   - Shortcut: `Ctrl+Shift+D`

2. **Verwendung**:
   - Kopiere deinen Code
   - Drücke `Ctrl+Shift+D`
   - Erhalte dokumentierten Code

### Workflow 3: Text zusammenfassen

1. **Preset erstellen**:
   - Name: "Text zusammenfassen"
   - Prompt: "Fasse folgenden Text in 3 Sätzen zusammen:"
   - Shortcut: `Ctrl+Shift+S`

2. **Verwendung**:
   - Kopiere langen Text
   - Drücke `Ctrl+Shift+S`
   - Erhalte Zusammenfassung

## Wichtige Hinweise

### Kosten

OpenAI API-Calls sind kostenpflichtig. Die Kosten hängen vom verwendeten Modell ab:
- **GPT-3.5-Turbo**: ~$0.002 pro 1K Tokens
- **GPT-4**: ~$0.03 pro 1K Tokens

Überwache deine Nutzung im [OpenAI Dashboard](https://platform.openai.com/usage).

### Datenschutz

- Alle API-Calls werden an OpenAI-Server gesendet
- Deine Presets und Credentials werden nur lokal gespeichert
- Lies die [OpenAI Privacy Policy](https://openai.com/policies/privacy-policy)

### Rate Limits

OpenAI hat Rate Limits pro Minute. Bei intensiver Nutzung können Requests abgelehnt werden.

## Team

**Cian Vonlanthen & Malik Zehnder**  
Vertiefungsarbeit 2024/2025

## Lizenz

Dieses Projekt wurde als schulische Vertiefungsarbeit entwickelt.

## Support

Bei Problemen oder Fragen:
1. Prüfe die [QUICKSTART.md](../QUICKSTART.md) für häufige Probleme
2. Prüfe die [Issues](../../issues) im Repository
3. Kontaktiere die Entwickler

## Updates

Um die neueste Version zu erhalten:

```bash
git pull origin main
source .venv/bin/activate
pip install --upgrade -r requirements.txt
```

---

**Viel Erfolg mit PromptPilot! 🚀**

