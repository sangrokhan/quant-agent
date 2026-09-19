"""Strategy: Statistical Dislocation Mean Reversion + rolling-CVaR tail-risk entry filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Direct rescue attempt for the recorded QQQ near-miss in 2026-09-08-140
(Statistical Dislocation quantile mean-reversion: Sharpe 0.866 vs 1.0
threshold, MDD 25.1% narrowly breaching the 25% budget, parameter
sensitivity 0.519 narrowly failing -- SPY passed cleanly at the same
config). Per Quantitativo's "More Bets, Better Bets"
(https://www.quantitativo.com/p/more-bets-better-bets), a follow-up to the
same author's "Murphy's Law" mean-reversion strategy: when naively scaling
the strategy to a wider (noisier) universe, the edge-per-trade survived but
tail risk exploded; the fix disclosed by the source was NOT a better
signal, but a tail-risk ENTRY FILTER -- before taking any trade, check the
name's own rolling CVaR 5% (Conditional Value at Risk, mean of the worst 5%
of trailing daily returns); skip the trade if that tail is "too deep"
(more negative than a threshold). The source's own numbers: adding this
single CVaR filter to the same signal/entry/exit on the Russell 3000
universe lifted Sharpe from 0.99 (unfiltered) to 1.30 and cut max drawdown
from -36.0% to -32.8% (further to -23.5% after also combining index
universes) -- purely by refusing trades in names/periods with unusually
fat tails already visible in the data, no change to the entry/exit logic
itself.

Adapted here to this repo's single-symbol (index-ETF) construction: the
"per-name" CVaR filter becomes a "per-period" CVaR filter -- since we
cannot swap to a different name, we instead only allow a dislocation entry
when the ASSET'S OWN trailing rolling CVaR 5% (over `cvar_window` days) is
NOT worse than `cvar_threshold` (i.e., skip the trade if the asset's own
recent return distribution already shows an unusually fat/dangerous left
tail -- the same "don't step on a landmine you can already see" logic,
applied through time on one asset rather than cross-sectionally across
many). Everything else (drop-quantile entry, SMA uptrend gate, fixed-
duration hold) is unchanged from 2026-09-08-140's exact implementation, to
isolate the CVaR filter's effect.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rolling_cvar(returns: pd.Series, window: int, alpha: float = 0.05) -> pd.Series:
    """Rolling CVaR (Expected Shortfall) at level `alpha`: mean of the worst
    `alpha`-fraction of returns in each trailing `window`-day slice.
    Computed with a simple rolling.apply -- window sizes here are modest
    (order of 60-120 trading days) so this stays fast enough for grid use.
    """

    def _cvar(x: pd.Series) -> float:
        n_tail = max(1, int(len(x) * alpha))
        worst = sorted(x)[:n_tail]
        return sum(worst) / len(worst)

    return returns.rolling(window, min_periods=max(20, window // 3)).apply(_cvar, raw=False)


def generate_signals(
    price_df: pd.DataFrame,
    n_day_window: int = 3,
    dist_window: int = 252,
    quantile_threshold: float = 0.15,
    trend_window: int = 200,
    hold_days: int = 5,
    cvar_window: int = 60,
    cvar_threshold: float = -0.04,
) -> pd.Series:
    """Return a {0,1} series: 1 = holding a fixed-duration long position,
    entries additionally gated by the rolling-CVaR tail-risk filter.
    """
    df = _prep(price_df)
    close = df["close"]

    n_day_return = close.pct_change(n_day_window)
    rolling_quantile = n_day_return.rolling(dist_window, min_periods=max(30, dist_window // 4)).quantile(
        quantile_threshold
    )
    drop_signal = n_day_return <= rolling_quantile

    sma = close.rolling(trend_window).mean()
    trend_filter = close > sma

    daily_ret = close.pct_change()
    rolling_cvar = _rolling_cvar(daily_ret, cvar_window)
    # Tail-risk filter: only trade when the asset's own recent CVaR 5% is
    # NOT worse (more negative) than cvar_threshold -- i.e. skip entries
    # during periods with an already-visible fat left tail.
    cvar_ok = rolling_cvar >= cvar_threshold

    entry_trigger = (drop_signal & trend_filter & cvar_ok.fillna(False)).shift(1).fillna(False)

    # Fixed-duration hold, non-overlapping: once triggered, stay in position
    # for hold_days bars, ignoring new entry signals until it closes.
    position = pd.Series(0, index=df.index, dtype=int)
    countdown = 0
    for i in range(len(df)):
        if countdown > 0:
            position.iloc[i] = 1
            countdown -= 1
        elif entry_trigger.iloc[i]:
            position.iloc[i] = 1
            countdown = hold_days - 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Close-to-close returns while holding the fixed-duration dislocation trade."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, **kwargs)
    asset_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * asset_ret
    return strategy_ret
