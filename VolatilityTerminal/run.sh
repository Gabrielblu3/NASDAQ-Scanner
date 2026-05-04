#!/bin/bash
# Build and run the Volatility Terminal menubar app
cd "$(dirname "$0")"
swift build -c release 2>&1 | tail -3
.build/release/VolatilityTerminal &
echo "Volatility Terminal running in menubar. PID: $!"
