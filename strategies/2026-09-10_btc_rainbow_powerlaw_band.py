"""Strategy: Bitcoin Rainbow Chart power-law regression band mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-018):
Per BlockchainCenter's Bitcoin Rainbow Chart
(https://www.blockchaincenter.net/en/bitcoin-rainbow-chart/): a power-law
regression fits BTC's entire price history (2012-present, disclosed 94-97%
R^2 fit strength) with the formula:

    price = 10^(5.6715 * log10(days) - 16.6773)

where `days` = days since the Genesis block (2009-01-03). The site colors
deviation from this fitted center into bands ("Fire Sale" far below,
"Maximum Bubble Territory" far above); its own stated interpretation is
that far-below-center readings ("Basically a Fire Sale"/"BUY!") are
attractive entries and far-above-center readings ("Sell. Seriously,
SELL!") are exits. Operationalized here as a symmetric log-deviation band:
long entry when log10(close) sits below the fitted center by at least
`entry_deviation` (in log10 units, i.e. price is a specific multiple below
the power-law center); exit when the deviation reverts back above
`exit_deviation` (recovering toward/above the fitted center) or a
max_hold_days time-stop.

This is a single-asset, multi-YEAR macro-cycle model, not a technical
oscillator on rolling price data -- distinct from every other regime/band
strategy already tested in this repo (all of which use rolling
statistics, e.g. Bollinger/Keltner/VWAP bands, rather than a single
fixed-since-genesis power-law curve fit to the ENTIRE historical series).
First Bitcoin-specific power-law valuation model in this repo. BTC-only by
construction (the formula's origin is calendar days since the Bitcoin
Genesis block) -- not meaningfully applicable to equities or even ETH.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

GENESIS_DATE = pd.Timestamp("2009-01-03", tz=None)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    idx = df.index
    if getattr(idx, "tz", None) is not None:
        df.index = idx.tz_localize(None)
    return df


def _fitted_log10_price(days_since_genesis: np.ndarray, a: float = 5.6715, b: float = -16.6773) -> np.ndarray:
    # log10(price) = a * log10(days) + b
    days_since_genesis = np.clip(days_since_genesis, 1, None)
    return a * np.log10(days_since_genesis) + b


def generate_signals(
    price_df: pd.DataFrame,
    entry_deviation: float = 0.5,
    exit_deviation: float = 0.1,
    max_hold_days: int = 365,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    days_since_genesis = (df.index - GENESIS_DATE).days.values.astype(float)
    fitted_log10 = _fitted_log10_price(days_since_genesis)
    log10_close = np.log10(close.values.clip(min=1e-9))
    deviation = log10_close - fitted_log10  # negative = below fitted center (undervalued)

    deviation_s = pd.Series(deviation, index=df.index)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    idx_list = df.index.tolist()

    for i in range(len(df)):
        ts = idx_list[i]
        if not in_pos:
            if deviation_s.iloc[i] <= -entry_deviation:
                in_pos = True
                entry_idx = i
        else:
            days_held = i - entry_idx
            reverted = deviation_s.iloc[i] >= exit_deviation
            if reverted or days_held >= max_hold_days:
                in_pos = False
            else:
                position.loc[ts] = 1

        if in_pos and i >= entry_idx:
            position.loc[ts] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(price_df, **params)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
