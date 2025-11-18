"""Platform aware global hotkey manager."""
from __future__ import annotations

from typing import Callable, Dict, Optional

try:
    from pynput import keyboard
except Exception:  # pragma: no cover - pynput may be unavailable in some envs
    keyboard = None  # type: ignore

from backend import get_platform


class GlobalHotkeyManager:
    """Simple wrapper around pynput.GlobalHotKeys that only activates on Windows."""

    def __init__(self, callback: Callable[[str], None]):
        self._platform = get_platform()
        self._callback = callback
        self._listener: Optional["keyboard.GlobalHotKeys"] = None
        self._shortcut_map: Dict[str, str] = {}

    def update_shortcuts(self, shortcut_to_preset: Dict[str, str]) -> None:
        """Replace the currently registered shortcuts."""
        self._shortcut_map = {
            shortcut: preset
            for shortcut, preset in shortcut_to_preset.items()
            if shortcut and preset
        }
        self._restart_listener()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    # ------------------------------------------------------------------
    # Internal helpers
    def _restart_listener(self) -> None:
        if self._platform != "windows" or keyboard is None:
            self.stop()
            return

        if self._listener:
            self._listener.stop()
            self._listener = None

        if not self._shortcut_map:
            return

        hotkey_actions = {}
        for shortcut, preset in self._shortcut_map.items():
            combo = self._to_pynput_format(shortcut)
            if not combo:
                continue
            hotkey_actions[combo] = self._build_callback(preset)

        if not hotkey_actions:
            return

        self._listener = keyboard.GlobalHotKeys(hotkey_actions)
        self._listener.start()

    def _build_callback(self, preset: str) -> Callable[[], None]:
        def _callback() -> None:
            self._callback(preset)

        return _callback

    @staticmethod
    def _to_pynput_format(shortcut: str) -> Optional[str]:
        parts = [p.strip() for p in shortcut.replace("-", "+").split("+") if p.strip()]
        if not parts:
            return None
        modifiers = [p for p in parts[:-1]]
        key = parts[-1]
        if not modifiers:
            return None

        mapped_modifiers = []
        for mod in modifiers:
            normalized = mod.lower()
            if normalized in {"ctrl", "control"}:
                mapped_modifiers.append("<ctrl>")
            elif normalized in {"alt", "option"}:
                mapped_modifiers.append("<alt>")
            elif normalized == "shift":
                mapped_modifiers.append("<shift>")
            elif normalized in {"win", "meta", "cmd", "command"}:
                mapped_modifiers.append("<cmd>")
            else:
                return None

        key_token = key.lower()
        if len(key_token) == 1:
            combo_key = key_token
        else:
            combo_key = f"<{key_token}>"

        return "+".join(mapped_modifiers + [combo_key])
