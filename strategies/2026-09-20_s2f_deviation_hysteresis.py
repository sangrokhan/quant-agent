"""Strategy: Bitcoin Stock-to-Flow (S2F) valuation-deviation hysteresis gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-098):
PlanB's Stock-to-Flow (S2F) model (Medium, "Modeling Bitcoin Value with
Scarcity", read via Google SERP this iteration): S2F = existing supply
(stock) / annual new issuance (flow). PlanB's own published log-linear
regression: ln(model market value) = 3.3 * ln(S2F) + 14.6 (R^2 ~0.95),
equivalently model_price ~= 0.18 * S2F^3.3 (Bitcoin.com Charts' own restated
per-BTC-price form of the same fit, corroborated by TradingView's
"Stocktoflow" script: ln(Model Price) = 3.3297*ln(S2F) - 12.214). A
ResearchGate-indexed paper ("Dissecting the stock to flow model for
Bitcoin") explicitly describes "a dynamic trading strategy that goes long
(short) when Bitcoin is undervalued (overvalued) according to S2F" -- this
strategy implements that long/flat (long-only per SAFETY.md convention).

Feasibility note (same argument as this trigger's earlier Puell Multiple
strategy, 2026-09-20-097): S2F's stock/flow inputs are fully deterministic
from the public Bitcoin block-subsidy halving schedule alone (no external
on-chain API needed), distinct from this repo's many genuinely
infeasible on-chain metrics (MVRV realized cap, NUPL, SOPR, hash rate --
all require external chain-state data data/loaders.py cannot fetch).

Signal logic (long/flat hysteresis, same mechanic as the accepted Crypto
Fear & Greed hysteresis strategy 2026-09-20-029 and this iteration's Puell
strategy): go/stay long while price <= model_price * (1 - band) (BTC
undervalued vs. the S2F fair-value line); flip flat once price >=
model_price * (1 + band) (overvalued); hold previous state in between.

As with the halving-schedule-derived Puell strategy, when grid-tested
against equity symbols the S2F signal degenerates into a pure BTC-specific
calendar/supply construction applied to the wrong asset's price -- expected
to show no genuine economic edge on equities; the real test is the crypto
cells (BTC/USDT specifically -- ETH does not follow BTC's own emission
schedule, so this signal is also expected to be a mismatch on ETH/USDT).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd

# (halving_date, block_reward_starting_at_this_halving, cumulative BTC supply
# mined by the START of this halving epoch -- i.e. supply(h) at t=h).
# Cumulative supply figures are the well-documented historical totals
# (210,000 blocks/epoch * reward of the PRIOR epoch, summed).
HALVING_EPOCHS = [
    (pd.Timestamp("2009-01-03", tz="UTC"), 50.0, 0.0),
    (pd.Timestamp("2012-11-28", tz="UTC"), 25.0, 10_500_000.0),
    (pd.Timestamp("2016-07-09", tz="UTC"), 12.5, 15_750_000.0),
    (pd.Timestamp("2020-05-11", tz="UTC"), 6.25, 18_375_000.0),
    (pd.Timestamp("2024-04-20", tz="UTC"), 3.125, 19_687_500.0),
    (pd.Timestamp("2028-04-01", tz="UTC"), 1.5625, 20_343_750.0),  # projected
]
BLOCKS_PER_DAY = 144.0


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stock_and_flow(idx_utc: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """Deterministic BTC circulating supply (stock) and annualized issuance
    rate (flow) per date, from the public halving schedule alone."""
    stock = pd.Series(0.0, index=idx_utc)
    flow = pd.Series(0.0, index=idx_utc)
    for i, (h, reward, supply_at_h) in enumerate(HALVING_EPOCHS):
        next_h = HALVING_EPOCHS[i + 1][0] if i + 1 < len(HALVING_EPOCHS) else None
        mask = (idx_utc >= h) if next_h is None else (idx_utc >= h) & (idx_utc < next_h)
        days_since_h = (idx_utc[mask] - h).total_seconds() / 86400.0
        stock.loc[mask] = supply_at_h + days_since_h * BLOCKS_PER_DAY * reward
        flow.loc[mask] = BLOCKS_PER_DAY * reward * 365.0
    return stock, flow


def _model_price(df: pd.DataFrame) -> pd.Series:
    idx = df.index
    idx_utc = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    stock, flow = _stock_and_flow(idx_utc)
    s2f = pd.Series(stock.values / flow.values, index=df.index)
    # PlanB's published fit, per-BTC-price restatement: model_price ~= 0.18 * S2F^3.3
    model_price = 0.18 * (s2f ** 3.3)
    return model_price


def generate_signals(
    price_df: pd.DataFrame,
    band: float = 0.5,
) -> pd.Series:
    """Long/flat hysteresis gate on price deviation from the S2F model line.

    Long (1) while price <= model_price*(1-band) (undervalued vs. S2F fair
    value); flip flat (0) once price >= model_price*(1+band) (overvalued);
    hold previous state in between (hysteresis).
    """
    df = _prep(price_df)
    close = df["close"]
    model_price = _model_price(df)

    enter_line = model_price * (1.0 - band)
    exit_line = model_price * (1.0 + band)

    position = pd.Series(0, index=df.index, dtype=int)
    state = 0
    for i in range(len(df)):
        c = close.iloc[i]
        if c <= enter_line.iloc[i]:
            state = 1
        elif c >= exit_line.iloc[i]:
            state = 0
        position.iloc[i] = state
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
