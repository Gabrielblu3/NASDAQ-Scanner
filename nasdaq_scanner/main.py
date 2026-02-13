#!/usr/bin/env python3
"""NASDAQ Volatility Scanner - Main entry point."""

import argparse
import logging
import sys
import time
from datetime import datetime

import schedule

from nasdaq_scanner.alerts.webhook import WebhookNotifier
from nasdaq_scanner.config.settings import NASDAQ_100, Settings, settings
from nasdaq_scanner.scanner.signal_generator import SignalGenerator
from nasdaq_scanner.scanner.stock_screener import StockScreener

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scanner.log"),
    ],
)
logger = logging.getLogger(__name__)


def run_scan(
    config: Settings = None,
    symbols: list[str] = None,
    max_signals: int = 10,
    send_alerts: bool = True,
    include_options: bool = True,
    use_yfinance_only: bool = False,
) -> list[dict]:
    """
    Run a single scan of the market.

    Args:
        config: Settings object (uses default if None)
        symbols: List of symbols to scan (uses NASDAQ-100 if None)
        max_signals: Maximum signals to generate
        send_alerts: Whether to send webhook alerts
        include_options: Whether to fetch options data
        use_yfinance_only: Use yfinance instead of Alpaca (no API key needed)

    Returns:
        List of signal dictionaries
    """
    config = config or settings
    symbols = symbols or NASDAQ_100

    logger.info("=" * 60)
    logger.info(f"Starting NASDAQ Volatility Scan at {datetime.now()}")
    logger.info(f"Scanning {len(symbols)} symbols...")
    if use_yfinance_only:
        logger.info("Using yfinance data source (no API keys required)")
    logger.info("=" * 60)

    # Validate config (skip if using yfinance only)
    if not use_yfinance_only:
        errors = config.validate()
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            if send_alerts:
                logger.warning("Continuing scan but alerts may fail")

    # Initialize components
    screener = StockScreener(config, use_yfinance_only=use_yfinance_only)
    signal_gen = SignalGenerator(config)
    notifier = WebhookNotifier(config)

    # Screen stocks
    logger.info("Screening stocks for volatility criteria...")
    screened = screener.screen_stocks(symbols, include_options_data=include_options)
    logger.info(f"Found {len(screened)} stocks passing volatility filters")

    # Log top screened stocks
    if screened:
        logger.info("Top screened stocks by volatility:")
        for stock in screened[:5]:
            atr_str = f"{stock.atr_percentile:.0f}" if stock.atr_percentile else "N/A"
            iv_str = f"{stock.iv_rank:.1f}" if stock.iv_rank else "N/A"
            rsi_str = f"{stock.rsi:.1f}" if stock.rsi else "N/A"
            logger.info(f"  {stock.symbol}: ATR%ile={atr_str}, IV Rank={iv_str}, RSI={rsi_str}")

    # Generate signals
    logger.info("Generating trading signals...")
    signals = signal_gen.generate_signals(screened, max_signals=max_signals)
    logger.info(f"Generated {len(signals)} trading signals")

    # Log signals
    for signal in signals:
        strike_str = f"${signal.suggested_strike:.2f}" if signal.suggested_strike else "N/A"
        price_str = f"${signal.current_price:.2f}" if signal.current_price else "N/A"
        logger.info(
            f"  {signal.signal_type.value} {signal.symbol}: "
            f"Strength={signal.strength.name}, Price={price_str}, Strike={strike_str}"
        )
        logger.info(f"    Rationale: {signal.rationale}")

    # Send alerts
    if send_alerts and signals:
        logger.info("Sending webhook alerts...")
        sent = notifier.send_signals(signals)
        notifier.send_summary(signals, len(symbols))
        logger.info(f"Sent {sent}/{len(signals)} signal alerts")

    logger.info("=" * 60)
    logger.info(f"Scan complete at {datetime.now()}")
    logger.info("=" * 60)

    return [s.to_dict() for s in signals]


def run_scheduled(config: Settings = None, interval_minutes: int = 60, use_yfinance_only: bool = False):
    """
    Run scanner on a schedule.

    Args:
        config: Settings object
        interval_minutes: Minutes between scans
        use_yfinance_only: Use yfinance instead of Alpaca
    """
    config = config or settings

    logger.info(f"Starting scheduled scanner (every {interval_minutes} minutes)")
    logger.info("Press Ctrl+C to stop")

    # Run immediately
    run_scan(config, use_yfinance_only=use_yfinance_only)

    # Schedule future runs
    schedule.every(interval_minutes).minutes.do(
        run_scan, config=config, use_yfinance_only=use_yfinance_only
    )

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="NASDAQ Volatility Scanner - Scan for high-volatility trading opportunities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --once                    Run a single scan
  %(prog)s --once --yfinance-only    Run without API keys (uses Yahoo Finance)
  %(prog)s --schedule 30             Run every 30 minutes
  %(prog)s --symbols AAPL,TSLA,NVDA  Scan specific symbols
  %(prog)s --no-options              Skip options data (faster)
  %(prog)s --dry-run                 Scan without sending alerts
        """,
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scan and exit",
    )
    parser.add_argument(
        "--schedule",
        type=int,
        metavar="MINUTES",
        help="Run on a schedule (minutes between scans)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of symbols to scan",
    )
    parser.add_argument(
        "--max-signals",
        type=int,
        default=10,
        help="Maximum number of signals to generate (default: 10)",
    )
    parser.add_argument(
        "--no-options",
        action="store_true",
        help="Skip fetching options data (faster but less accurate)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run scan without sending webhook alerts",
    )
    parser.add_argument(
        "--yfinance-only",
        action="store_true",
        help="Use only yfinance for data (no Alpaca API key required)",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    if args.env_file:
        from pathlib import Path
        config = Settings.load(Path(args.env_file))
    else:
        config = settings

    # Parse symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]

    # Run mode
    if args.schedule:
        run_scheduled(config, args.schedule, use_yfinance_only=args.yfinance_only)
    else:
        # Default to single scan
        signals = run_scan(
            config=config,
            symbols=symbols,
            max_signals=args.max_signals,
            send_alerts=not args.dry_run,
            include_options=not args.no_options,
            use_yfinance_only=args.yfinance_only,
        )

        # Print summary to stdout
        print(f"\n{'=' * 60}")
        print(f"SCAN RESULTS: {len(signals)} signals generated")
        print("=" * 60)

        for signal in signals:
            print(f"\n{signal['signal_type']} {signal['symbol']}")
            print(f"  Strength: {signal['strength_name']}")
            print(f"  Price: ${signal['current_price']:.2f}")
            if signal.get("suggested_strike"):
                print(f"  Strike: ${signal['suggested_strike']:.2f}")
            if signal.get("stop_loss"):
                print(f"  Stop Loss: ${signal['stop_loss']:.2f}")
            if signal.get("target_price"):
                print(f"  Target: ${signal['target_price']:.2f}")
            if signal.get("risk_reward_ratio"):
                print(f"  R/R Ratio: {signal['risk_reward_ratio']:.2f}")
            print(f"  Rationale: {signal['rationale']}")


if __name__ == "__main__":
    main()
