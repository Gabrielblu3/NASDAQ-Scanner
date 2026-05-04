"""Tests for the UserProfile model."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasdaq_scanner.user_profile import PROFILE_PATH, UserProfile


class TestUserProfileDefaults:
    """Test that UserProfile defaults are set correctly."""

    def test_default_budget(self):
        profile = UserProfile()
        assert profile.budget == 1000

    def test_default_risk_tolerance(self):
        profile = UserProfile()
        assert profile.risk_tolerance == "moderate"

    def test_default_experience(self):
        profile = UserProfile()
        assert profile.experience == "beginner"

    def test_default_trading_mode(self):
        profile = UserProfile()
        assert profile.trading_mode == "paper"

    def test_default_api_keys_empty(self):
        profile = UserProfile()
        assert profile.alpaca_api_key == ""
        assert profile.alpaca_secret_key == ""


class TestUserProfileIsConnected:
    """Test the is_connected property."""

    def test_not_connected_when_keys_empty(self):
        profile = UserProfile()
        assert profile.is_connected is False

    def test_not_connected_when_only_api_key(self):
        profile = UserProfile(alpaca_api_key="key123")
        assert profile.is_connected is False

    def test_not_connected_when_only_secret_key(self):
        profile = UserProfile(alpaca_secret_key="secret123")
        assert profile.is_connected is False

    def test_connected_when_both_keys_set(self):
        profile = UserProfile(alpaca_api_key="key123", alpaca_secret_key="secret123")
        assert profile.is_connected is True


class TestUserProfileModeLabel:
    """Test the mode_label property."""

    def test_browsing_when_not_connected(self):
        profile = UserProfile()
        assert profile.mode_label == "BROWSING"

    def test_paper_mode_label(self):
        profile = UserProfile(
            alpaca_api_key="key", alpaca_secret_key="secret", trading_mode="paper"
        )
        assert profile.mode_label == "PAPER"

    def test_live_mode_label(self):
        profile = UserProfile(
            alpaca_api_key="key", alpaca_secret_key="secret", trading_mode="live"
        )
        assert profile.mode_label == "LIVE"


class TestUserProfilePositionSizing:
    """Test max_position_pct and max_position_dollars."""

    def test_conservative_max_position_pct(self):
        profile = UserProfile(risk_tolerance="conservative")
        assert profile.max_position_pct == 0.15

    def test_moderate_max_position_pct(self):
        profile = UserProfile(risk_tolerance="moderate")
        assert profile.max_position_pct == 0.30

    def test_aggressive_max_position_pct(self):
        profile = UserProfile(risk_tolerance="aggressive")
        assert profile.max_position_pct == 0.50

    def test_max_position_dollars_default(self):
        # budget=1000, moderate=0.30 -> 300
        profile = UserProfile()
        assert profile.max_position_dollars == 300.0

    def test_max_position_dollars_custom_budget(self):
        profile = UserProfile(budget=5000, risk_tolerance="aggressive")
        assert profile.max_position_dollars == 2500.0


class TestUserProfileLoad:
    """Test UserProfile.load always returns None."""

    def test_load_returns_none(self):
        result = UserProfile.load()
        assert result is None


class TestUserProfileSave:
    """Test UserProfile.save writes to disk without API keys."""

    def test_save_creates_file(self, tmp_path):
        fake_profile_path = tmp_path / "data" / "user_profile.json"
        with patch("nasdaq_scanner.user_profile.PROFILE_PATH", fake_profile_path):
            profile = UserProfile(
                budget=2000,
                risk_tolerance="aggressive",
                alpaca_api_key="should_not_persist",
                alpaca_secret_key="should_not_persist",
            )
            profile.save()

            assert fake_profile_path.exists()
            data = json.loads(fake_profile_path.read_text())
            assert data["budget"] == 2000
            assert data["risk_tolerance"] == "aggressive"
            assert "alpaca_api_key" not in data
            assert "alpaca_secret_key" not in data


class TestUserProfileDelete:
    """Test UserProfile.delete removes the file."""

    def test_delete_removes_file(self, tmp_path):
        fake_profile_path = tmp_path / "data" / "user_profile.json"
        fake_profile_path.parent.mkdir(parents=True, exist_ok=True)
        fake_profile_path.write_text("{}")

        with patch("nasdaq_scanner.user_profile.PROFILE_PATH", fake_profile_path):
            UserProfile.delete()
            assert not fake_profile_path.exists()

    def test_delete_no_error_when_file_missing(self, tmp_path):
        fake_profile_path = tmp_path / "data" / "user_profile.json"
        with patch("nasdaq_scanner.user_profile.PROFILE_PATH", fake_profile_path):
            # Should not raise
            UserProfile.delete()
