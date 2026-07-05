# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environments

The project uses [uv](https://github.com/astral-sh/uv) for dependency management.

**Core environment** (trading and ML scripts):
```bash
uv venv --python 3.10
source .venv/bin/activate
uv pip install -e .
```

**Dashboard environment** (separate, lighter deps):
```bash
cd dashboard
uv venv --python 3.10
source .venv/bin/activate
uv pip install -r requirements.txt
```

Note: [TA-Lib](https://github.com/TA-Lib/ta-lib-python#dependencies) requires a system-level C library to be installed before `uv pip install -e .`.

## Running Scripts

**All scripts are run from the project root.** The `calpha` package must be installed first (`uv pip install -e .`).

```bash
# Train ML models on production data
python hhhl_ml1_train_models_prod.py -c "configs/hhhl_ml1_train_models_prod.yaml"

# Backtest trained models
python hhhl_ml1_backtest.py -c "configs/hhhl_ml1_backtest.yaml"

# Run the live portfolio (also used as cron job via run_portfolio.sh)
python run_portfolio.py -c "configs/portfolios_hhhl_ml1_200.yaml"

# Discover strategy parameters for new symbols
python run_strategy.py -c "configs/run_strategy_config.yaml"

# Initialize the SQLite database (destructive — drops and recreates all tables)
python create_db.py
```

The dashboard runs separately (activate its own venv first):
```bash
cd dashboard/
source .venv/bin/activate
python app.py
```

## Secrets

`keys.yaml` at the project root (gitignored) holds Alpaca API credentials:
```yaml
paper_key: <alpaca-paper-api-key>
paper_secret: <alpaca-paper-api-secret>
```
This file is loaded directly by `utils_strategy.py` and `utils_portfolio.py` at import time — it must exist before running any script.

## Architecture

### Core Strategy Logic (`src/calpha/strategies.py`)

Two strategies are defined:

1. **`HigherHighStrategy`** — a VectorBT `IndicatorFactory` wrapping `hh_hl_strategy_logic`. Detects consecutive higher highs/higher lows (entry) and lower highs (exit). Parameters: `window_entry`, `hh_hl_counts`, `window_exit`, `lh_counts`.

2. **`hhhl_ml1_strategy_logic`** — ML-enhanced version. Iterates all parameter combinations of HHHL, gets ML model probability for each, and selects the highest-probability exit signal above a threshold.

### Data & Indicators (`src/calpha/utils_strategy.py`)

- `data_load()` / `strategy_data_prep()` — fetches OHLCV data from yfinance (default) with Alpaca as fallback, then computes 100+ technical indicators via `pandas_ta`.
- `get_alpaca_data()` / `get_yf_data()` — raw data fetchers.
- Crypto symbols use the `BTC/USD` format for yfinance and must be mapped to `BTCUSD` for Alpaca orders (see `crypto_map` in `utils_portfolio.py`).

### Portfolio Execution (`src/calpha/utils_portfolio.py`)

Handles all live trading logic:
- `run_strategy()` — generates entry/exit signals for a symbol using its configured strategy
- `open_positions()` / `close_positions()` — places market orders via Alpaca Trading API
- `eval_position()` — checks if stop loss or take profit has been hit
- `update_portfolio_state()` / `update_strategy_state()` / `update_symbol_state()` — write performance metrics to SQLite

All trading is paper trading (`TradingClient(..., paper=True)`).

### Database (`db/calpha.db`)

SQLite database with tables: `portfolio_info`, `portfolio_state`, `whole_portfolio_state`, `strategy_state`, `symbol_state`, `positions`. Schema is in `create_db.py` and queries in `sql/queries.sql`.

### ML Training Flow

1. `hhhl_ml1_train_models_prod.py` downloads full history per symbol, generates all HHHL parameter combos, runs VectorBT backtests to label trades win/loss, trains `HistGradientBoostingClassifier` with `GridSearchCV` + `TimeSeriesSplit`, saves model to `outputs_hhhl_ml1_train_prod/<experiment_name>/<symbol>/`.
2. `hhhl_ml1_backtest.py` loads trained models from `outputs_hhhl_ml1/<experiment_name>/` and evaluates them across time-series splits.
3. `run_portfolio.py` loads models from the path specified in the portfolio YAML config (`model_folder` key per symbol).

### Portfolio Config Format

YAML files in `configs/` define portfolios:
```yaml
portfolio_name:
  portfolio_size: 10000
  min_available_cash: 100
  weights: equal          # or win_rate
  data_preference: yf     # or alpaca
  symbols:
    AAPL:
      hhhl_ml1:
        params: {window_entry: 3, hh_hl_counts: 1, window_exit: 6, lh_counts: 4}
        stoploss: 0.1
        take_profit: None
        model_folder: 'outputs_hhhl_ml1_train_prod/experiment_name'
```

### Output Directories

- `outputs_hhhl_ml1/<experiment>/` — backtest training artifacts (model + per-split metrics)
- `outputs_hhhl_ml1_train_prod/<experiment>/` — production training artifacts
- `models/` — manually placed model checkpoints for live trading
- `logs/`, `logs_backtest/`, `logs_model_train/` — per-run log files (timestamped)
- `run_data/` — per-run entry/exit signal CSVs saved by `run_portfolio.py`
