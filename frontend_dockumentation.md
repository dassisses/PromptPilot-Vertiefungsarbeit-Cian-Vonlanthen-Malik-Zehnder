# Backend Dokumentation - PromptPilot

## Inhaltsverzeichnis
1. [Einleitung](#einleitung)
2. [Konzeption des Backends](#konzeption-des-backends)
3. [Kernfunktionalitäten](#kernfunktionalitäten)
4. [Debug-Modus](#debug-modus)
5. [API-Schnittstellen](#api-schnittstellen)
6. [Verwendungsbeispiele](#verwendungsbeispiele)

---

## Einleitung

Willkommen zur Backend-Dokumentation vom PromptPilot Projekt. In dieser Dokumentation finden Sie alle Informationen über den Aufbau des Backends sowie das Konzept dahinter.

---

## Konzeption des Backends

Das Backend ist für die **Datenverarbeitung und -verwaltung** zuständig. Es empfängt Daten vom Frontend, verarbeitet diese und gibt die Ergebnisse zurück. Dadurch kann sich das Frontend ausschließlich auf die Darstellung der Daten konzentrieren.

### Architektur-Prinzip
```
Frontend (UI) → Backend (Logik) → API (externe Dienste)
     ↑                                      ↓
     └──────────── Verarbeitete Daten ──────┘
```

---

## Kernfunktionalitäten

### 1. Preset-Verwaltung

Das Backend ermöglicht das Speichern, Bearbeiten und Löschen von Presets. Jedes Preset enthält:

- **Name des Presets** – Eindeutiger Identifikator
- **Beschreibung des Presets** – Zusätzliche Informationen (optional)
- **API-Credentials** – API-Key und weitere benötigte Zugangsdaten
- **Prompt-Template** – Die Vorlage für die API-Abfrage
- **API-Typ** – z.B. OpenAI, Azure OpenAI, Anthropic

#### Datenstruktur (JSON):
```json
{
  "name": "Zusammenfassung",
  "description": "Erstellt eine kurze Zusammenfassung",
  "api_type": "chatgpt",
  "prompt": "Fasse den folgenden Text zusammen: {text}",
  "category": "Text-Verarbeitung"
}
```

### 2. API-Kommunikation

Das Backend übernimmt die gesamte Kommunikation mit externen APIs (OpenAI, Azure, Anthropic, etc.).

**Vom Frontend benötigte Informationen für eine API-Abfrage:**
- **Preset-Name** – Welches Preset soll verwendet werden?
- **Prompt/Eingabedaten** – Die eigentliche Abfrage bzw. der zu verarbeitende Text
- **Zusätzliche Parameter** (optional) – z.B. Temperatur, Max-Tokens

**Rückgabe an das Frontend:**
- **JSON-Response** mit den verarbeiteten Daten
- **Status-Informationen** (Erfolg/Fehler)
- **Metadaten** (verwendetes Modell, Token-Verbrauch, etc.)

#### Ablauf einer API-Abfrage:
```
1. Frontend sendet: {preset_name, prompt, parameter}
2. Backend lädt Preset-Konfiguration
3. Backend erstellt API-Request mit Credentials
4. Backend sendet Request an externe API
5. Backend empfängt Response
6. Backend formatiert Response als JSON
7. Backend sendet JSON an Frontend
```

---

## Debug-Modus

### Aktivierung

Der Debug-Modus wird über eine **globale Variable** am Anfang der Backend-Datei gesteuert:

```python
DEBUG_MODE = True  # Auf True setzen für Debug-Modus
```

### Funktionen im Debug-Modus

Wenn `DEBUG_MODE = True` gesetzt ist, kann das Backend **ohne Frontend** über das Terminal bedient werden.

**Verfügbare Befehle:**

| Befehl | Beschreibung |
|--------|--------------|
| `create` | Neues Preset anlegen |
| `list` | Alle Presets auflisten |
| `delete` | Preset löschen |
| `query` | API-Abfrage mit Preset durchführen |
| `help` | Hilfe-Menü anzeigen |
| `exit` | Debug-Modus beenden |

### Beispiel-Ablauf im Terminal:

```bash
$ python backend.py

=== PromptPilot Backend - Debug-Modus ===

Verfügbare Befehle: create, list, delete, query, help, exit

> create
Preset-Name: Test-Preset
Beschreibung: Ein Test-Preset
API-Typ: chatgpt
Prompt: Sage Hallo!
✓ Preset 'Test-Preset' wurde erstellt

> list
Gespeicherte Presets:
1. Test-Preset (chatgpt) - Ein Test-Preset

> query
Preset-Name: Test-Preset
Eingabe-Prompt: 
API-Antwort:
{
  "response": "Hallo! Wie kann ich Ihnen helfen?",
  "model": "gpt-3.5-turbo",
  "tokens": 12
}

> exit
Backend wird beendet.
```

---

## API-Schnittstellen

### Backend-Klasse: `APIBackend`

#### Methoden:

```python
# Preset-Verwaltung
save_preset(name, prompt, api_type, description="", category="")
load_presets()
delete_preset(preset_name)
update_preset(preset_name, **kwargs)

# Credentials-Verwaltung
save_credentials(api_key, api_url, **kwargs)
load_credentials()

# API-Kommunikation
query_api(preset_name, user_input, **params)
test_api_connection(credentials)
```

#### Verwendung im Frontend:

```python
from backend import APIBackend

# Backend-Instanz erstellen
backend = APIBackend()

# Preset speichern
backend.save_preset(
    name="Zusammenfassung",
    prompt="Fasse zusammen: {text}",
    api_type="chatgpt",
    description="Erstellt Zusammenfassungen"
)

# API-Abfrage durchführen
result = backend.query_api(
    preset_name="Zusammenfassung",
    user_input="Langer Text hier..."
)

print(result)  # JSON-Response
```

---

## Verwendungsbeispiele

### Beispiel 1: Preset erstellen und verwenden

```python
# Preset erstellen
backend.save_preset(
    name="Code-Review",
    prompt="Überprüfe den folgenden Code und gib Verbesserungsvorschläge: {code}",
    api_type="gpt-4",
    category="Entwicklung"
)

# Preset verwenden
response = backend.query_api(
    preset_name="Code-Review",
    user_input="def hello(): print('Hello')"
)
```

### Beispiel 2: Credentials speichern

```python
backend.save_credentials(
    api_key="sk-...",
    api_url="https://api.openai.com/v1",
    model="gpt-4",
    org_id="org-..."
)
```

### Beispiel 3: Alle Presets auflisten

```python
presets = backend.load_presets()
for preset in presets:
    print(f"{preset['name']} - {preset['api_type']}")
```

---

## Fehlerbehandlung

Das Backend gibt bei Fehlern strukturierte Fehlermeldungen zurück:

```json
{
  "success": false,
  "error": "API-Key ungültig",
  "error_code": "INVALID_API_KEY",
  "timestamp": "2025-10-23T10:30:00Z"
}
```

---

## Zusammenfassung

Das Backend von PromptPilot ist für folgende Hauptaufgaben zuständig:

✅ **Preset-Verwaltung** – Speichern, Laden, Bearbeiten, Löschen  
✅ **Credentials-Verwaltung** – Sichere Speicherung von API-Keys  
✅ **API-Kommunikation** – Anfragen an OpenAI, Azure, Anthropic, etc.  
✅ **Debug-Modus** – Terminal-basierte Bedienung ohne Frontend  
✅ **Datenverarbeitung** – JSON-Formatierung und Validierung  

---

**Version:** 1.0  
**Letzte Aktualisierung:** 23. Oktober 2025
