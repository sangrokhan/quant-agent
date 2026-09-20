"""Strategy: Bitcoin Puell Multiple miner-stress hysteresis regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-097):
The Puell Multiple = (daily USD value of new BTC issuance) / (365-day moving
average of that daily USD value), per Glassnode/Bitbo/Samara Asset Group/
MacroMicro (all read this iteration): "Multiple = Daily BTC Issuance Value
(USD) / 365-day Moving Average of Daily Issuance Value (USD)... Neutral zone
(0.5-4.0) suggests a stable market" (Samara Asset Group). Historically low
readings (miners under revenue stress, <=enter_level, e.g. 0.5) have marked
accumulation zones near cycle bottoms; high readings (>=exit_level, e.g. 4.0)
have marked overheated/cycle-top conditions. This repo tests it as a
long/flat two-level hysteresis regime gate (same hysteresis mechanic as the
already-accepted Crypto Fear & Greed hysteresis strategy, 2026-09-20-029):
go/stay long while Puell <= enter_level (miner stress / undervaluation),
flip flat once Puell >= exit_level (miner windfall / overvaluation), and
hold the previous state in between.

Distinct from this repo's prior MVRV Z-Score attempt (2026-09-13-075,
rejected) and the repeatedly-logged "on-chain data infeasible" dead ends
(2026-09-09-042, 2026-09-10-110, 2026-09-11-036/106, 2026-09-17-011,
2026-09-18-013/071/089, 2026-09-20-015): those metrics (MVRV realized cap,
NUPL, SOPR, hash rate) genuinely require external on-chain/address-level
data this repo's OHLCV-only data/loaders.py cannot fetch. The Puell
Multiple's numerator/denominator, by contrast, depend ONLY on (a) the
publicly-known, fully deterministic Bitcoin block-subsidy halving schedule
(50 BTC/block at genesis, halving every 210,000 blocks / ~4 years, ~144
blocks/day) and (b) the BTC/USDT close price already available via
load_crypto -- no external on-chain API call needed. This makes it feasible
where the other on-chain metrics were correctly ruled infeasible.

Note: the halving-schedule-derived "daily issuance value" component is
BTC-specific and calendar-driven, not price-series-derived, so when this
strategy is grid-tested against equity symbols (SPY/QQQ) the "Puell" signal
degenerates into a pure calendar/date-based regime (same known caveat as
2026-09-04's BTC halving-cycle strategy) -- expected to show no genuine
edge on equities; the real test of this hypothesis is the crypto cells.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd

GENESIS = pd.Timestamp("2009-01-03", tz="UTC")
HALVING_DATES = [
    pd.Timestamp("2012-11-28", tz="UTC"),
    pd.Timestamp("2016-07-09", tz="UTC"),
    pd.Timestamp("2020-05-11", tz="UTC"),
    pd.Timestamp("2024-04-20", tz="UTC"),
    pd.Timestamp("2028-04-01", tz="UTC"),  # projected, outside most backtest windows
]
BLOCKS_PER_DAY = 144.0
INITIAL_REWARD = 50.0


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _block_reward(idx_utc: pd.DatetimeIndex) -> pd.Series:
    """Deterministic BTC block subsidy per date (halving every 210,000 blocks)."""
    reward = pd.Series(INITIAL_REWARD, index=idx_utc, dtype=float)
    for h in HALVING_DATES:
        reward.loc[idx_utc >= h] = reward.loc[idx_utc >= h] / 2.0
    return reward


def _puell_multiple(df: pd.DataFrame, ma_window: int) -> pd.Series:
    idx = df.index
    idx_utc = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    reward = _block_reward(idx_utc)
    daily_issuance_btc = reward * BLOCKS_PER_DAY
    daily_issuance_usd = pd.Series(daily_issuance_btc.values, index=df.index) * df["close"]
    ma = daily_issuance_usd.rolling(window=ma_window, min_periods=ma_window // 2).mean()
    puell = daily_issuance_usd / ma
    return puell


def generate_signals(
    price_df: pd.DataFrame,
    enter_level: float = 0.5,
    exit_level: float = 4.0,
    ma_window: int = 365,
) -> pd.Series:
    """Long/flat hysteresis gate on the Puell Multiple.

    Long (1) while Puell <= enter_level (miner stress / accumulation zone);
    flip flat (0) once Puell >= exit_level (miner windfall / overheated);
    hold previous state in between (hysteresis, no repeated whipsaw).
    """
    df = _prep(price_df)
    puell = _puell_multiple(df, ma_window=ma_window)

    position = pd.Series(0, index=df.index, dtype=int)
    state = 0
    for i, val in enumerate(puell.values):
        if pd.isna(val):
            position.iloc[i] = state
            continue
        if val <= enter_level:
            state = 1
        elif val >= exit_level:
            state = 0
        position.iloc[i] = state
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
