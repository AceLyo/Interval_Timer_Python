import os
import json
from dataclasses import dataclass, asdict
from typing import List, Dict

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
    # Show rounds by default in minimalist mode; time/progress remain hidden
    minimalist_rounds_active: bool = True
    minimalist_time_active: bool = False
    minimalist_progressbar_active: bool = False
    presets: list = None

    def __post_init__(self):
        if self.presets is None:
            # Each preset is a dict of settings, or None if unused
            self.presets = [None, None, None]

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

    # New method to restore all configuration values to their defaults
    def reset_to_default(self):
        """Reset all configuration attributes to their default values."""
        from dataclasses import fields

        # Create a new Config instance which will contain default values
        default_config = Config()

        # Iterate through dataclass fields and copy default values
        for field in fields(Config):
            setattr(self, field.name, getattr(default_config, field.name))

        # Ensure presets list has correct length (handled in __post_init__ of default_config)
        # Save the reset configuration to file so external sessions pick up the change
        self.save_to_file()

    def update(self, **kwargs):
        """Update settings attributes and save to file."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save_to_file()
