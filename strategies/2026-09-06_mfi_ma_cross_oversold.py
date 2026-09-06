"""Strategy: Money Flow Index (MFI) MA-cross-from-oversold reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-129):
Per TradingView's "Basic Money Flow Strategy" write-up (surfaced via SERP
snippet, corroborated by Investopedia/FxPro/TrendSpider/VT Markets on the
standard 80/20 overbought/oversold thresholds): the Money Flow Index (MFI,
a volume-weighted RSI variant using typical price * volume as "money flow")
signals a long entry when MFI crosses above its own short moving average
while coming from an oversold (<20) reading -- i.e. not a simple MFI<20
threshold cross, but a confirmation cross of MFI over its own MA after an
oversold dip, meant to avoid entering too early while MFI is still falling.
Exit is symmetrically the reverse: MFI crossing below its MA from an
overbought (>80) reading, or (since this repo trades long-only) a plain
MFI/MA down-cross without the overbought qualifier, plus a max_hold_days
time-stop for robustness.

MFI is a genuinely different indicator family from RSI (already tested
extensively in this repo) because it weights price change by dollar volume
("money flow") rather than using price change alone -- a volume-confirmed
momentum oscillator, not a pure-price one. First MFI-based strategy in this
repo.

Source: Google SERP snippet of https://www.tradingview.com/support/solutions/43000502348/
("Money Flow Index (MFI) — Indicators and Strategies") plus corroborating
80/20 threshold snippets from Investopedia/FxPro/TrendSpider (web_search
errored on this iteration's query; browser_exec used for the Google search
itself).

Signal logic
------------
- MFI(mfi_window) computed the standard way: typical price = (H+L+C)/3;
  raw money flow = typical_price * volume; positive/negative money flow
  based on typical_price change vs prior bar; money_ratio = sum(positive
  MF, mfi_window) / sum(negative MF, mfi_window); MFI = 100 - 100/(1+money_ratio).
- MFI_MA = simple moving average of MFI over `ma_window` bars.
- Entry (long): MFI was below `oversold_threshold` within the last
  `lookback_bars` bars AND MFI just crossed above MFI_MA.
- Exit: MFI crosses below MFI_MA (from any level), OR a `max_hold_days`
  time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mfi(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    raw_money_flow = typical_price * df["volume"]
    tp_change = typical_price.diff()

    positive_flow = raw_money_flow.where(tp_change > 0, 0.0)
    negative_flow = raw_money_flow.where(tp_change < 0, 0.0)

    positive_sum = positive_flow.rolling(window).sum()
    negative_sum = negative_flow.rolling(window).sum()

    money_ratio = positive_sum / negative_sum.replace(0, 1e-12)
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi


def generate_signals(
    price_df: pd.DataFrame,
    mfi_window: int = 14,
    ma_window: int = 9,
    oversold_threshold: float = 20.0,
    lookback_bars: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    mfi = _mfi(df, mfi_window)
    mfi_ma = mfi.rolling(ma_window).mean()

    was_oversold_recently = (mfi < oversold_threshold).rolling(lookback_bars).max().astype(bool)
    cross_up = (mfi > mfi_ma) & (mfi.shift(1) <= mfi_ma.shift(1))
    entry = was_oversold_recently.shift(1).fillna(False) & cross_up.fillna(False)

    cross_down = (mfi < mfi_ma) & (mfi.shift(1) >= mfi_ma.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
