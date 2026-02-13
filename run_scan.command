#!/bin/bash
# NASDAQ Scanner - Quick Scan
cd "$(dirname "$0")"
echo "============================================"
echo "   NASDAQ Volatility Scanner"
echo "============================================"
echo ""
python3 -m nasdaq_scanner.main --once --dry-run --no-options --symbols AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META,AMD,NFLX,INTC,CRM,PYPL
echo ""
echo "Scan complete! Press Enter to close."
read
