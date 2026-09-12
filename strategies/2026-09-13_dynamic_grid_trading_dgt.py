"""Strategy: Dynamic Grid-based Trading (DGT), daily-bar adaptation.

Source: Chen, Chen & Jang, "Dynamic Grid Trading Strategy: From Zero
Expectation to Market Outperformance" (arXiv:2506.11921, June 2025),
read this iteration via browser_exec (web_search DDGS backend used for
initial discovery, browser_exec used to read the full arXiv HTML text
directly). First grid-trading strategy of any kind in this repo (0 prior
knowledge_base hits for "grid trading").

Paper's core finding: a TRADITIONAL geometric grid-trading strategy (n
grid levels above/below a starting price P, buy 1/G_j of cash when price
crosses down through grid level G_j, sell 1/G_i of held coin when price
crosses up through grid level G_i, TERMINATE when price exits the grid's
upper/lower bounds) has a provably ZERO expected value under a symmetric
random-walk assumption -- proven via a finite-automaton coin-toss
argument in the paper's Section 2.2. Their proposed fix, Dynamic
Grid-based Trading (DGT), instead RESETS the grid (re-centers on the
current price, recomputing new grid levels) whenever price breaks out of
the current grid's bounds, rather than terminating: if price broke ABOVE
the upper bound, the position is closed to cash and a new grid started;
if price broke BELOW the lower bound, the position stays in the asset
(now fully invested) and a new grid is started using the accumulated
arbitrage profit as the new principal. The paper's own backtest (1-minute
BTC/ETH bars, Jan 2021-Jul 2024) found DGT outperforms both the
traditional (terminating) grid and buy-and-hold.

Daily-bar adaptation (this repo's loaders provide daily OHLCV, not
minute-level data): grid-level crossings are detected using each day's
HIGH and LOW (not just close) to approximate intraday level-touches,
since a pure close-to-close check would miss crossings inside a big
daily range. At most one full grid reset is processed per day (the paper
itself notes real crossings are far more frequent at 1-minute
granularity; this is a necessary granularity trade-off, logged
explicitly as a scope caveat).

Signal logic
------------
- `n_grids`: number of grid intervals (n+1 levels), `grid_size` (k): the
  fixed percentage step between adjacent grid levels (geometric grid,
  levels at P*(1+k)^i for i in [-(n-m), m]).
- `m_above`: number of grid levels initially placed above the starting
  price (n-m below).
- Starting capital split: m/n fraction in the asset, (n-m)/n in cash.
- Each day, using the day's high/low range, detect how many grid levels
  were crossed up (sell 1/level_index of currently held coin per level
  crossed, moving cash<-coin) or down (buy 1/level_index of currently
  held cash per level crossed, moving coin<-cash), tracking level state.
- If the day's high exceeds the top grid level: liquidate all coin to
  cash, recenter a new grid on the close price (fresh m_above/n split).
- If the day's low breaks the bottom grid level: the position is already
  fully in coin at that point (per the DGT mechanism); recenter a new
  grid on the close price using the current total portfolio value as the
  new principal.
- Position (exposure fraction, 0.0-1.0 = coin_value / total_value) and
  total-portfolio daily returns are tracked and returned.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (coin exposure
        fraction 0.0-1.0, NOT a binary {0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily portfolio
        returns, including the grid's buy-low/sell-high arbitrage P&L)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if not isinstance(df.index, pd.DatetimeIndex):
        return df
    # Loaders may return native intraday (e.g. hourly) bars; resample to
    # daily OHLC for this repo's standard daily-bar convention.
    daily = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return daily


def _build_grid(center_price: float, n_grids: int, grid_size: float, m_above: int):
    """Return sorted grid level prices (n_grids+1 levels) around center_price."""
    levels = []
    for i in range(-(n_grids - m_above), m_above + 1):
        levels.append(center_price * (1.0 + grid_size) ** i)
    return sorted(levels)


def _simulate(
    price_df: pd.DataFrame,
    n_grids: int = 10,
    grid_size: float = 0.02,
    m_above: int = 5,
    fee_rate: float = 0.0008,
) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    coin_value = 0.0
    cash_value = 0.0
    total_value = 1.0
    grid_levels = None
    current_level_idx = None

    positions = np.zeros(n)
    total_values = np.zeros(n)

    for i in range(n):
        c = close.iloc[i]
        h = high.iloc[i]
        l = low.iloc[i]

        if grid_levels is None:
            grid_levels = _build_grid(c, n_grids, grid_size, m_above)
            coin_value = total_value * (m_above / n_grids)
            cash_value = total_value * ((n_grids - m_above) / n_grids)
            current_level_idx = m_above  # index into grid_levels (0-based from bottom)

        top = grid_levels[-1]
        bottom = grid_levels[0]

        # Mark-to-market coin_value using today's close before processing crossings.
        prev_close = close.iloc[i - 1] if i > 0 else c
        coin_value *= (c / prev_close) if prev_close else 1.0

        # Detect crossings using high/low range (approximate, daily granularity).
        # Count how many grid levels were crossed upward (via high) and
        # downward (via low) relative to the current tracked level index.
        up_crossings = 0
        while current_level_idx + up_crossings + 1 < len(grid_levels) and h >= grid_levels[current_level_idx + up_crossings + 1]:
            up_crossings += 1
        down_crossings = 0
        while current_level_idx - down_crossings - 1 >= 0 and l <= grid_levels[current_level_idx - down_crossings - 1]:
            down_crossings += 1

        # Process (at most) whichever direction dominates this bar (simplification
        # for daily-granularity approximation -- can't know intrabar sequencing).
        if up_crossings > 0 and up_crossings >= down_crossings:
            for k in range(up_crossings):
                lvl_idx = current_level_idx + 1
                if lvl_idx >= len(grid_levels):
                    break
                sell_frac = 1.0 / (lvl_idx + 1)
                traded = coin_value * sell_frac
                fee = traded * fee_rate
                coin_value -= traded
                cash_value += traded - fee
                current_level_idx = lvl_idx
        elif down_crossings > 0:
            for k in range(down_crossings):
                lvl_idx = current_level_idx - 1
                if lvl_idx < 0:
                    break
                buy_frac = 1.0 / (lvl_idx + 1)
                traded = cash_value * buy_frac
                fee = traded * fee_rate
                cash_value -= traded
                coin_value += traded - fee
                current_level_idx = lvl_idx

        total_value = coin_value + cash_value

        # Grid reset on boundary breach.
        if h >= top:
            # Liquidate to cash, recenter new grid on close.
            cash_value = total_value
            coin_value = 0.0
            grid_levels = _build_grid(c, n_grids, grid_size, m_above)
            current_level_idx = m_above
            coin_value = total_value * (m_above / n_grids)
            cash_value = total_value * ((n_grids - m_above) / n_grids)
        elif l <= bottom:
            # Fully invested, recenter new grid using current value as new principal.
            coin_value = total_value
            cash_value = 0.0
            grid_levels = _build_grid(c, n_grids, grid_size, m_above)
            current_level_idx = m_above
            coin_value = total_value * (m_above / n_grids)
            cash_value = total_value * ((n_grids - m_above) / n_grids)

        positions[i] = coin_value / total_value if total_value else 0.0
        total_values[i] = total_value

    total_series = pd.Series(total_values, index=close.index)
    returns = total_series.pct_change().fillna(0.0)
    position = pd.Series(positions, index=close.index)

    return pd.DataFrame({"position": position, "returns": returns}, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    n_grids: int = 10,
    grid_size: float = 0.02,
    m_above: int = 5,
    fee_rate: float = 0.0008,
) -> pd.Series:
    return _simulate(price_df, n_grids=n_grids, grid_size=grid_size, m_above=m_above, fee_rate=fee_rate)["position"]


def generate_returns(
    price_df: pd.DataFrame,
    n_grids: int = 10,
    grid_size: float = 0.02,
    m_above: int = 5,
    fee_rate: float = 0.0008,
) -> pd.Series:
    return _simulate(price_df, n_grids=n_grids, grid_size=grid_size, m_above=m_above, fee_rate=fee_rate)["returns"]
