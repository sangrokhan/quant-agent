"""Strategy: RSI(2) Oversold-Recovery Mean Reversion on Solana / XRP
(higher-beta altcoins), testing whether Larry Connors-style short-lookback
RSI mean reversion generalizes beyond this repo's existing BTC/USDT and
ETH/USDT crypto universe.

Source: CoinQuant.ai's "XRP Trading Strategy: 3 Approaches Backtested
During the June 2026 Selloff" (https://www.coinquant.ai/blog/xrp-trading-
strategy-3-approaches-backtested-during-the-june-2026-selloff, read via
browser_exec this iteration -- web_search DDGS backend TLS-erroring on
every query attempted) found that during a March-June 2026 XRP selloff, a
plain RSI(14) 30/70 oversold-recovery mean-reversion rule was the ONLY one
of three tested approach types (mean reversion / EMA trend-following /
MACD momentum) that stayed profitable (+7.7%, Sharpe 1.36, 100% win rate
over 3 trades), while EMA-crossover trend-following (-9.0%) and MACD
momentum (-22.5%) both lost money -- the source's own explanation is that
retail-sentiment-driven altcoins like XRP overshoot on selloffs and
partially mean-revert rather than trending persistently, unlike BTC.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): if higher-beta, more retail-sentiment-driven altcoins genuinely show a
STRONGER mean-reversion tendency than BTC/ETH (this repo's only crypto
symbols tested to date), then a Larry Connors-style RSI(2) oversold
mean-reversion rule (already accepted on equities in this repo, id
2026-09-03-005, but never tested on crypto beyond BTC/ETH) should show a
cleaner edge on SOL/USDT and XRP/USDT than it did when previously tested
on BTC/USDT and ETH/USDT (where RSI-mean-reversion-family strategies in
this repo have mostly failed/been rejected). This is the first strategy in
this repo to test SOL/USDT or XRP/USDT at all -- every prior crypto entry
in this knowledge base is BTC/USDT and/or ETH/USDT only.

Signal logic
------------
- Daily-resampled close (crypto loader default is hourly; resample to
  daily to match this repo's standard RSI-mean-reversion construction and
  keep grid-test/validator compatibility).
- Entry (long): RSI(rsi_period) closes <= oversold_threshold.
- Exit: RSI(rsi_period) closes >= exit_threshold, or a max_hold_days
  time-stop (source's own multi-day-hold nature; the 3 backtested trades
  in the source held multiple days each, not a single bar).
- No trend filter (this repo's existing 200-day-SMA-gated equity RSI(2)
  strategy uses one, but the source's own XRP test used NO trend filter at
  all and specifically credits the strategy's success to NOT requiring
  trend persistence -- testing the ungated version here is the more
  faithful replication of the source's actual claim).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep_daily(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    # Crypto loader default interval is hourly; resample to daily close.
    daily = df["close"].resample("1D").last().dropna()
    return pd.DataFrame({"close": daily})


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 2,
    oversold_threshold: float = 10.0,
    exit_threshold: float = 70.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series (daily bars)."""
    df = _prep_daily(price_df)
    close = df["close"]
    rsi = _rsi(close, rsi_period)

    entry_cond = (rsi <= oversold_threshold).fillna(False)
    exit_cond = (rsi >= exit_threshold).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cond.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs), daily bars."""
    df = _prep_daily(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
