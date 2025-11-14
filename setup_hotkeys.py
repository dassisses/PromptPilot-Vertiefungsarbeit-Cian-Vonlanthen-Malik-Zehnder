import os
import stat
import sys
from textwrap import dedent

# Name der Hauptdatei mit der main()-Funktion und dem Qt-Start.
# Falls deine Hauptdatei anders heißt als 'main.py', setze diesen Namen entsprechend.
MAIN_FILE = "frontend.py"

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Wir erzeugen ein .command-Skript für macOS, das die App außerhalb von PyCharm startet
    script_path = os.path.join(project_dir, "run_promptpilot.command")

    # Pfad zum aktuellen Python-Interpreter
    python_executable = sys.executable

    script_content = dedent(f"""\
        #!/bin/bash
        cd "{project_dir}"

        # Falls PYCHARM_HOSTED gesetzt ist, löschen,
        # damit in der App PYNPUT_AVAILABLE = True bleibt und pynput verwendet wird
        unset PYCHARM_HOSTED

        "{python_executable}" "{MAIN_FILE}"
        read -p "Drücke Enter, um dieses Fenster zu schließen..."
    """)

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    # Ausführbar machen
    st = os.stat(script_path)
    os.chmod(script_path, st.st_mode | stat.S_IEXEC)

    print("✅ Setup fertig.")
    print(f"Starte deine App künftig mit: {script_path}")
    print("Dann sollten die globalen Hotkeys mit pynput funktionieren (sofern macOS-Berechtigungen gesetzt sind).")


if __name__ == "__main__":
    main()
