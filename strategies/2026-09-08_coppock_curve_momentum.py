"""Strategy: Coppock Curve momentum indicator, adapted from its original
monthly timeframe to trading-day-equivalent periods on daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per https://www.quantifiedstrategies.com/coppock-curve-strategy/, the
Coppock Curve -- a weighted moving average of the sum of two rate-of-change
(ROC) indicators, originally designed by Edwin Coppock (1962) on MONTHLY
bars with periods (11, 14, 10) chosen to approximate the psychological
"mourning recovery" period -- captures broad market uptrends while
filtering out downtrends/corrections, historically applied to the S&P 500
index. Source's own monthly backtest (since 1960): 12 trades, 100% win
rate, avg gain 45%/trade, max drawdown 30.16% vs buy-and-hold 52.56%,
invested 73.75% of the time.

Adaptation note: this repo's daily-bar data (2000-2026, ~6700 daily bars)
is too short to test the ORIGINAL monthly-bar version meaningfully (would
yield only a handful of trades over the whole backtest window). Instead,
this strategy scales the three period parameters from months to
approximate trading-day equivalents (~21 trading days/month): roc1=231d
(11mo), roc2=294d (14mo), wma_period=210d (10mo) as defaults, all exposed
as tunable params so the grid test (Step 6) can probe faster variants too
(e.g. halved periods) to see whether the strategy still holds an edge at a
higher signal frequency more suited to this repo's data length.

Signal logic
------------
- ROC1 = pct change of close over roc1_period trading days.
- ROC2 = pct change of close over roc2_period trading days.
- Coppock = WMA(ROC1 + ROC2, wma_period) -- weighted moving average giving
  more weight to recent values (weights 1..wma_period).
- Entry (long): Coppock crosses from <=0 to >0 (zero-line cross up).
- Exit: Coppock crosses from >=0 to <0 (zero-line cross down), or
  max_hold_days time-stop (source's own monthly version has no explicit
  stop, but a time-stop backstop avoids indefinite mega-multi-year holds
  incompatible with this repo's grid-testing/validator conventions).
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = list(range(1, window + 1))
    total_weight = sum(weights)
    return series.rolling(window).apply(
        lambda x: sum(w * v for w, v in zip(weights, x)) / total_weight, raw=True
    )


def _coppock(close: pd.Series, roc1_period: int, roc2_period: int, wma_period: int) -> pd.Series:
    roc1 = close.pct_change(roc1_period) * 100.0
    roc2 = close.pct_change(roc2_period) * 100.0
    return _wma(roc1 + roc2, wma_period)


def generate_signals(
    price_df: pd.DataFrame,
    roc1_period: int = 231,
    roc2_period: int = 294,
    wma_period: int = 210,
    max_hold_days: int = 500,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    coppock = _coppock(close, roc1_period, roc2_period, wma_period)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(df.index)):
        c = coppock.iloc[i]
        c_prev = coppock.iloc[i - 1] if i > 0 else float("nan")
        if in_position:
            hold_days += 1
            crossed_down = (not pd.isna(c)) and (not pd.isna(c_prev)) and c_prev >= 0 and c < 0
            if crossed_down or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            crossed_up = (not pd.isna(c)) and (not pd.isna(c_prev)) and c_prev <= 0 and c > 0
            if crossed_up:
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    roc1_period: int = 231,
    roc2_period: int = 294,
    wma_period: int = 210,
    max_hold_days: int = 500,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        roc1_period=roc1_period,
        roc2_period=roc2_period,
        wma_period=wma_period,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
