"""Strategy: Rebalancing-Pressure Front-Run (equity/bond relative-performance
signal, gated to a turn-of-month calendar window).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Harvey, Mazzoleni & Melone, "The Unintended Consequences of Rebalancing"
(summarized at
https://www.quantitativo.com/p/the-unintended-consequences-of-rebalancing):
institutional investors (pension/mutual funds) mechanically rebalance
between equities and bonds at month-end per calendar rules or drift
thresholds. When equities have underperformed bonds recently, rebalancers
must BUY equities (and sell bonds) to restore target weights -- creating
predictable end-of-month buying pressure that pushes equity prices up,
reverting within ~2 weeks. The paper's own "Threshold Signal" measures
equity/bond weight deviation from target, and its "Calendar Signal"
captures end-of-month timing; both predict next-day cross-asset returns
(a 1-std signal increase toward "equities overweight" predicts ~17bps
next-day equity decline -- i.e. the inverse, "equities underweight",
predicts a positive next-day move).

This repo already has GEM-style dual momentum (equity vs bond absolute/
relative momentum switching, 2026-09-04-097 rejected; 2026-09-07 SPY/TLT
and SPY/IEF variants) but none use a REBALANCING-PRESSURE framing: this
strategy is long-only equity, testable via `generate_returns_fn(price_df,
**params)` where `price_df` is the primary asset (equity or crypto per the
grid) and a bond proxy (TLT) is fetched internally as the rebalancing
counterparty. It is a long-only front-run: go long the primary asset only
during a turn-of-month calendar window (last `calendar_days_before` trading
days of month, but only if the primary asset's trailing `lookback`-day
return is at least `underperf_threshold` (as a fraction, e.g. -0.03 = -3%)
BELOW the bond proxy's trailing return over the same lookback (i.e.
equities are "underweight" relative to bonds and due for rebalancing
inflows). For crypto, there is no equivalent institutional pension/401k
rebalancing flow into a bond sleeve, so this is expected to fail there
(falsification check) -- TLT is still fetched as the "bond" leg for
comparability across asset classes even though the underlying arbitrage
mechanism structurally does not apply to crypto.

Signal logic
------------
- rel_perf[t] = pct_change(primary_close, lookback)[t] - pct_change(TLT_close, lookback)[t]
  (aligned on the primary asset's dates; TLT return forward/back-filled
  onto crypto's 24/7 calendar since TLT only trades equity sessions).
- calendar window[t] = True iff t falls within the last `calendar_days_before`
  trading days of its month (turn-of-month, per Lakonishok & Smidt framing
  used elsewhere in this repo).
- Position[t] = 1 iff calendar_window[t-1] AND rel_perf[t-1] <=
  underperf_threshold (decision known as of prior close, shifted forward
  1 bar); else 0. Holds the primary asset's close-to-close return while
  active (standard daily-bar long-only hold, no explicit exit rule beyond
  the calendar window closing).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_BOND_PROXY = "TLT"
_bond_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_bond_close(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch TLT close, reindexed/forward-filled onto `index`."""
    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    key = (start.date(), end.date())
    if key not in _bond_cache:
        bond_df = load_equity(_BOND_PROXY, start, end)
        bond_df = _prep(bond_df)
        _bond_cache[key] = bond_df["close"]
    bond_close = _bond_cache[key]
    # Align to primary index (handles crypto's 24/7 calendar vs TLT's
    # equity-session-only calendar via forward/back fill).
    bond_close = bond_close.reindex(bond_close.index.union(index)).sort_index()
    bond_close = bond_close.ffill().bfill()
    return bond_close.reindex(index)


def _turn_of_month_window(index: pd.DatetimeIndex, calendar_days_before: int) -> pd.Series:
    """True for the last `calendar_days_before` trading days of each month."""
    s = pd.Series(index.month, index=index)
    is_month_end_block = pd.Series(False, index=index)
    for _, group_idx in s.groupby([index.year, index.month]).groups.items():
        tail = group_idx[-calendar_days_before:] if len(group_idx) >= calendar_days_before else group_idx
        is_month_end_block.loc[tail] = True
    return is_month_end_block


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 10,
    underperf_threshold: float = -0.03,
    calendar_days_before: int = 3,
) -> pd.Series:
    """Return a {0,1} series: 1 = long the primary asset this bar."""
    df = _prep(price_df)
    close = df["close"]

    bond_close = _get_bond_close(df.index)

    primary_ret = close.pct_change(lookback)
    bond_ret = bond_close.pct_change(lookback)
    rel_perf = (primary_ret - bond_ret).fillna(0.0)

    tom_window = _turn_of_month_window(df.index, calendar_days_before)

    raw_signal = tom_window & (rel_perf <= underperf_threshold)
    position = raw_signal.shift(1).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Long-only close-to-close returns while the rebalancing-pressure signal is on."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, **kwargs)
    asset_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * asset_ret
    return strategy_ret
