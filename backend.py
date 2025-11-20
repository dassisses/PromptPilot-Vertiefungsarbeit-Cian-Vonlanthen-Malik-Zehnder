import json
import os
import platform
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

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


PROVIDER_REGISTRY: Dict[str, Dict[str, object]] = {
    "OpenAI": {
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "default_model": "gpt-3.5-turbo",
        "type": "openai",
    },
    "Anthropic": {
        "models": [
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ],
        "default_model": "claude-3-5-sonnet-20240620",
        "type": "anthropic",
    },
    "Google": {
        "models": ["gemini-1.5-pro", "gemini-1.5-flash"],
        "default_model": "gemini-1.5-flash",
        "type": "gemini",
    },
    "Cohere": {
        "models": ["command-r", "command-r-plus", "command"],
        "default_model": "command-r",
        "type": "cohere",
    },
}


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
                    "api_type": "chatgpt",
                    "provider": "OpenAI",
                    "model": PROVIDER_REGISTRY["OpenAI"]["default_model"],
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

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Return the API key for a provider if available."""

        try:
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            credential = next((c for c in credentials if c["name"].lower() == provider.lower()), None)
            return credential["api_key"] if credential else None
        except Exception:
            return None

    def _init_client(self, provider: str) -> bool:
        """Initialize SDK clients where applicable."""

        provider = provider or ""
        provider_key = provider.title()

        if provider_key == "OpenAI":
            api_key = self._get_api_key(provider_key)
            if api_key:
                try:
                    self.client = openai.OpenAI(api_key=api_key)
                    return self.client is not None
                except Exception:
                    self.client = None
                    return False
            self.client = None
            return False

        return bool(self._get_api_key(provider))

    def _infer_provider_model(self, preset: Dict) -> Tuple[str, str]:
        """Determine provider and model for a preset with backward compatibility."""

        provider = preset.get("provider")
        model = preset.get("model")
        api_type = (preset.get("api_type") or "").lower()

        if not provider:
            if api_type in {"chatgpt", "gpt-4", "gpt-3.5-turbo"}:
                provider = "OpenAI"
                if not model:
                    model = "gpt-3.5-turbo"
            elif api_type in {"claude", "claude-3", "claude-2"}:
                provider = "Anthropic"
            elif api_type in {"gemini", "palm"}:
                provider = "Google"
            elif api_type in {"cohere", "command"}:
                provider = "Cohere"

        if not model and provider in PROVIDER_REGISTRY:
            model = PROVIDER_REGISTRY[provider].get("default_model")

        return provider or "", model or ""

    def list_providers(self) -> List[str]:
        return list(PROVIDER_REGISTRY.keys())

    def list_models(self, provider: str) -> List[str]:
        return list(PROVIDER_REGISTRY.get(provider, {}).get("models", []))

    def provider_models(self) -> Dict[str, List[str]]:
        return {name: cfg.get("models", []) for name, cfg in PROVIDER_REGISTRY.items()}

    def resolve_preset_target(self, preset: Dict) -> Tuple[str, str]:
        """Return provider and model for the given preset with fallbacks."""

        return self._infer_provider_model(preset)

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

    def save_preset(self, name: str, prompt: str, api_type: str, provider: str = None, model: str = None) -> bool:
        """Speichert ein neues Preset"""
        try:
            presets = self.presets
            # Prüfe ob Preset bereits existiert
            if any(p["name"] == name for p in presets):
                return False

            provider = provider or "OpenAI"
            model = model or PROVIDER_REGISTRY.get(provider, {}).get("default_model")

            presets.append({
                "name": name,
                "prompt": prompt,
                "api_type": api_type or provider,
                "provider": provider,
                "model": model,
            })

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

    def update_preset_by_index(self, index: int, name: str, prompt: str, api_type: str, provider: str = None, model: str = None) -> bool:
        """Aktualisiert ein Preset anhand des Index"""
        try:
            presets = self.presets
            if 0 <= index < len(presets):
                provider = provider or presets[index].get("provider") or "OpenAI"
                model = model or presets[index].get("model") or PROVIDER_REGISTRY.get(provider, {}).get("default_model")
                presets[index] = {
                    "name": name,
                    "prompt": prompt,
                    "api_type": api_type or provider,
                    "provider": provider,
                    "model": model,
                }
                with open(self.preset_file, 'w') as f:
                    json.dump(presets, f, indent=2)
                return True
            return False
        except Exception:
            return False

    def manage_preset(self, action: str, name: str, prompt: str = None, api_type: str = None, provider: str = None, model: str = None) -> Dict[str, str]:
        try:
            with open(self.preset_file, 'r') as f:
                presets = json.load(f)

            if action == "post":
                if any(p["name"] == name for p in presets):
                    return {"status": "fail", "message": f"Preset '{name}' already exists"}
                provider = provider or "OpenAI"
                model = model or PROVIDER_REGISTRY.get(provider, {}).get("default_model")
                presets.append({
                    "name": name,
                    "prompt": prompt,
                    "api_type": api_type or provider,
                    "provider": provider,
                    "model": model,
                })

            elif action == "delete":
                presets = [p for p in presets if p["name"] != name]

            elif action == "update":
                for preset in presets:
                    if preset["name"] == name:
                        preset["prompt"] = prompt
                        preset["api_type"] = api_type or preset.get("api_type")
                        preset["provider"] = provider or preset.get("provider")
                        preset["model"] = model or preset.get("model")
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
        """Gibt Credentials als Dictionary zurück - für Frontend-Kompatibilität"""
        creds = self.get_credentials()
        result = {}
        for cred in creds:
            result[cred["name"]] = cred["api_key"]
        return result

    def _execute_openai(self, model: str, full_prompt: str) -> Dict[str, str]:
        if not self.client and not self._init_client("OpenAI"):
            return {"status": "fail", "message": "Could not initialize OpenAI client. Please check your credentials."}
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": full_prompt}]
            )
            return {
                "status": "success",
                "message": "API call successful",
                "response": response.choices[0].message.content
            }
        except Exception as e:
            return {"status": "fail", "message": f"API call failed: {str(e)}"}

    def _execute_http_request(self, url: str, headers: Dict[str, str], payload: Dict) -> Dict[str, str]:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"status": "success", "data": data}
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                error_body = str(e)
            return {"status": "fail", "message": error_body or str(e)}
        except Exception as e:
            return {"status": "fail", "message": str(e)}

    def _execute_anthropic(self, model: str, full_prompt: str, api_key: str) -> Dict[str, str]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        payload = {"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": full_prompt}]}
        result = self._execute_http_request(url, headers, payload)
        if result.get("status") != "success":
            return result
        data = result.get("data", {})
        content = data.get("content") or []
        text = ""
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                text = first.get("text") or ""
        return {"status": "success", "message": "API call successful", "response": text}

    def _execute_gemini(self, model: str, full_prompt: str, api_key: str) -> Dict[str, str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
        result = self._execute_http_request(url, {}, payload)
        if result.get("status") != "success":
            return result
        data = result.get("data", {})
        text = ""
        candidates = data.get("candidates") or []
        if candidates:
            first = candidates[0]
            content = first.get("content", {}) if isinstance(first, dict) else {}
            parts = content.get("parts") or []
            if parts and isinstance(parts[0], dict):
                text = parts[0].get("text") or ""
        return {"status": "success", "message": "API call successful", "response": text}

    def _execute_cohere(self, model: str, full_prompt: str, api_key: str) -> Dict[str, str]:
        url = "https://api.cohere.com/v1/chat"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
        result = self._execute_http_request(url, headers, payload)
        if result.get("status") != "success":
            return result
        data = result.get("data", {})
        text = data.get("text") or ""
        if not text:
            message = data.get("message") or {}
            if isinstance(message, dict):
                contents = message.get("content") or []
                if contents and isinstance(contents[0], dict):
                    text = contents[0].get("text") or ""
        return {"status": "success", "message": "API call successful", "response": text}

    def execute_preset(self, preset_name: str, user_input: str) -> Dict[str, str]:
        try:
            with open(self.preset_file, 'r') as f:
                presets = json.load(f)
            preset = next((p for p in presets if p["name"] == preset_name), None)
            if not preset:
                return {"status": "fail", "message": f"Preset '{preset_name}' not found"}
            provider, model = self._infer_provider_model(preset)
            if not provider:
                return {"status": "fail", "message": "Kein Anbieter für dieses Preset konfiguriert"}
            if not self._init_client(provider):
                return {"status": "fail", "message": f"Could not initialize {provider} client. Please check your credentials."}
            full_prompt = f"{preset['prompt']}{user_input}"
            api_key = self._get_api_key(provider)
            provider_type = PROVIDER_REGISTRY.get(provider, {}).get("type")
            if provider_type == "openai":
                return self._execute_openai(model or PROVIDER_REGISTRY[provider]["default_model"], full_prompt)
            if provider_type == "anthropic":
                return self._execute_anthropic(model or PROVIDER_REGISTRY[provider]["default_model"], full_prompt, api_key)
            if provider_type == "gemini":
                return self._execute_gemini(model or PROVIDER_REGISTRY[provider]["default_model"], full_prompt, api_key)
            if provider_type == "cohere":
                return self._execute_cohere(model or PROVIDER_REGISTRY[provider]["default_model"], full_prompt, api_key)
            return {"status": "fail", "message": f"Unsupported provider: {provider}"}
        except Exception as e:
            return {"status": "fail", "message": str(e)}

    def test_credential(self, credential_name: str) -> Dict[str, str]:
        try:
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            credential = next((c for c in credentials if c["name"] == credential_name), None)
            if not credential:
                return {"status": "fail", "message": f"Credential '{credential_name}' not found"}
            provider = credential.get("name")
            provider_type = PROVIDER_REGISTRY.get(provider, {}).get("type")
            if provider_type == "openai":
                try:
                    client = openai.OpenAI(api_key=credential["api_key"])
                    client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "Hi"}],
                        max_tokens=5
                    )
                    return {"status": "success", "message": "Credential test successful"}
                except Exception as e:
                    return {"status": "fail", "message": f"API test failed: {str(e)}"}
            dummy_prompt = "Hello!"
            if provider_type == "anthropic":
                return self._execute_anthropic(PROVIDER_REGISTRY[provider]["default_model"], dummy_prompt, credential["api_key"])
            if provider_type == "gemini":
                return self._execute_gemini(PROVIDER_REGISTRY[provider]["default_model"], dummy_prompt, credential["api_key"])
            if provider_type == "cohere":
                return self._execute_cohere(PROVIDER_REGISTRY[provider]["default_model"], dummy_prompt, credential["api_key"])
            return {"status": "fail", "message": "Unsupported provider for credential test"}
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
