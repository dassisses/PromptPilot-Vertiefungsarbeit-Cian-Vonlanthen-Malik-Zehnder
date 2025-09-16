import json
import os

class APIBackend:
    def __init__(self, config_file="config.json", presets_file="presets.json"):
        self.config_file = config_file
        self.presets_file = presets_file
        self.api_credentials = self.load_credentials()
        self.presets = self.load_presets()

    def load_credentials(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {"api_key": "", "api_url": ""}
        return {"api_key": "", "api_url": ""}

    def save_credentials(self, api_key, api_url):
        credentials = {
            "api_key": api_key,
            "api_url": api_url
        }
        with open(self.config_file, 'w') as f:
            json.dump(credentials, f)
        self.api_credentials = credentials
        return True

    def load_presets(self):
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_preset(self, name, prompt, api_type="chatgpt"):
        preset = {
            "name": name,
            "prompt": prompt,
            "api_type": api_type
        }
        self.presets.append(preset)
        with open(self.presets_file, 'w') as f:
            json.dump(self.presets, f)
        return True

