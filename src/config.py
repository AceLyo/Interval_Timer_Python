import os
import json
from dataclasses import dataclass, asdict

SETTINGS_FILE = "settings.json"

@dataclass
class Config:
    # Default Values
    workout_duration: int = 60
    rest_duration: int = 45
    lead_up_duration: int = 5
    rounds: int = 10
    minimalist_mode_size: int = 120
    always_on_top: bool = False
    minimize_after_complete: bool = False
    minimalist_mode_active: bool = False
    minimalist_rounds_active: bool = False
    minimalist_time_active: bool = False
    minimalist_progressbar_active: bool = False

    @staticmethod
    def load_from_file(filename: str = SETTINGS_FILE) -> "Config":
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                return Config(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                default = Config()
                default.save_to_file(filename)
                return default
        else:
            default = Config()
            default.save_to_file(filename)
            return default

    def save_to_file(self, filename: str = SETTINGS_FILE):
        try:
            with open(filename, "w") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            print("Error saving settings:", e)

    def update(self, **kwargs):
        """Update settings attributes and save to file."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save_to_file()
