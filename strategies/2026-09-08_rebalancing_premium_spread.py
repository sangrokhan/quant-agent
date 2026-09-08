"""Strategy: Rebalancing-Premium Long-Short (primary asset vs a partner
asset, daily-rebalanced equal-weight portfolio vs buy-and-hold weight-drift
portfolio).

Hypothesis (see knowledge_base/strategies_log.jsonl, this id), sourced from
Quantpedia "Rebalancing Premium in Cryptocurrencies"
(https://quantpedia.com/strategies/rebalancing-premium-in-cryptocurrencies/,
paper: Hanicova/Vojtko, SSRN 3982120): a periodically-rebalanced
equal-weight portfolio of uncorrelated/volatile assets earns a structural
"rebalancing premium" (a.k.a. diversification return) over a buy-and-hold
portfolio of the same assets left to drift, because rebalancing forces
systematic buy-low/sell-high between the constituents. The source's own
strategy: long a daily-rebalanced 27-crypto equal-weight portfolio, short a
buy-and-hold (unrebalanced) version of the same 27-crypto portfolio with a
70% short weight, reporting Sharpe 2.93 (2018-2021, small starting capital
fraction).

We adapt this DOWN to the smallest possible 2-asset version that fits this
repo's single-primary-asset strategy contract: pair the PRIMARY asset with
a fixed PARTNER asset (chosen for low correlation/different vol profile),
form a daily-rebalanced 50/50 equal-weight portfolio and a buy-and-hold
(weight-drift) portfolio of the same two assets, and go long the spread
(rebalanced portfolio return minus short_weight * buy-hold portfolio
return) -- an always-on structural position (no discretionary market-timing
signal, matching the source's own unconditional systematic-rebalancing
premise). For equity primaries the partner is TLT (long bonds, a classic
low-correlation-to-equities pairing already used in this repo's other
cross-asset strategies); for crypto primaries the partner is a different
crypto (ETH for a BTC primary, BTC for any other primary) since the source
paper's premise is specifically about volatile/uncorrelated CRYPTO pairs
and we want to preserve that structural setting when testing crypto
primaries, rather than defaulting to TLT (crypto rarely trades against TLT
directly with clean daily bars in the same session hours).

Signal logic
------------
- Fetch the partner asset's daily closes via data/loaders.py internally.
- Compute each asset's own daily simple return.
- Rebalanced (equal-weight) portfolio daily return_t =
  0.5 * primary_return_t + 0.5 * partner_return_t (implicitly rebalanced
  back to 50/50 every day -- the textbook constant-mix construction).
- Buy-and-hold (weight-drift) portfolio: track cumulative weights starting
  at 50/50 and drifting with relative performance (no rebalancing), daily
  portfolio return = w_primary_t * primary_return_t + w_partner_t *
  partner_return_t using the DRIFTED weights as of the start of day t.
- Strategy return_t = rebalanced_return_t - short_weight *
  buyhold_return_t (the source's own long-rebalanced/short-buy-hold
  spread construction).
- Always-on (position = 1 for the full available history) -- this is a
  structural risk-premium harvest, not a timed entry/exit signal, matching
  the source's own unconditional systematic-rebalancing premise; no
  trend/oscillator gate is applied.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1}, always 1
        once both return series are available)
    generate_returns(price_df, **params) -> pd.Series  (the long-short
        rebalancing-premium spread return described above)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_partner_returns(idx: pd.DatetimeIndex, partner_symbol: str, is_crypto: bool) -> pd.Series:
    """Fetch the partner asset's daily simple returns, reindexed/ffilled
    onto the strategy's own trading-day index."""
    from loaders import load_equity, load_crypto

    pad_days = 30
    start = (idx.min() - pd.Timedelta(days=pad_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    if is_crypto:
        d = load_crypto(partner_symbol, start=start, end=end)
    else:
        d = load_equity(partner_symbol, start=start, end=end)

    close = d.set_index("timestamp")["close"].sort_index()
    close.index = close.index.tz_localize(None) if close.index.tz is not None else close.index
    ret = close.pct_change()

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    ret = ret.reindex(ret.index.union(target_idx)).sort_index().fillna(0.0)
    ret = ret.reindex(target_idx)
    ret.index = idx
    return ret


def _rebalanced_and_buyhold_returns(
    primary_ret: pd.Series, partner_ret: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Return (rebalanced_50_50_daily_return, buyhold_weight_drift_daily_return)."""
    n = len(primary_ret)
    rebal_ret = 0.5 * primary_ret + 0.5 * partner_ret

    buyhold_ret = pd.Series(0.0, index=primary_ret.index)
    w_primary, w_partner = 0.5, 0.5
    for i in range(n):
        r_p = primary_ret.iloc[i] if pd.notna(primary_ret.iloc[i]) else 0.0
        r_q = partner_ret.iloc[i] if pd.notna(partner_ret.iloc[i]) else 0.0
        port_ret = w_primary * r_p + w_partner * r_q
        buyhold_ret.iloc[i] = port_ret
        # Drift weights forward for next day based on this day's relative growth.
        new_v_primary = w_primary * (1 + r_p)
        new_v_partner = w_partner * (1 + r_q)
        total = new_v_primary + new_v_partner
        if total > 0:
            w_primary, w_partner = new_v_primary / total, new_v_partner / total
    return rebal_ret, buyhold_ret


def generate_signals(
    price_df: pd.DataFrame,
    partner_symbol: str = "TLT",
    is_crypto_partner: bool = False,
    short_weight: float = 0.7,
) -> pd.Series:
    """Always-on {0,1} position series (1 once return data is available)."""
    df = _prep(price_df)
    idx = df.index
    position = pd.Series(1, index=idx, dtype=int)
    position.iloc[:2] = 0  # need at least 2 bars for pct_change to be defined
    return position


def generate_returns(
    price_df: pd.DataFrame,
    partner_symbol: str = "TLT",
    is_crypto_partner: bool = False,
    short_weight: float = 0.7,
) -> pd.Series:
    """Rebalancing-premium spread: long daily-rebalanced 50/50 portfolio,
    short (short_weight) the buy-and-hold weight-drift portfolio of the
    same two assets (primary + partner)."""
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    primary_ret = close.pct_change().fillna(0.0)

    try:
        partner_ret = _get_partner_returns(idx, partner_symbol, is_crypto_partner)
    except Exception:
        return pd.Series(0.0, index=idx)

    rebal_ret, buyhold_ret = _rebalanced_and_buyhold_returns(primary_ret, partner_ret)
    spread_ret = rebal_ret - short_weight * buyhold_ret

    position = generate_signals(
        price_df, partner_symbol=partner_symbol, is_crypto_partner=is_crypto_partner,
        short_weight=short_weight,
    )
    strategy_ret = position * spread_ret
    return strategy_ret
