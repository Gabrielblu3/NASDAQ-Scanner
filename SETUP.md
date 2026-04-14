# NASDAQ Volatility Scanner — Setup Guide

## Prerequisites
- Python 3.10+
- Free Alpaca account (paper trading): https://alpaca.markets

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/Gabrielblu3/NASDAQ-Scanner.git
cd NASDAQ-Scanner
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up your API keys
Create a `.env` file in the project root:
```
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

To get your keys:
1. Sign up at https://alpaca.markets
2. Go to Paper Trading → API Keys
3. Generate a new key pair
4. Paste them into your `.env` file

### 4. Run the dashboard
```bash
python3 -m streamlit run nasdaq_scanner/dashboard.py
```

Opens at http://localhost:8501 in your browser.

### 5. (Optional) Use with Claude Code
If you want AI assistance while working on this project:
```bash
npm install -g @anthropic-ai/claude-code
cd NASDAQ-Scanner
claude
```

## Troubleshooting
- **ModuleNotFoundError**: Make sure you ran `pip install -r requirements.txt`
- **API errors**: Double-check your `.env` keys are correct and the Alpaca account is active
- **Port in use**: Streamlit will auto-increment to 8502, 8503, etc.
