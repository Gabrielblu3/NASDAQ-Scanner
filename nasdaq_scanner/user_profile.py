"""User profile management for personalized trading experience."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path


PROFILE_PATH = Path(__file__).parent.parent / "data" / "user_profile.json"


@dataclass
class UserProfile:
    budget: int = 1000
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    experience: str = "beginner"  # beginner, intermediate, experienced
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    trading_mode: str = "paper"  # paper, live, browsing

    @property
    def is_connected(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)

    @property
    def mode_label(self) -> str:
        if not self.is_connected:
            return "BROWSING"
        return self.trading_mode.upper()

    @property
    def max_position_pct(self) -> float:
        """Max percentage of budget for a single trade based on risk tolerance."""
        return {"conservative": 0.15, "moderate": 0.30, "aggressive": 0.50}[
            self.risk_tolerance
        ]

    @property
    def max_position_dollars(self) -> float:
        return self.budget * self.max_position_pct

    def save(self):
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        # Never persist API keys to disk — they stay in session_state only
        data.pop("alpaca_api_key", None)
        data.pop("alpaca_secret_key", None)
        PROFILE_PATH.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "UserProfile | None":
        # Always return None so every visitor sees onboarding.
        # File-based persistence would be shared across all users on the server.
        return None

    @classmethod
    def delete(cls):
        if PROFILE_PATH.exists():
            PROFILE_PATH.unlink()
