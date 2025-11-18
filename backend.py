import json
import os
import platform
import sys
from typing import Dict, List

import openai


def get_platform() -> str:
    """Return the normalized platform identifier."""
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    if "darwin" in system or "mac" in system:
        return "mac"
    return "linux"


def resource_path(filename: str) -> str:
    """Resolve resource paths for dev and PyInstaller bundle modes."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "resources", filename)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    appdata_dir = os.path.join(base_dir, "appdata")
    candidate = os.path.join(appdata_dir, filename)
    if os.path.exists(candidate):
        return candidate
    return os.path.join(base_dir, filename)


PRESETS_FILE = resource_path("presets.json")
CREDENTIALS_FILE = resource_path("credentials.json")
SETTINGS_FILE = resource_path("settings.json")


class PromptPilotBackend:
    def __init__(self):
        self.preset_file = PRESETS_FILE
        self.credentials_file = CREDENTIALS_FILE
        self.settings_file = SETTINGS_FILE
        self._init_files()
        self.client = None

    def _init_files(self):
        os.makedirs(os.path.dirname(self.preset_file) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(self.credentials_file) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(self.settings_file) or ".", exist_ok=True)
        # Initialize presets.json if not exists
        if not os.path.exists(self.preset_file):
            default_presets = [
                {
                    "name": "Translation to Spanish",
                    "prompt": "Uebersetze mir folgenden text auf spanisch: ",
                    "api_type": "chatgpt"
                }
            ]
            with open(self.preset_file, 'w') as f:
                json.dump(default_presets, f, indent=2)

        # Initialize credentials.json if not exists
        if not os.path.exists(self.credentials_file):
            with open(self.credentials_file, 'w') as f:
                json.dump([], f, indent=2)

        if not os.path.exists(self.settings_file):
            default_settings = {"theme": "dark", "show_shortcut": ""}
            with open(self.settings_file, 'w') as f:
                json.dump(default_settings, f, indent=2)

    def _init_client(self, api_type: str) -> bool:
        try:
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)

            if api_type.lower() in ["chatgpt", "gpt-4", "gpt-3.5-turbo"]:
                credential = next((c for c in credentials if c["name"] == "OpenAI"), None)
                if credential:
                    self.client = openai.OpenAI(api_key=credential["api_key"])
                    return True
            return False
        except Exception:
            return False

    @property
    def presets(self) -> List[Dict]:
        """Gibt alle Presets zurück"""
        try:
            with open(self.preset_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def save_presets(self) -> bool:
        """Speichert die Presets-Liste in die JSON-Datei"""
        try:
            with open(self.preset_file, 'w') as f:
                json.dump(self.presets, f, indent=2)
            return True
        except Exception:
            return False

    def save_preset(self, name: str, prompt: str, api_type: str) -> bool:
        """Speichert ein neues Preset"""
        try:
            presets = self.presets
            # Prüfe ob Preset bereits existiert
            if any(p["name"] == name for p in presets):
                return False

            presets.append({"name": name, "prompt": prompt, "api_type": api_type})

            with open(self.preset_file, 'w') as f:
                json.dump(presets, f, indent=2)
            return True
        except Exception:
            return False

    def save_preset_shortcut(self, index: int, shortcut: str) -> bool:
        """Speichert eine Tastenkombination für ein Preset (persistiert in presets.json).

        Rückgabe: True bei Erfolg, False bei Fehler oder ungültigem Index.
        """
        try:
            with open(self.preset_file, 'r') as f:
                presets = json.load(f)

            if 0 <= index < len(presets):
                if shortcut:
                    presets[index]["shortcut"] = shortcut
                else:
                    presets[index].pop("shortcut", None)
                with open(self.preset_file, 'w') as f:
                    json.dump(presets, f, indent=2)
                return True
            return False
        except Exception:
            return False

    def delete_preset_by_index(self, index: int) -> bool:
        """Löscht ein Preset anhand des Index"""
        try:
            presets = self.presets
            if 0 <= index < len(presets):
                presets.pop(index)
                with open(self.preset_file, 'w') as f:
                    json.dump(presets, f, indent=2)
                return True
            return False
        except Exception:
            return False

    def update_preset_by_index(self, index: int, name: str, prompt: str, api_type: str) -> bool:
        """Aktualisiert ein Preset anhand des Index"""
        try:
            presets = self.presets
            if 0 <= index < len(presets):
                presets[index] = {"name": name, "prompt": prompt, "api_type": api_type}
                with open(self.preset_file, 'w') as f:
                    json.dump(presets, f, indent=2)
                return True
            return False
        except Exception:
            return False

    def manage_preset(self, action: str, name: str, prompt: str = None, api_type: str = None) -> Dict[str, str]:
        try:
            with open(self.preset_file, 'r') as f:
                presets = json.load(f)

            if action == "post":
                if any(p["name"] == name for p in presets):
                    return {"status": "fail", "message": f"Preset '{name}' already exists"}
                presets.append({"name": name, "prompt": prompt, "api_type": api_type})

            elif action == "delete":
                presets = [p for p in presets if p["name"] != name]

            elif action == "update":
                for preset in presets:
                    if preset["name"] == name:
                        preset["prompt"] = prompt
                        preset["api_type"] = api_type
                        break
                else:
                    return {"status": "fail", "message": f"Preset '{name}' not found"}

            with open(self.preset_file, 'w') as f:
                json.dump(presets, f, indent=2)

            return {"status": "success", "message": f"Preset {action} successful"}

        except Exception as e:
            return {"status": "fail", "message": str(e)}

    def manage_credential(self, action: str, name: str, api_key: str = None) -> Dict[str, str]:
        try:
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)

            if action == "post":
                if any(c["name"] == name for c in credentials):
                    return {"status": "fail", "message": f"Credential '{name}' already exists"}
                credentials.append({"name": name, "api_key": api_key})

            elif action == "delete":
                credentials = [c for c in credentials if c["name"] != name]

            elif action == "update":
                for cred in credentials:
                    if cred["name"] == name:
                        cred["api_key"] = api_key
                        break
                else:
                    return {"status": "fail", "message": f"Credential '{name}' not found"}

            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)

            return {"status": "success", "message": f"Credential {action} successful"}

        except Exception as e:
            return {"status": "fail", "message": str(e)}

    def save_credentials(self, api_key: str, provider: str = "OpenAI") -> bool:
        """Speichert API Credentials - kompatibel mit Frontend"""
        result = self.manage_credential("post", provider, api_key)
        if result["status"] == "fail" and "already exists" in result["message"]:
            # Update statt post wenn schon vorhanden
            result = self.manage_credential("update", provider, api_key)
        return result["status"] == "success"

    def get_credentials(self) -> List[Dict]:
        """Gibt alle Credentials zurück"""
        try:
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    # Einstellungen (Theme, Show-Shortcut etc.)
    def _load_settings(self) -> Dict:
        """Lädt die Einstellungen aus settings.json"""
        try:
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings(self, settings: Dict) -> bool:
        """Speichert die Einstellungen in settings.json"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception:
            return False

    def get_setting(self, key: str, default=None):
        """Gibt einen Einstellungswert zurück"""
        s = self._load_settings()
        return s.get(key, default)

    def set_setting(self, key: str, value) -> bool:
        """Setzt und persistiert einen Einstellungswert"""
        s = self._load_settings()
        s[key] = value
        return self._save_settings(s)

    @property
    def api_credentials(self) -> Dict:
        """Gibt Credentials als Dictionary zur��ck - für Frontend-Kompatibilität"""
        creds = self.get_credentials()
        result = {}
        for cred in creds:
            result[cred["name"]] = cred["api_key"]
        return result

    def execute_preset(self, preset_name: str, user_input: str) -> Dict[str, str]:
        try:
            # Load presets
            with open(self.preset_file, 'r') as f:
                presets = json.load(f)

            # Find the requested preset
            preset = next((p for p in presets if p["name"] == preset_name), None)
            if not preset:
                return {"status": "fail", "message": f"Preset '{preset_name}' not found"}

            # Initialize the appropriate client
            if not self._init_client(preset["api_type"]):
                return {"status": "fail", "message": f"Could not initialize {preset['api_type']} client. Please check your credentials."}

            # Execute the API call based on the type
            full_prompt = f"{preset['prompt']}{user_input}"

            if preset["api_type"].lower() in ["chatgpt", "gpt-4", "gpt-3.5-turbo"]:
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "user", "content": full_prompt}
                        ]
                    )
                    return {
                        "status": "success",
                        "message": "API call successful",
                        "response": response.choices[0].message.content
                    }
                except Exception as e:
                    return {"status": "fail", "message": f"API call failed: {str(e)}"}

            return {"status": "fail", "message": f"Unsupported API type: {preset['api_type']}"}

        except Exception as e:
            return {"status": "fail", "message": str(e)}

    def test_credential(self, credential_name: str) -> Dict[str, str]:
        try:
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)

            credential = next((c for c in credentials if c["name"] == credential_name), None)
            if not credential:
                return {"status": "fail", "message": f"Credential '{credential_name}' not found"}

            # Test the API key with a simple request
            try:
                client = openai.OpenAI(api_key=credential["api_key"])
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5
                )
                return {"status": "success", "message": "Credential test successful"}
            except Exception as e:
                return {"status": "fail", "message": f"API test failed: {str(e)}"}

        except Exception as e:
            return {"status": "fail", "message": str(e)}


# Alias für Frontend-Kompatibilität
APIBackend = PromptPilotBackend

# Example usage:
if __name__ == "__main__":
    backend = PromptPilotBackend()

    # Test preset management
    print(backend.manage_preset("post", "Test Preset", "This is a test prompt", "chatgpt"))
    print(backend.manage_preset("update", "Test Preset", "Updated test prompt", "chatgpt"))
    print(backend.execute_preset("Test Preset", "Hello world"))
    print(backend.manage_preset("delete", "Test Preset"))

    # Test credential management
    print(backend.manage_credential("post", "OpenAI", "sk-test123"))
    print(backend.test_credential("OpenAI"))
    print(backend.manage_credential("delete", "OpenAI"))
