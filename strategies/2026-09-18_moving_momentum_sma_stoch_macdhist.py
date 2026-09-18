"""Strategy: Moving Momentum (StockCharts) -- SMA(20/150) trend bias +
Stochastic pullback + MACD-Histogram reversal confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per StockCharts.com ChartSchool's "Moving Momentum"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/moving-momentum,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content): a 3-step process combining three DIFFERENT
indicator families for three DIFFERENT jobs -- (1) TREND BIAS: 20-day SMA
above (below) the 150-day SMA sets a bullish (bearish) bias; (2) CORRECTION
IDENTIFICATION: while bias is bullish, a Stochastic Oscillator (14-period,
standard) move below 20 signals a pullback worth watching (mirror: above 80
for a bearish-bias bounce); (3) REVERSAL TRIGGER: MACD-Histogram (12,26,9)
turning positive is the actual entry trigger, confirming the pullback has
ended and the bigger uptrend is resuming (mirror: turning negative for
bearish-bias bounces). Source's own explicit caution: "Sometimes this
indicator stays negative for another week or two, so it's important to
wait for confirmation" -- i.e. don't act on the Stochastic alert alone,
wait for the MACD-Histogram sign flip.

Exit: source's own worked trading examples use price-structure stop-losses
(support/resistance) rather than a fixed mechanical exit; this repo
translates that into an exit when the bias itself flips (SMA20 crosses back
below SMA150) or a max_hold_days time-stop backstop, consistent with this
repo's convention for sources presenting discretionary/structural exits.

Distinct from every prior SMA-crossover-alone, Stochastic-alone, and
MACD-histogram-alone strategy in this repo (dozens of each) via requiring
this SPECIFIC 3-step chained confirmation across three indicator families
(a slower dual-SMA bias filter -> a bounded-oscillator correction-alert ->
a momentum-histogram sign-flip trigger) -- the same "one tool per job"
multi-indicator-stack pattern the source itself calls out, but with a
distinct set of three specific tools/parameters not used together
elsewhere in this repo (2026-09-10-077's Stack-A used EMA50/200+EMA20
pullback+RSI midline+MACD-zero, a different tool selection entirely).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stochastic_k(df: pd.DataFrame, window: int) -> pd.Series:
    low_min = df["low"].rolling(window).min()
    high_max = df["high"].rolling(window).max()
    denom = (high_max - low_min).replace(0, float("nan"))
    k = 100.0 * (df["close"] - low_min) / denom
    return k.fillna(50.0)


def _macd_histogram(close: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def _core(
    price_df: pd.DataFrame,
    sma_fast: int = 20,
    sma_slow: int = 150,
    stoch_window: int = 14,
    stoch_low: float = 20.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    sma_f = close.rolling(sma_fast).mean()
    sma_s = close.rolling(sma_slow).mean()
    bullish_bias = sma_f > sma_s

    k = _stochastic_k(df, stoch_window)
    pullback_alert = k < stoch_low

    hist = _macd_histogram(close, macd_fast, macd_slow, macd_signal)
    hist_turns_positive = (hist > 0) & (hist.shift(1) <= 0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    awaiting_confirm = False
    hold_days = 0
    for i in range(len(df)):
        bias = bool(bullish_bias.iloc[i]) if pd.notna(bullish_bias.iloc[i]) else False
        if in_pos:
            hold_days += 1
            if not bias or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                awaiting_confirm = False
            else:
                position.iloc[i] = 1
        else:
            if bias:
                if bool(pullback_alert.iloc[i]):
                    awaiting_confirm = True
                if awaiting_confirm and bool(hist_turns_positive.iloc[i]):
                    in_pos = True
                    hold_days = 0
                    awaiting_confirm = False
                    position.iloc[i] = 1
            else:
                awaiting_confirm = False
    return position


def generate_signals(
    price_df: pd.DataFrame,
    sma_fast: int = 20,
    sma_slow: int = 150,
    stoch_window: int = 14,
    stoch_low: float = 20.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    max_hold_days: int = 40,
) -> pd.Series:
    return _core(
        price_df, sma_fast, sma_slow, stoch_window, stoch_low,
        macd_fast, macd_slow, macd_signal, max_hold_days,
    )


def generate_returns(
    price_df: pd.DataFrame,
    sma_fast: int = 20,
    sma_slow: int = 150,
    stoch_window: int = 14,
    stoch_low: float = 20.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = _core(
        df, sma_fast, sma_slow, stoch_window, stoch_low,
        macd_fast, macd_slow, macd_signal, max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    return daily_ret * position.shift(1).fillna(0)
