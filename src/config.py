import os
import json
from dataclasses import dataclass, asdict

SETTINGS_FILE = "settings.json"

@dataclass
class Settings:
    workout_duration: int = 60
    rest_duration: int = 45
    lead_up_duration: int = 5
    rounds: int = 10
    minimalist_mode_size: int = 80
    always_on_top: bool = False
    minimize_after_complete: bool = False

    @staticmethod
    def load_from_file(filename: str = SETTINGS_FILE) -> "Settings":
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                return Settings(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                default = Settings()
                default.save_to_file(filename)
                return default
        else:
            default = Settings()
            default.save_to_file(filename)
            return default

    def save_to_file(self, filename: str = SETTINGS_FILE):
        try:
            with open(filename, "w") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            print("Error saving settings:", e)
