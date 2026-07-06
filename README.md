# CAlpha

An automated algorithmic trading system that combines technical analysis with machine learning to identify and execute trading opportunities across stocks and crypto. It discovers optimal strategy parameters per symbol, trains an ML model to predict winning trades, and executes a diversified 200-symbol portfolio via the Alpaca API.

---

## How it works

The system is built around the **Higher High / Higher Low (HHHL)** strategy, enhanced with an ML layer (**HHHL ML1**):

1. **Strategy Discovery** — test all HHHL parameter combinations per symbol, backtest with VectorBT, cluster results, select top performers
2. **Model Training** — label trades win/loss, compute 100+ technical indicators as features, train a `HistGradientBoostingClassifier` with time-series cross-validation
3. **Backtesting** — evaluate trained models across historical periods, compute Sharpe ratio, drawdown, win rate
4. **Live Execution** — load trained models, generate entry/exit signals, execute market orders via Alpaca, track positions in SQLite
5. **Monitoring** — Dash web dashboard with real-time portfolio stats and trade history

```
Historical data (yfinance / Alpaca)
        │
        ▼
  run_strategy.py               ← discover best HHHL params per symbol
        │
        ▼
  hhhl_ml1_train_models_prod.py ← train ML model per symbol to get exit params with highest probability of positive return.
        │
        ▼
  hhhl_ml1_backtest.py          ← evaluate models on historical splits
        │
        ▼
  run_portfolio.py              ← live execution + order management
        │
        ▼
  dashboard/app.py              ← monitoring UI
```

---

## Dashboard

A Dash web app for monitoring the live portfolio: equity curves, returns, open/closed trades, ratios, and a parallel-coordinates symbol explorer for comparing strategy performance across the full symbol universe.

<table>
<tr>
<td width="50%"><img src="assets/screenshots/whole_portfolio_overview.png" alt="Whole portfolio overview"/><br/><sub>Whole portfolio — overview</sub></td>
<td width="50%"><img src="assets/screenshots/whole_portfolio_equity.png" alt="Whole portfolio equity"/><br/><sub>Whole portfolio — equity</sub></td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/whole_portfolio_returns.png" alt="Whole portfolio returns"/><br/><sub>Whole portfolio — returns</sub></td>
<td width="50%"><img src="assets/screenshots/subportfolios_overview.png" alt="Subportfolios overview"/><br/><sub>Subportfolios — overview</sub></td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/subportfolios_trades.png" alt="Subportfolios trades"/><br/><sub>Subportfolios — trades</sub></td>
<td width="50%"><img src="assets/screenshots/subportfolios_ratios.png" alt="Subportfolios ratios"/><br/><sub>Subportfolios — ratios</sub></td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/strategies_open_positions.png" alt="Strategy open positions"/><br/><sub>Strategies — open positions</sub></td>
<td width="50%"><img src="assets/screenshots/symbols_parallel_coordinates.png" alt="Symbols parallel coordinates"/><br/><sub>Symbols — parallel-coordinates explorer</sub></td>
</tr>
</table>

---

## Project structure

```
algot_trading/
├── src/calpha/                        # Core library
│   ├── strategies.py                  # HHHL and HHHL ML1 strategy logic
│   ├── utils_strategy.py              # Data fetching, technical indicators
│   └── utils_portfolio.py             # Order management, position tracking, DB writes
│
├── run_portfolio.py                   # Live portfolio execution (cron entry point)
├── hhhl_ml1_train_models_prod.py      # Production model training
├── hhhl_ml1_train_models_backtest.py  # Backtest model training
├── hhhl_ml1_backtest.py               # Backtest evaluation
├── run_strategy.py                    # Strategy parameter discovery
├── select_symbols.py                  # Symbol selection and correlation analysis
├── create_db.py                       # Initialize SQLite database
├── run_portfolio.sh                   # Cron wrapper for run_portfolio.py
│
├── configs/                           # YAML configs for each pipeline stage
│   ├── portfolios_hhhl_ml1_200.yaml   # Main 200-symbol portfolio definition
│   ├── hhhl_ml1_train_models_prod.yaml
│   ├── hhhl_ml1_backtest.yaml
│   ├── run_strategy_config.yaml
│   └── archive/                       # Older experiment configs
│
├── dashboard/                         # Dash monitoring UI (separate environment)
│   ├── app.py
│   ├── utils.py
│   └── requirements.txt
│
├── dashboard_demo/                    # Read-only clone of the dashboard for demo/screenshot purposes
│   ├── app_demo.py                    # Runs on its own port, no Alpaca dependency
│   └── utils_demo.py                  # Synthetic per-trade data derived from real symbol_state stats
│
├── assets/screenshots/                # Dashboard screenshots used in this README
│
├── experiment_notebooks/              # Strategy research and analysis notebooks
├── sql/queries.sql                    # Reference SQL for dashboard queries
│
├── pyproject.toml                     # Package definition (uv / pip install -e .)
└── requirements.txt                   # Direct dependencies
```

