import requests
import json
import os
from typing import Dict, List, Optional


class APIBackend:
    """
    Backend für PromptPilot

    Diese Klasse verwaltet:
    - API-Credentials (OpenAI, Azure, Anthropic)
    - Presets (gespeicherte Prompt-Konfigurationen)
    - API-Anfragen an verschiedene LLM-Anbieter
    """

    def __init__(self):
        """
        Initialisierung des Backends

        Lädt beim Start:
        - API-Credentials aus config.json
        - Presets aus presets.json
        """
        self.config_file = "config.json"
        self.presets_file = "presets.json"

        # Lade gespeicherte Daten
        self.credentials = self._load_credentials()
        self.presets = self._load_presets()

    # ========================================================================
    # TEIL 1: DATEI-VERWALTUNG (Laden & Speichern)
    # ========================================================================

    def _load_credentials(self) -> Dict:
        """
        Lädt API-Credentials aus config.json

        Returns:
            Dictionary mit API-Keys für verschiedene Anbieter
            Beispiel: {"openai_key": "sk-...", "anthropic_key": "..."}
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Fehler beim Laden der Credentials: {e}")
                return {}
        return {}

    def _save_credentials(self) -> bool:
        """
        Speichert API-Credentials in config.json

        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.credentials, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern der Credentials: {e}")
            return False

    def _load_presets(self) -> List[Dict]:
        """
        Lädt Presets aus presets.json

        Returns:
            Liste von Preset-Dictionaries
            Beispiel: [{"name": "Rechtschreibung", "prompt": "...", "api_type": "openai"}]
        """
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Fehler beim Laden der Presets: {e}")
                return []
        return []

    def _save_presets(self) -> bool:
        """
        Speichert Presets in presets.json

        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        try:
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern der Presets: {e}")
            return False

    # ========================================================================
    # TEIL 2: CREDENTIALS-VERWALTUNG
    # ========================================================================

    def set_credential(self, key: str, value: str) -> bool:
        """
        Speichert einen API-Key

        Args:
            key: Name des Keys (z.B. "openai_key", "anthropic_key")
            value: Der API-Key

        Returns:
            True wenn erfolgreich gespeichert
        """
        self.credentials[key] = value
        return self._save_credentials()

    def get_credential(self, key: str) -> Optional[str]:
        """
        Holt einen gespeicherten API-Key

        Args:
            key: Name des Keys

        Returns:
            Der API-Key oder None wenn nicht vorhanden
        """
        return self.credentials.get(key)

    def get_all_credentials(self) -> Dict:
        """
        Gibt alle Credentials zurück

        Returns:
            Dictionary mit allen API-Keys
        """
        return self.credentials.copy()

    def delete_credential(self, key: str) -> bool:
        """
        Löscht einen API-Key

        Args:
            key: Name des zu löschenden Keys

        Returns:
            True wenn erfolgreich gelöscht
        """
        if key in self.credentials:
            del self.credentials[key]
            return self._save_credentials()
        return False

    # ========================================================================
    # TEIL 3: PRESET-VERWALTUNG
    # ========================================================================

    def add_preset(self, name: str, prompt: str, api_type: str,
                   model: str = "gpt-4", temperature: float = 0.7) -> bool:
        """
        Fügt ein neues Preset hinzu

        Args:
            name: Name des Presets (z.B. "Rechtschreibung korrigieren")
            prompt: Der System-Prompt
            api_type: API-Anbieter ("openai", "azure", "anthropic")
            model: Modellname (Standard: "gpt-4")
            temperature: Kreativität 0.0-1.0 (Standard: 0.7)

        Returns:
            True wenn erfolgreich hinzugefügt
        """
        preset = {
            "name": name,
            "prompt": prompt,
            "api_type": api_type,
            "model": model,
            "temperature": temperature
        }

        self.presets.append(preset)
        return self._save_presets()

    def get_all_presets(self) -> List[Dict]:
        """
        Gibt alle Presets zurück

        Returns:
            Liste aller Preset-Dictionaries
        """
        return self.presets.copy()

    def get_preset_by_name(self, name: str) -> Optional[Dict]:
        """
        Sucht ein Preset nach Namen

        Args:
            name: Name des Presets

        Returns:
            Preset-Dictionary oder None wenn nicht gefunden
        """
        for preset in self.presets:
            if preset.get("name") == name:
                return preset.copy()
        return None

    def update_preset(self, old_name: str, name: str, prompt: str,
                     api_type: str, model: str = "gpt-4",
                     temperature: float = 0.7) -> bool:
        """
        Aktualisiert ein bestehendes Preset

        Args:
            old_name: Aktueller Name des Presets
            name: Neuer Name
            prompt: Neuer Prompt
            api_type: Neuer API-Typ
            model: Neues Modell
            temperature: Neue Temperature

        Returns:
            True wenn erfolgreich aktualisiert
        """
        for i, preset in enumerate(self.presets):
            if preset.get("name") == old_name:
                self.presets[i] = {
                    "name": name,
                    "prompt": prompt,
                    "api_type": api_type,
                    "model": model,
                    "temperature": temperature
                }
                return self._save_presets()
        return False

    def delete_preset(self, name: str) -> bool:
        """
        Löscht ein Preset

        Args:
            name: Name des zu löschenden Presets

        Returns:
            True wenn erfolgreich gelöscht
        """
        for i, preset in enumerate(self.presets):
            if preset.get("name") == name:
                self.presets.pop(i)
                return self._save_presets()
        return False

    # ========================================================================
    # TEIL 4: API-KOMMUNIKATION
    # ========================================================================

    def send_prompt(self, user_text: str, preset_name: str) -> Dict:
        """
        Sendet einen Prompt an die API

        Args:
            user_text: Der Text vom User (z.B. markierter Text)
            preset_name: Name des zu verwendenden Presets

        Returns:
            Dictionary mit "success" und "response" oder "error"
            Beispiel: {"success": True, "response": "Korrigierter Text..."}
        """
        # Hole das Preset
        preset = self.get_preset_by_name(preset_name)
        if not preset:
            return {"success": False, "error": "Preset nicht gefunden"}

        # Wähle die richtige API basierend auf api_type
        api_type = preset.get("api_type", "openai")

        if api_type == "openai":
            return self._send_to_openai(user_text, preset)
        elif api_type == "azure":
            return self._send_to_azure(user_text, preset)
        elif api_type == "anthropic":
            return self._send_to_anthropic(user_text, preset)
        else:
            return {"success": False, "error": f"Unbekannter API-Typ: {api_type}"}

    def _send_to_openai(self, user_text: str, preset: Dict) -> Dict:
        """
        Sendet Request an OpenAI API

        Args:
            user_text: User-Text
            preset: Preset-Konfiguration

        Returns:
            Response-Dictionary
        """
        api_key = self.get_credential("openai_key")
        if not api_key:
            return {"success": False, "error": "OpenAI API-Key nicht konfiguriert"}

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Baue die Nachricht zusammen
        system_prompt = preset.get("prompt", "")
        full_prompt = f"{system_prompt}\n\n{user_text}"

        data = {
            "model": preset.get("model", "gpt-4"),
            "messages": [
                {"role": "user", "content": full_prompt}
            ],
            "temperature": preset.get("temperature", 0.7)
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]

            return {"success": True, "response": ai_response}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"API-Fehler: {str(e)}"}
        except (KeyError, IndexError) as e:
            return {"success": False, "error": f"Antwort-Format-Fehler: {str(e)}"}

    def _send_to_azure(self, user_text: str, preset: Dict) -> Dict:
        """
        Sendet Request an Azure OpenAI API

        Args:
            user_text: User-Text
            preset: Preset-Konfiguration

        Returns:
            Response-Dictionary
        """
        api_key = self.get_credential("azure_key")
        endpoint = self.get_credential("azure_endpoint")

        if not api_key or not endpoint:
            return {"success": False, "error": "Azure API-Key oder Endpoint nicht konfiguriert"}

        # Azure verwendet einen anderen URL-Aufbau
        url = f"{endpoint}/openai/deployments/{preset.get('model', 'gpt-4')}/chat/completions?api-version=2023-05-15"

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        system_prompt = preset.get("prompt", "")
        full_prompt = f"{system_prompt}\n\n{user_text}"

        data = {
            "messages": [
                {"role": "user", "content": full_prompt}
            ],
            "temperature": preset.get("temperature", 0.7)
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]

            return {"success": True, "response": ai_response}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Azure API-Fehler: {str(e)}"}
        except (KeyError, IndexError) as e:
            return {"success": False, "error": f"Antwort-Format-Fehler: {str(e)}"}

    def _send_to_anthropic(self, user_text: str, preset: Dict) -> Dict:
        """
        Sendet Request an Anthropic (Claude) API

        Args:
            user_text: User-Text
            preset: Preset-Konfiguration

        Returns:
            Response-Dictionary
        """
        api_key = self.get_credential("anthropic_key")
        if not api_key:
            return {"success": False, "error": "Anthropic API-Key nicht konfiguriert"}

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        system_prompt = preset.get("prompt", "")

        data = {
            "model": preset.get("model", "claude-3-opus-20240229"),
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_text}
            ],
            "temperature": preset.get("temperature", 0.7)
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            ai_response = result["content"][0]["text"]

            return {"success": True, "response": ai_response}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Anthropic API-Fehler: {str(e)}"}
        except (KeyError, IndexError) as e:
            return {"success": False, "error": f"Antwort-Format-Fehler: {str(e)}"}

    # ========================================================================
    # TEIL 5: HILFSFUNKTIONEN
    # ========================================================================

    def test_preset(self, preset_name: str) -> Dict:
        """
        Testet ein Preset mit einem Dummy-Text

        Args:
            preset_name: Name des zu testenden Presets

        Returns:
            Response-Dictionary
        """
        test_text = "Dies ist ein Test-Text zum Testen des Presets."
        return self.send_prompt(test_text, preset_name)

    def validate_api_key(self, api_type: str) -> Dict:
        """
        Validiert ob ein API-Key funktioniert

        Args:
            api_type: Typ der API ("openai", "azure", "anthropic")

        Returns:
            Dictionary mit "valid" (True/False) und optional "error"
        """
        # Erstelle ein Test-Preset
        test_preset = {
            "name": "_test",
            "prompt": "Sage nur 'OK'",
            "api_type": api_type,
            "model": "gpt-4" if api_type in ["openai", "azure"] else "claude-3-opus-20240229",
            "temperature": 0.7
        }

        if api_type == "openai":
            result = self._send_to_openai("Test", test_preset)
        elif api_type == "azure":
            result = self._send_to_azure("Test", test_preset)
        elif api_type == "anthropic":
            result = self._send_to_anthropic("Test", test_preset)
        else:
            return {"valid": False, "error": "Unbekannter API-Typ"}

        return {"valid": result.get("success", False), "error": result.get("error")}

    @property
    def api_credentials(self) -> Dict:
        """
        Property für Kompatibilität mit Frontend.
        Gibt alle gespeicherten API-Credentials zurück.
        """
        return self.credentials

