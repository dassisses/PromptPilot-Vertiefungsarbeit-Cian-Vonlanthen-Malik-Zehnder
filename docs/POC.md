# Proof of Concept

Dieses Dokument zeigt, wie du den End-to-End-Flow von PromptPilot mit minimalem Setup verifizieren kannst. Es baut auf dem Konzept in `docs/Konzept.md` auf.

## Ziel
- UI startet und lädt ein Preset
- OpenAI-API-Key wird akzeptiert
- Ein Prompt wird ausgeführt und das Ergebnis landet in der Zwischenablage

## Vorbereitung
1. `./scripts/install.sh` ausführen (legt `.venv` an und installiert Abhängigkeiten).
2. OpenAI API-Key bereithalten.

## Ablauf
1. Anwendung starten:
   ```bash
   ./scripts/start.sh
   ```
2. In der App auf **API Einstellungen** wechseln (`Ctrl+2`).
3. Deinen OpenAI-Key eintragen und auf **Verbindung testen** klicken – die Statusmeldung sollte "✓ Verbindung erfolgreich" anzeigen.
4. Zum Tab **Presets** wechseln (`Ctrl+1`). Das Standard-Preset "Translation to Spanish" ist bereits angelegt.
5. In einem beliebigen Texteditor einen Satz markieren und kopieren.
6. Im PromptPilot das Preset ausführen (Button klicken oder Shortcut vergeben) und auf das Ergebnis warten.
7. Füge den Text ein (`Ctrl+V`) – er sollte ins Spanische übersetzt worden sein.

## Erwartetes Ergebnis
- Die Anwendung bleibt responsiv, das Preset wird ohne Fehler ausgeführt.
- Die Zwischenablage enthält die übersetzte Ausgabe.
- In `presets.json` bleibt das Standard-Preset erhalten und kann bei Bedarf angepasst werden.

## Nächste Schritte
- Weitere Presets anlegen (z. B. Zusammenfassung oder Code-Kommentierung).
- Zusätzliche Provider in den Einstellungen hinterlegen und testen.
- Das Bundle mit `./scripts/build_app.sh` erstellen, um den PoC als standalone App zu teilen.