**Runtime directories** (gitignored, created on first run):
`logs/`, `logs_backtest/`, `logs_model_train/`, `outputs/`, `outputs_hhhl_ml1/`, `outputs_hhhl_ml1_train_prod/`, `models/`, `data/`, `db/`, `run_data/`

---

## Setup

### Prerequisites

Install the [TA-Lib C library](https://github.com/TA-Lib/ta-lib-python#dependencies) for your OS before installing Python packages.

### Install with uv

```bash
uv venv --python 3.10
source .venv/bin/activate
uv pip install -e .
```

### API credentials

Create `keys.yaml` in the project root (this file is gitignored):

```yaml
paper_key: <alpaca-paper-api-key>
paper_secret: <alpaca-paper-api-secret>
```

Sign up for a free [Alpaca paper trading account](https://alpaca.markets) to get keys.

### Initialize the database

```bash
mkdir -p db logs logs_backtest logs_model_train
python create_db.py
```

---

## Pipeline usage

All scripts are run from the **project root** and accept a `-c` flag pointing to a config file.

### 1. Discover strategy parameters

```bash
python run_strategy.py -c configs/run_strategy_config.yaml
```

Outputs per-symbol backtest results to `outputs/`.

### 2. Train ML models

```bash
# Production training (on latest market data)
python hhhl_ml1_train_models_prod.py -c configs/hhhl_ml1_train_models_prod.yaml

# Backtest training (with time-series cross-validation splits)
python hhhl_ml1_train_models_backtest.py -c configs/hhhl_ml1_train_models_prod.yaml
```

Models and training metadata are saved to `outputs_hhhl_ml1_train_prod/<experiment>/`.

### 3. Evaluate models

```bash
python hhhl_ml1_backtest.py -c configs/hhhl_ml1_backtest.yaml
```

### 4. Run the live portfolio

```bash
python run_portfolio.py -c configs/portfolios_hhhl_ml1_200.yaml
```

Or use the cron wrapper (update the path inside first):

```bash
bash run_portfolio.sh
```

### 5. Dashboard

The dashboard uses a separate, lighter environment:

```bash
cd dashboard
uv venv --python 3.10
source .venv/bin/activate
uv pip install -r requirements.txt
python app.py
```

---

## Portfolio config format

A single config file can define **multiple independent sub-portfolios**, each run in the same execution pass. Each sub-portfolio has its own dollar allocation, symbol set, strategy, position sizing method, and ML model path. This lets you run and compare different portfolio constructions (e.g. different symbol universes, equal vs. win-rate weighting, different position sizes) side by side under one cron job.

```yaml
# Multiple sub-portfolios in one file — each runs independently
p1:
  portfolio_size: 10000        # dollar allocation for this sub-portfolio
  min_available_cash: 100      # minimum cash to keep uninvested
  weights:
    initial: equal             # starting weight method: equal | win_rate
    running: win_rate          # rebalancing method: equal | win_rate
    running_params:
      min_trades: 10           # minimum closed trades before win_rate weighting kicks in
      min_weight: 0.02         # floor weight for symbols with insufficient trade history
      min_symbols: 5           # minimum symbols meeting min_trades before switching from initial weights
  data_preference: yf          # data source: yf | alpaca | longer_period
  model_folder:
    hhhl_ml1: 'outputs_hhhl_ml1_train_prod/experiment_name'
  ml_strategies_setup:
    hhhl_ml1:
      param_ranges:
        window_entry: [2, 9]
        hh_hl_counts: [1, 5]
        window_exit: [2, 9]
        lh_counts: [1, 5]
  symbols:
    AAPL:
      hhhl_ml1:
        params: {probability_threshold: 0.5}
        stoploss: 0.1
        take_profit: None
    BTC/USD:
      hhhl_ml1:
        params: {probability_threshold: 0.5}
        stoploss: 0.1
        take_profit: None

p2:
  portfolio_size: 5000         # separate allocation, independent of p1
  min_available_cash: 100
  weights:
    initial: equal
    running: equal
  data_preference: yf
  model_folder:
    hhhl_ml1: 'outputs_hhhl_ml1_train_prod/experiment_name'
  ml_strategies_setup:
    hhhl_ml1:
      param_ranges:
        window_entry: [2, 9]
        hh_hl_counts: [1, 5]
        window_exit: [2, 9]
        lh_counts: [1, 5]
  symbols:
    NVDA:
      hhhl_ml1:
        params: {probability_threshold: 0.5}
        stoploss: 0.1
        take_profit: None
```

---

## Tech stack

| Component | Library |
|---|---|
| Backtesting | VectorBT |
| Technical indicators | pandas-ta, TA-Lib |
| ML model | scikit-learn (`HistGradientBoostingClassifier`) |
| Trading API | Alpaca (`alpaca-py`) |
| Market data | yfinance, Alpaca historical |
| Dashboard | Dash + Plotly |
| Portfolio analytics | quantstats |
| Database | SQLite |
| Task scheduling | click + bash cron |
