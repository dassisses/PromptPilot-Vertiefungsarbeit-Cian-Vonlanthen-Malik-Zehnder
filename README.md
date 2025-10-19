# PromptPilot Vertiefungsarbeit Cian Vonlanthen und Malik Zehnder
In diesem Repository befindet sich unser selbst entwickeltes Tool PromptPilot. Dieses haben wir im Rahmen unserer Vertiefungsarbeit entwickelt, um einen persönlichen Use Case, den wir lösen wollten, abzudecken.


Schnittstellen im Überblick zwischen back end und frontend


Grundelgend braucht es folgende Schnittstellen:

einmal im back end eine schnittstelle mit der man promts an Openai sendet

schnittstelle für openai soll folgendes bereit stellen 

dass ganze soll so funktionieren. 

Front end fragt beim user folgende daten ab: 

im tap credentials soll er credentials hinzufügen können
pro jeweilgen Provider zum bsp openai 

anschliessend wenn er ein neues Preset erstellen will kann er dann dort zwischen denn verschiedenen models wählen 



schnittstelle für cloude usw sind geplannt aber noch nicht jetzt.

# Anleitung Installation und Nutzung

1\. Vorbereitung und Erster Start (Installation der Basis)
----------------------------------------------------------

Um das Python-Programm zu starten, brauchen wir das **Terminal** (Mac/Linux) oder die **Kommandozeile** (Windows). Hier führen Sie die Befehle aus.

### A. Den Projektordner Vorbereiten

1.  **Den Ort Finden:** Öffnen Sie den Ordner, der den gesamten Code des Prompt Pilots enthält.
    
2.  **Zum Terminal Wechseln:** Öffnen Sie das Terminal/die Kommandozeile und navigieren Sie zu diesem Ordner.
    
    *   _Tipp:_ Wenn Ihr Ordner zum Beispiel "PromptPilot" heißt, geben Sie ein: cd PromptPilot (wobei cd für "Change Directory" steht).
        

### B. Notwendige Zusatzteile Installieren (Abhängigkeiten)

Ihr Programm braucht oft kleine Helfer aus dem Internet (sogenannte Bibliotheken, wie z.B. für die Verbindung zur KI oder die grafische Oberfläche). Diese müssen einmalig installiert werden.

1.  Bashpip install -r requirements.txt
    
    *   _Erklärung:_ Dieser Befehl nutzt **pip** (den Standard-Installationshelfer für Python) und liest die Datei **requirements.txt** aus Ihrem Ordner. Dort sind alle benötigten Helfer aufgelistet, die dann automatisch heruntergeladen und installiert werden.
        

### C. Das Programm Starten

Sobald die Installation der Zusatzteile abgeschlossen ist, können Sie den Prompt Pilot starten.

1.  Bashpython main.py
    
    *   _Erklärung:_ Dieser Befehl weist Ihren Computer an, die Hauptdatei des Programms (**main.py**) mithilfe von Python auszuführen.
        
2.  **Öffnen der Oberfläche:** Jetzt sollte das Fenster des **Prompt Pilots** mit der Verwaltungsoberfläche erscheinen.
    

2\. Konfiguration der KI-Zugänge und Workflows
----------------------------------------------

Nach dem ersten Start müssen Sie die Zugangsdaten hinterlegen und Ihre Befehle festlegen.

### A. KI-Schlüssel Hinterlegen

1.  **API-Verwaltung Öffnen:** Navigieren Sie im Programmfenster zum Bereich **"API-Verwaltung"** oder **"Einstellungen"**.
    
2.  **Anbieter Auswählen:** Wählen Sie aus dem Menü Ihren gewünschten KI-Anbieter (z.B. **OpenAI** oder **Anthropic**).
    
3.  **Zugangsdaten Eingeben:** Geben Sie Ihren **persönlichen API-Schlüssel** in das Hauptfeld ein.
    
    *   _Achtung bei Azure:_ Wenn Sie **Azure OpenAI** gewählt haben, geben Sie zusätzlich die Internetadresse (**Endpunkt**) und den **Bereitstellungsnamen** ein.
        
4.  **Speichern:** Achten Sie darauf, dass die Statusanzeige grün wird, nachdem Sie den Schlüssel eingegeben haben. Klicken Sie dann auf **"Einstellungen speichern"**. Die Schlüssel werden im Hintergrund sicher abgelegt, sodass Sie sie nicht erneut eingeben müssen.
    

### B. Automatisierte Workflows Erstellen

Wechseln Sie nun in den Bereich, in dem Sie Ihre **Prompt-Vorlagen** (Workflows) definieren.

1.  **Workflow Manager:** Suchen Sie den Abschnitt **"Workflows"** oder **"Prompt-Vorlagen verwalten"**.
    
2.  **Befehl Definieren:** Erstellen Sie eine neue Vorlage und geben Sie Ihre feste Anweisung ein, die Sie oft nutzen. Zum Beispiel: Bitte fasse den folgenden Text in der Du-Form kurz zusammen:.
    
3.  **Tastenkombination Festlegen:** Weisen Sie dieser Anweisung eine einzigartige Tastenkombination zu (z.B. $\\text{Cmd} + \\text{Y}$ oder $\\text{Strg} + \\text{Alt} + \\text{S}$).
    
4.  **Aktivieren:** Speichern Sie den Workflow. Das Programm ist nun im Hintergrund aktiv und hört auf Ihre festgelegte Tastenkombination.
    

3\. Nutzung im Alltag (Der Produktivitäts-Turbo)
------------------------------------------------

Der Prompt Pilot muss **gestartet bleiben** (wie in Schritt 1.C beschrieben), damit er die Tastenkombinationen abfangen kann. Er läuft dann unauffällig im Hintergrund.

1.  **Text Markieren:** Gehen Sie zu jeder beliebigen Anwendung auf Ihrem Computer (Browser, Word-Dokument, E-Mail). **Markieren Sie den Textabschnitt**, den Sie von der KI verarbeiten lassen möchten.
    
2.  **Befehl Auslösen:** Drücken Sie die Tastenkombination, die Sie für den gewünschten Befehl gespeichert haben (z.B. $\\text{Cmd} + \\text{Y}$).
    
3.  **Die Verarbeitung:** Das Programm fängt den Befehl ab, fügt den markierten Text an Ihren gespeicherten Prompt an und schickt ihn zur KI.
    
4.  **Ergebnis Erhalten:** Nach kurzer Wartezeit erhalten Sie die Antwort der KI. Diese wird entweder automatisch in Ihre **Zwischenablage** kopiert (sodass Sie sie sofort einfügen können) oder erscheint in einer **kurzen Benachrichtigung** auf dem Bildschirm.
    

Auf diese Weise nutzen Sie die KI direkt aus jedem Programm heraus, ohne jemals die Anwendung wechseln zu müssen.