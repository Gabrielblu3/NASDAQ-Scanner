#!/bin/bash
# NASDAQ Scanner Dashboard Launcher
cd "$(dirname "$0")"
echo "============================================"
echo "   NASDAQ Volatility Scanner Dashboard"
echo "============================================"
echo ""
echo "Starting server..."
echo "Opening in your browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
python3 -m streamlit run nasdaq_scanner/dashboard.py --server.headless true
