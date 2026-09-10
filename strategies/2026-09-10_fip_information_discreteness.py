"""Strategy: "Frog in the Pan" (FIP) information-discreteness continuation filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-108):
Per Da, Gurun & Warachka, "Frog in the Pan: Continuous Information and
Momentum" (SSRN/UQ working paper, Nov 2011; formula per
https://business.uq.edu.au/sites/default/files/events/files/mitch-warachka-paper.pdf,
equation 1), momentum/trend continuation is stronger when a stock's
formation-period return is built from many small SAME-signed daily moves
("continuous information") rather than a few large jumps ("discrete
information"), because limited-attention investors underreact to steadily
arriving small news but react promptly to big, salient news. The paper's own
information-discreteness (ID) measure:

    ID = sign(PRET) * (%neg - %pos)

where PRET is the cumulative return over a formation window (paper: trailing
12 months skipping the most recent month) and %pos/%neg are the percentage
of daily-return-positive/negative days within that formation window. A LOW
ID (very negative, close to its floor of -1) means the trend was built from
mostly same-direction small moves -> "continuous" -> paper's own empirical
finding: momentum profits increase monotonically as ID becomes more
continuous (Table 2: 2.91% discrete quintile -> 8.86% continuous quintile,
6-month unadjusted return, t-stat 5.13).

Adapted here as a single-asset time-series regime filter (the original paper
is a cross-sectional equity factor sort; this repo's loaders provide only
single-symbol OHLCV, so we operationalize the SAME underlying test: within
one asset's own daily-bar history, only stay long during an established
uptrend (PRET>0 over the trailing lookback_days window, skipping the most
recent skip_days per the source's own methodology) when that uptrend's own
ID reading is at/below id_threshold (i.e. continuous, not jumpy) -- exactly
the source's finding that continuous-information uptrends persist more
strongly and for longer (paper's Figure 2: momentum profits from continuous
information persist ~8 months vs ~3 months for discrete).

Signal logic
------------
- PRET[t] = cumulative return over the window ending skip_days before t and
  spanning lookback_days trading days (approximating the paper's "12 months
  skipping the most recent month").
- Daily returns within that same window are used to compute %pos/%neg
  (percentage of up-days / down-days), and ID[t] = sign(PRET[t]) *
  (%neg - %pos).
- Entry (long): PRET[t] > 0 (established uptrend, matches the paper's own
  restriction to past "winners") AND ID[t] <= id_threshold (continuous
  information, per the source's own definition that ID is "more negative"
  for continuous information; default id_threshold=-0.02 requires a mild
  same-direction-day skew, not exactly the -1 floor).
- Exit: PRET[t] <= 0 (uptrend has broken) OR ID[t] > id_threshold (the
  uptrend has become "discrete"/jumpy per the paper's own predicted
  breakdown of return continuation) OR a max_hold_days safety time-stop
  (the paper's own Figure 2 shows continuous-information momentum profits
  become insignificant by month 9 -- we cap holds well inside that horizon
  by default via a large max_hold_days so the time-stop is a safety
  backstop rather than the primary exit trigger).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept params as keyword arguments (grid_test.py calls them directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_id_and_pret(
    close: pd.Series, lookback_days: int, skip_days: int
) -> tuple[pd.Series, pd.Series]:
    """Compute PRET (formation-period cumulative return, skipping the most
    recent skip_days) and ID (information discreteness, per Da/Gurun/
    Warachka eq. 1) at every bar t, using only data available at t.
    """
    daily_ret = close.pct_change()

    # PRET[t]: cumulative return over the window ending skip_days bars ago,
    # spanning lookback_days bars -- i.e. close[t-skip_days] vs
    # close[t-skip_days-lookback_days].
    close_lagged = close.shift(skip_days)
    pret = close_lagged / close_lagged.shift(lookback_days) - 1.0

    # %pos / %neg over that same trailing window of daily returns (also
    # shifted by skip_days so today's own last-month return doesn't leak in,
    # matching the source's "skip the most recent month" design).
    ret_lagged = daily_ret.shift(skip_days)
    is_pos = (ret_lagged > 0).astype(float)
    is_neg = (ret_lagged < 0).astype(float)
    pct_pos = is_pos.rolling(lookback_days).mean()
    pct_neg = is_neg.rolling(lookback_days).mean()

    sign_pret = pret.apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0))
    id_measure = sign_pret * (pct_neg - pct_pos)

    return pret, id_measure


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    skip_days: int = 5,
    id_threshold: float = -0.02,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pret, id_measure = _compute_id_and_pret(close, lookback_days, skip_days)

    entry_cond = (pret > 0) & (id_measure <= id_threshold)
    exit_cond = (pret <= 0) | (id_measure > id_threshold)

    entry_cond = entry_cond.fillna(False)
    exit_cond = exit_cond.fillna(True)

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
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
