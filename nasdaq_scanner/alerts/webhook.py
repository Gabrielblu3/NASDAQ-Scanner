"""Discord and Slack webhook notifications."""

import json
import logging
from datetime import datetime
from typing import Optional

import requests

from nasdaq_scanner.config.settings import Settings, settings
from nasdaq_scanner.scanner.signal_generator import SignalType, TradingSignal

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """Send trading signals via Discord and Slack webhooks."""

    # Signal type colors for embeds
    COLORS = {
        SignalType.PUT_OPPORTUNITY: 0xFF4444,  # Red
        SignalType.CALL_OPPORTUNITY: 0x44FF44,  # Green
        SignalType.HEDGE_SIGNAL: 0xFFAA00,  # Orange
        SignalType.VOLATILITY_PLAY: 0x4444FF,  # Blue
    }

    # Signal type emojis
    EMOJIS = {
        SignalType.PUT_OPPORTUNITY: "📉",
        SignalType.CALL_OPPORTUNITY: "📈",
        SignalType.HEDGE_SIGNAL: "🛡️",
        SignalType.VOLATILITY_PLAY: "⚡",
    }

    def __init__(self, config: Optional[Settings] = None):
        """Initialize notifier with webhook URLs."""
        self.config = config or settings
        self.discord_url = self.config.discord_webhook_url
        self.slack_url = self.config.slack_webhook_url

    def send_signal(self, signal: TradingSignal) -> bool:
        """
        Send a trading signal to configured webhooks.

        Args:
            signal: TradingSignal to send

        Returns:
            True if at least one webhook succeeded
        """
        success = False

        if self.discord_url:
            if self._send_discord(signal):
                success = True

        if self.slack_url:
            if self._send_slack(signal):
                success = True

        return success

    def send_signals(self, signals: list[TradingSignal]) -> int:
        """
        Send multiple signals.

        Args:
            signals: List of signals to send

        Returns:
            Number of successfully sent signals
        """
        sent = 0
        for signal in signals:
            if self.send_signal(signal):
                sent += 1
        return sent

    def send_summary(self, signals: list[TradingSignal], total_scanned: int) -> bool:
        """
        Send a summary of the scan results.

        Args:
            signals: List of generated signals
            total_scanned: Total number of stocks scanned

        Returns:
            True if at least one webhook succeeded
        """
        success = False

        if self.discord_url:
            if self._send_discord_summary(signals, total_scanned):
                success = True

        if self.slack_url:
            if self._send_slack_summary(signals, total_scanned):
                success = True

        return success

    def _send_discord(self, signal: TradingSignal) -> bool:
        """Send signal to Discord webhook."""
        emoji = self.EMOJIS.get(signal.signal_type, "📊")
        color = self.COLORS.get(signal.signal_type, 0x808080)

        # Build fields
        fields = [
            {
                "name": "Signal Type",
                "value": f"{emoji} {signal.signal_type.value}",
                "inline": True,
            },
            {
                "name": "Strength",
                "value": f"{'⭐' * signal.strength.value} ({signal.strength.name})",
                "inline": True,
            },
            {
                "name": "Current Price",
                "value": f"${signal.current_price:.2f}",
                "inline": True,
            },
        ]

        if signal.suggested_strike:
            fields.append({
                "name": "Suggested Strike",
                "value": f"${signal.suggested_strike:.2f}",
                "inline": True,
            })

        if signal.stop_loss:
            fields.append({
                "name": "Stop Loss",
                "value": f"${signal.stop_loss:.2f}",
                "inline": True,
            })

        if signal.target_price:
            fields.append({
                "name": "Target",
                "value": f"${signal.target_price:.2f}",
                "inline": True,
            })

        if signal.risk_reward_ratio:
            fields.append({
                "name": "Risk/Reward",
                "value": f"{signal.risk_reward_ratio:.2f}",
                "inline": True,
            })

        # Key metrics
        metrics_text = "\n".join(
            f"**{k.replace('_', ' ').title()}**: {v}"
            for k, v in signal.key_metrics.items()
            if v is not None
        )

        fields.append({
            "name": "Key Metrics",
            "value": metrics_text or "N/A",
            "inline": False,
        })

        fields.append({
            "name": "Rationale",
            "value": signal.rationale,
            "inline": False,
        })

        # Options suggestion
        fields.append({
            "name": "Options Suggestion",
            "value": f"Expiry: ~{signal.suggested_expiry_days} days | Delta: {signal.suggested_delta}",
            "inline": False,
        })

        payload = {
            "embeds": [
                {
                    "title": f"🚨 {signal.symbol} - Trading Signal",
                    "color": color,
                    "fields": fields,
                    "footer": {
                        "text": "NASDAQ Volatility Scanner | Not Financial Advice"
                    },
                    "timestamp": signal.timestamp.isoformat(),
                }
            ]
        }

        return self._post_webhook(self.discord_url, payload)

    def _send_slack(self, signal: TradingSignal) -> bool:
        """Send signal to Slack webhook."""
        emoji = self.EMOJIS.get(signal.signal_type, "📊")

        # Build blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {signal.symbol} - Trading Signal",
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Signal Type:*\n{emoji} {signal.signal_type.value}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Strength:*\n{'⭐' * signal.strength.value} ({signal.strength.name})"
                    },
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Price:*\n${signal.current_price:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Suggested Strike:*\n${signal.suggested_strike:.2f}" if signal.suggested_strike else "*Strike:*\nN/A"
                    },
                ]
            },
        ]

        if signal.stop_loss or signal.target_price:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Stop Loss:*\n${signal.stop_loss:.2f}" if signal.stop_loss else "*Stop:*\nN/A"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Target:*\n${signal.target_price:.2f}" if signal.target_price else "*Target:*\nN/A"
                    },
                ]
            })

        # Metrics
        metrics_text = " | ".join(
            f"{k.replace('_', ' ').title()}: {v}"
            for k, v in signal.key_metrics.items()
            if v is not None
        )

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key Metrics:* {metrics_text}"
            }
        })

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Rationale:* {signal.rationale}"
            }
        })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Options: ~{signal.suggested_expiry_days} day expiry | Delta {signal.suggested_delta} | _Not financial advice_"
                }
            ]
        })

        blocks.append({"type": "divider"})

        payload = {"blocks": blocks}
        return self._post_webhook(self.slack_url, payload)

    def _send_discord_summary(self, signals: list[TradingSignal], total_scanned: int) -> bool:
        """Send summary to Discord."""
        signal_counts = {}
        for s in signals:
            signal_counts[s.signal_type.value] = signal_counts.get(s.signal_type.value, 0) + 1

        summary_text = "\n".join(
            f"• {self.EMOJIS.get(SignalType(k), '📊')} {k}: {v}"
            for k, v in signal_counts.items()
        ) or "No signals generated"

        top_signals = "\n".join(
            f"• **{s.symbol}** ({s.signal_type.value}) - Strength: {'⭐' * s.strength.value}"
            for s in signals[:5]
        ) or "None"

        payload = {
            "embeds": [
                {
                    "title": "📊 NASDAQ Scan Complete",
                    "color": 0x4444FF,
                    "fields": [
                        {
                            "name": "Stocks Scanned",
                            "value": str(total_scanned),
                            "inline": True,
                        },
                        {
                            "name": "Signals Generated",
                            "value": str(len(signals)),
                            "inline": True,
                        },
                        {
                            "name": "Signal Breakdown",
                            "value": summary_text,
                            "inline": False,
                        },
                        {
                            "name": "Top Signals",
                            "value": top_signals,
                            "inline": False,
                        },
                    ],
                    "footer": {
                        "text": "NASDAQ Volatility Scanner"
                    },
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }

        return self._post_webhook(self.discord_url, payload)

    def _send_slack_summary(self, signals: list[TradingSignal], total_scanned: int) -> bool:
        """Send summary to Slack."""
        signal_counts = {}
        for s in signals:
            signal_counts[s.signal_type.value] = signal_counts.get(s.signal_type.value, 0) + 1

        summary_text = " | ".join(
            f"{self.EMOJIS.get(SignalType(k), '📊')} {k}: {v}"
            for k, v in signal_counts.items()
        ) or "No signals generated"

        top_signals = "\n".join(
            f"• *{s.symbol}* ({s.signal_type.value}) - {'⭐' * s.strength.value}"
            for s in signals[:5]
        ) or "None"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 NASDAQ Scan Complete",
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Stocks Scanned:*\n{total_scanned}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Signals Generated:*\n{len(signals)}"
                    },
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Breakdown:* {summary_text}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top Signals:*\n{top_signals}"
                }
            },
        ]

        payload = {"blocks": blocks}
        return self._post_webhook(self.slack_url, payload)

    def _post_webhook(self, url: str, payload: dict) -> bool:
        """Post payload to webhook URL."""
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Webhook sent successfully to {url[:50]}...")
            return True
        except requests.RequestException as e:
            logger.error(f"Webhook failed: {e}")
            return False
