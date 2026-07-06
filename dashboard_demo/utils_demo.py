import sqlite3
import numpy as np
import pandas as pd
import yfinance as yf

crypto_map = {'BTCUSD': 'BTC/USD'}

DB_PATH = '../db/calpha.db'


def get_yf_data(symbols, start, end, attempts=10):
    dfs = []
    for symbol in symbols:
        if symbol in crypto_map.keys():
            symbol = crypto_map[symbol].replace('/', '-')
        for attempt in range(1, attempts + 1):
            try:
                df = yf.download(symbol, start=start, end=end, timeout=100)
                break
            except:
                pass

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.columns = df.columns.str.lower()
        df['symbol'] = symbol
        df.index.name = 'timestamp'
        dfs.append(df)
    df_whole = pd.concat(dfs, axis=0)
    df_whole.reset_index(inplace=True)

    return df_whole


def get_trades(symbols):
    """Synthetic stand-in for utils.get_trades().

    The real version pulls closed order fills from the Alpaca paper account,
    which no longer exists. Individual fills were never persisted to the
    database (only aggregates in symbol_state), so history can't be recovered.
    This generates per-trade returns consistent with each symbol's real
    closed_trades_cnt / win_rate from symbol_state, for demo purposes only.
    """
    con = sqlite3.connect(DB_PATH)
    df_latest = pd.read_sql(
        """select symbol, closed_trades_cnt, win_rate
           from symbol_state
           where date = (select max(date) from symbol_state)""",
        con
    )
    con.close()

    trades = []
    for symbol in symbols:
        row = df_latest.loc[df_latest['symbol'] == symbol]
        if row.empty:
            continue

        cnt = int(row['closed_trades_cnt'].iloc[0] or 0)
        if cnt < 2:
            continue

        win_rate = row['win_rate'].iloc[0]
        win_rate = 0.5 if pd.isna(win_rate) else win_rate

        rng = np.random.default_rng(abs(hash(symbol)) % (2**32))
        n_wins = round(cnt * win_rate)
        n_losses = cnt - n_wins

        wins = rng.gamma(shape=2.0, scale=0.035, size=n_wins)
        losses = -rng.gamma(shape=2.0, scale=0.025, size=n_losses)
        returns = np.concatenate([wins, losses])
        rng.shuffle(returns)

        trade_size = 100.0  # typical cost basis per position, from symbol_state history
        pl = returns * trade_size

        trades.append(pd.DataFrame({'symbol': symbol, 'return': returns, 'pl': pl}))

    if not trades:
        return pd.DataFrame(columns=['symbol', 'return', 'pl'])

    return pd.concat(trades, ignore_index=True)
