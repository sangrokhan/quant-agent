"""Strategy: Triple crypto-proxy MAJORITY-VOTE stress gate (GBTC/BTC,
ETHE/ETH, MSTR/BTC ratio z-scores -- >=2 of 3 must signal stress) on a
primary asset's SMA trend-following signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
This cron trigger's iteration 2026-09-27-097 required BOTH GBTC/BTC and
ETHE/ETH ratio z-scores to simultaneously signal stress (a strict AND-gate
across 2 signals) before flattening a primary asset's trend signal
(accepted QQQ+SPY with the trigger's strongest margins). This iteration
tests a genuinely distinct aggregation rule: a 3-proxy MAJORITY VOTE
(>=2 of 3 must signal stress), adding MSTR/BTC (MicroStrategy's
mNAV-premium proxy, already validated as an independent cross-asset signal
in this repo's 2026-09-20-040/041, though used there as a ratio-LEVEL
trend gate rather than a z-score stress vote) as a third independent leg.

The majority-vote rule is a MEANINGFULLY DIFFERENT aggregation logic from
the strict AND-of-2: it tolerates one proxy dissenting (e.g. idiosyncratic
noise or a lagging signal in one specific trust/proxy) while still acting
on genuine 2-out-of-3 consensus, versus AND-of-2's requirement that EVERY
signal agree. This should trade OFF specificity (AND-of-2 is stricter, so
should have fewer false positives) for sensitivity (majority-vote should
catch more genuine stress episodes, potentially at the cost of more
whipsaw) -- an empirical question this iteration's grid test settles.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _ratio_zscore(a: pd.Series, b: pd.Series, zscore_window: int) -> pd.Series:
    merged = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    ratio = merged["a"] / merged["b"]
    roll_mean = ratio.rolling(zscore_window).mean()
    roll_std = ratio.rolling(zscore_window).std()
    zscore = (ratio - roll_mean) / roll_std.replace(0, float("nan"))
    return zscore


def _triple_proxy_stress_vote(
    index: pd.DatetimeIndex, zscore_window: int, low_z_threshold: float
) -> pd.Series:
    from loaders import load_equity, load_crypto

    start = index.min() - pd.Timedelta(days=zscore_window * 3 + 30)
    end = index.max() + pd.Timedelta(days=5)

    gbtc = _prep(load_equity("GBTC", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    ethe = _prep(load_equity("ETHE", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    mstr = _prep(load_equity("MSTR", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    btc = _prep(load_crypto("BTC/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    eth = _prep(load_crypto("ETH/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]

    gbtc_z = _ratio_zscore(gbtc, btc, zscore_window)
    ethe_z = _ratio_zscore(ethe, eth, zscore_window)
    mstr_z = _ratio_zscore(mstr, btc, zscore_window)

    gbtc_z = gbtc_z.reindex(index, method="ffill")
    ethe_z = ethe_z.reindex(index, method="ffill")
    mstr_z = mstr_z.reindex(index, method="ffill")

    votes = (
        (gbtc_z <= low_z_threshold).astype(int).fillna(0)
        + (ethe_z <= low_z_threshold).astype(int).fillna(0)
        + (mstr_z <= low_z_threshold).astype(int).fillna(0)
    )
    stress = votes >= 2
    return stress


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    zscore_window: int = 90,
    low_z_threshold: float = -1.0,
    min_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    base_trend = close > sma

    stress = _triple_proxy_stress_vote(close.index, zscore_window, low_z_threshold)

    raw_position = (base_trend & (~stress.fillna(False))).astype(int)

    n = len(raw_position)
    raw_v = raw_position.values
    state = raw_v.copy()
    last_change = 0
    for i in range(1, n):
        if state[i] != state[i - 1]:
            if (i - last_change) < min_hold_days:
                state[i] = state[i - 1]
            else:
                last_change = i

    position = pd.Series(state, index=close.index).astype(bool)
    signal = position.shift(1).fillna(False).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    zscore_window: int = 90,
    low_z_threshold: float = -1.0,
    min_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        trend_window=trend_window,
        zscore_window=zscore_window,
        low_z_threshold=low_z_threshold,
        min_hold_days=min_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions * daily_ret
    return strat_ret.fillna(0.0)
