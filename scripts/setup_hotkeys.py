"""Utility script to create a double-clickable launcher on macOS.

The generated .command file launches the frontend outside of IDEs so that
`pynput` global hotkeys keep working.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from textwrap import dedent

MAIN_FILE = "frontend.py"


def main() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    script_path = project_dir / "run_promptpilot.command"

    python_executable = Path(sys.executable)

    script_content = dedent(
        f"""
        #!/bin/bash
        cd "{project_dir}"
        unset PYCHARM_HOSTED
        "{python_executable}" "{MAIN_FILE}"
        read -p "Drücke Enter, um dieses Fenster zu schließen..."
        """
    ).strip() + "\n"

    script_path.write_text(script_content, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    print("✅ Setup fertig.")
    print(f"Starte PromptPilot künftig mit: {script_path}")
    print("Dann sollten die globalen Hotkeys funktionieren (macOS-Berechtigungen nötig).")


if __name__ == "__main__":
    main()
