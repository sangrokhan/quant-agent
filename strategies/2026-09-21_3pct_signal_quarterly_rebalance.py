"""Strategy: Jason Kelly's "3% Signal" quarterly growth-target rebalancing,
single-asset adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-182):
Per CXO Advisory's "Long-term Tests of Simple X% Rules"
(https://www.cxoadvisory.com/technical-trading/long-term-tests-of-simple-x-rules/),
Jason Kelly's "3% Signal" book describes a quarterly rebalancing rule
between a stock fund and a bond fund:

    - Start with an X0% stock / (100-X0)% cash allocation (source tests
      80/20 and 60/40).
    - Each quarter, compare the stock fund's growth to a target X% (source
      tests 2%-4% in 0.5% steps).
    - If the stock fund grew MORE than X% this quarter, sell the excess
      growth back into cash (lock in gains above target).
    - If the stock fund grew LESS than X% this quarter (including a
      decline), buy the shortfall using cash (dip-buying to bring the
      stock position back up to its target growth trajectory).
    - If cash runs out, either draw it to zero and stop buying (this
      variant) or add fresh cash (source's alternate variant, not modeled
      here to keep this a fair single-asset, no-new-capital comparison).

Adapted here to this repo's single-asset contract: "bond fund" is modeled
as a zero-return cash buffer (long-only, no external bond data), and the
strategy's `position` is a CONTINUOUS stock-weight in [0, 1] (the fraction
of total notional currently allocated to the traded asset), following this
repo's established continuous-sizing pattern (see e.g.
strategies/2026-09-20_force_index_sizing_sma_trend.py) rather than a binary
0/1 signal -- appropriate here since the underlying rule is inherently a
rebalancing/sizing rule, not a discrete entry/exit signal.

This is a genuinely new indicator family for this repo: a target-growth-rate
rebalancing rule (buy dips / sell strength relative to a fixed quarterly
growth target), distinct from every moving-average/oscillator/pattern/
seasonal strategy already tested.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        Continuous stock-weight series in [0, 1], aligned to price_df.index
        (only quarter-end rebalance dates actually change the weight; it is
        held constant intra-quarter).
    generate_returns(price_df, **params) -> pd.Series
        Position-weighted daily returns (position shifted by 1 day to avoid
        look-ahead bias), no transaction costs applied here.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    initial_stock_pct: float = 0.8,
    quarterly_target_pct: float = 0.03,
) -> pd.Series:
    """Return a continuous [0,1] stock-weight series, rebalanced quarterly."""
    df = _prep(price_df)
    close = df["close"]

    # Quarter-end rebalance dates: last available bar in each calendar quarter.
    quarter_labels = close.index.to_series().dt.to_period("Q")
    quarter_end_mask = quarter_labels.ne(quarter_labels.shift(-1))
    quarter_end_idx = list(close.index[quarter_end_mask.values])

    stock_value = initial_stock_pct * 100.0
    cash_value = (1.0 - initial_stock_pct) * 100.0
    # Target stock value grows deterministically by quarterly_target_pct
    # each quarter, regardless of actual market performance.
    target_stock_value = stock_value

    weight = pd.Series(initial_stock_pct, index=close.index, dtype=float)

    prev_rebalance_price = close.iloc[0]
    last_weight = initial_stock_pct

    for i, ts in enumerate(close.index):
        if ts in quarter_end_idx and i > 0:
            current_price = close.loc[ts]
            # Grow stock_value by actual market return since last rebalance.
            growth_ratio = current_price / prev_rebalance_price if prev_rebalance_price else 1.0
            stock_value = stock_value * growth_ratio
            target_stock_value = target_stock_value * (1.0 + quarterly_target_pct)

            excess = stock_value - target_stock_value
            if excess > 0:
                # Grew more than target: sell excess into cash.
                transfer = min(excess, stock_value)
                stock_value -= transfer
                cash_value += transfer
            else:
                # Grew less than target (or declined): buy the shortfall
                # from cash, capped at available cash (no new capital added).
                shortfall = -excess
                transfer = min(shortfall, cash_value)
                stock_value += transfer
                cash_value -= transfer

            total = stock_value + cash_value
            last_weight = (stock_value / total) if total > 0 else 0.0
            prev_rebalance_price = current_price

        weight.iloc[i] = last_weight

    return weight.clip(0.0, 1.0)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0) * daily_ret
    return strategy_ret
