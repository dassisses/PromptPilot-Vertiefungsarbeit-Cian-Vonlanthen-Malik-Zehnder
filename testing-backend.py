import requests
import json
import os
from typing import Dict, List, Optional


class APIBackend:

# diese klasse ist das API backend in dieser Classe befinden sich alle Funktionen die für das backend benötigt  werden.


# erste funktion für das initialisieren des backend




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


