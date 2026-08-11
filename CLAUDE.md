# NASDAQ Scanner

Python/Streamlit volatility scanner for NASDAQ-listed equities + native macOS menubar app (SwiftUI). Part of Kirby's trading stack alongside Mollusk and polymarket_scalper.

**Repo:** github.com/Gabrielblu3/NASDAQ-Scanner
**CI/CD:** GitHub Actions

## Documentation (read first)

- `README.md` — top-level overview
- `SETUP.md` — installation + run instructions
- `NASDAQ_Scanner_Guide.md` — usage guide
- `docs/` — additional reference

## Run Commands

- `run_dashboard.command` — launches Streamlit dashboard
- `run_scan.command` — runs a one-shot scan
- `render.yaml` — Render.com deploy config (if used)
- `requirements.txt` — Python deps (use `uv pip install -r requirements.txt` in a project venv)

## Architecture

- `nasdaq_scanner/` — core Python scanner module
- `data/` — output / cached data
- Native macOS menubar app (SwiftUI) — separate component, monitors scanner output

## Python Environment

Use `uv` for all Python work (no `pip` / `venv` directly):
```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

## Related Projects

- **TradingCompanion** (`~/Cursor Projects/TradingCompanion/`) — unified SwiftUI app that consumes NASDAQ Scanner output
- **Mollusk** (`~/Cursor Projects/mollusk/`) — broader AI-native trading firm; NASDAQ Scanner feeds it volatility signals
- **polymarket_scalper** — sibling bot, different market

## Important

- Code repo is github.com/Gabrielblu3/NASDAQ-Scanner — push changes via `gh` CLI (auth: `gh auth login` if not authenticated)
- CI/CD via GitHub Actions; check `.github/workflows/` before deploying changes
- Streamlit dashboard runs locally — for sharing, use the menubar app or deploy via render.yaml
- Don't introduce paid data feeds without explicit user approval (free tier discipline)
