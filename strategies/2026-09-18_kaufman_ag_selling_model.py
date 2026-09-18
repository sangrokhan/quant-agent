"""Strategy: Perry J. Kaufman's "Ag Selling Model" (TASC August 2026).

Hypothesis (see knowledge_base/strategies_log.jsonl for this id): Kaufman's
Ag Selling Model is a seasonal timing model for hedging/selling grain
positions -- it goes SHORT (sell) whenever price rallies far enough above
its own trend (a 40-day SMA plus an ATR-based buffer) during the part of
the crop year after harvest-year planting uncertainty has passed, and
flattens (covers/exits) at the start of the new crop year. Adapted here
long-only-inverse (short signal) applied to grain-tracking ETFs (CORN,
WEAT, SOYB) as a testable proxy for futures (this repo's data/loaders.py
doesn't support futures contracts directly, but ETF proxies track the same
underlying commodity price dynamics closely enough for a first pass).

Source: https://traders.com/Documentation/FEEDbk_docs/2026/08/TradersTips.html
(thinkorswim thinkscript code, fully disclosed formula; fetched via
browser_exec -- web_search DDGS backend failing this cron trigger).

Signal logic (thinkscript -> Python translation)
-------------------------------------------------
- Trend = SMA(close, average_length)
- ATR = SMA(TrueRange, atr_length)
- SellLevel = Trend + ATR * atr_factor
- "Selling season" begins `delay_in_months` months after
  `crop_year_start_month` (e.g. Nov start + 4-month delay = selling season
  begins ~March) and runs until the next crop_year_start_month.
- Short entry ("sell"): high >= SellLevel AND we're in the selling season
  AND at least `days_between_sales` trading days have passed since the
  last sell signal (rate-limits repeated sells).
- Exit (cover short): at the start of the next crop year
  (crop_year_start_month rolls over) -- unconditional flatten, mirroring
  the source's "exit at harvest" framing.
- First iteration testing a short-only seasonal model in this repo.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({-1,0} short/flat)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    average_length: int = 40,
    atr_length: int = 20,
    atr_factor: float = 2.5,
    crop_year_start_month: int = 11,
    delay_in_months: int = 4,
    days_between_sales: int = 30,
) -> pd.Series:
    """Return a {-1,0} short/flat position series (short-only seasonal model)."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    trend = close.rolling(average_length).mean()
    tr = _true_range(df)
    atr = tr.rolling(atr_length).mean()
    sell_level = trend + atr * atr_factor

    months = df.index.month
    n = len(df)

    position = [0.0] * n
    days_since_sale = days_between_sales  # allow immediate sale at season start (mirrors CompoundValue seed)
    in_short = False

    close_arr = close.to_numpy()
    high_arr = high.to_numpy()
    sell_level_arr = sell_level.to_numpy()
    months_arr = months.to_numpy()

    prev_month = None
    for i in range(n):
        month = int(months_arr[i])
        crop_year_start = prev_month is not None and month == crop_year_start_month and prev_month != crop_year_start_month
        prev_month = month

        if crop_year_start:
            days_since_sale = days_between_sales
            in_short = False

        # months elapsed since crop_year_start_month, wrapping mod 12
        months_elapsed = (month - crop_year_start_month) % 12
        begin_sales = months_elapsed >= delay_in_months

        to_sell = (
            begin_sales
            and days_since_sale >= days_between_sales
            and not pd.isna(sell_level_arr[i])
            and high_arr[i] >= sell_level_arr[i]
        )

        if to_sell:
            in_short = True
            days_since_sale = 0
        else:
            days_since_sale += 1

        position[i] = -1.0 if in_short else 0.0

    return pd.Series(position, index=df.index, dtype=float)


def generate_returns(
    price_df: pd.DataFrame,
    average_length: int = 40,
    atr_length: int = 20,
    atr_factor: float = 2.5,
    crop_year_start_month: int = 11,
    delay_in_months: int = 4,
    days_between_sales: int = 30,
) -> pd.Series:
    """Daily strategy returns (no transaction costs -- applied separately)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        average_length=average_length,
        atr_length=atr_length,
        atr_factor=atr_factor,
        crop_year_start_month=crop_year_start_month,
        delay_in_months=delay_in_months,
        days_between_sales=days_between_sales,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    # short position * negative price move = positive strategy return
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
