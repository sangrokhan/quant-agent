"""Strategy: Dual Momentum Rotation between Gold (GLD) and Bitcoin
("Digital Gold"), with volatility-targeted position sizing.

Source: Quantpedia "Dual Momentum Allocation Between Physical Gold and
Bitcoin (Digital Gold)" (6 May 2026, own-research article, R. Vojtko),
https://quantpedia.com/dual-momentum-allocation-between-physical-gold-and-bitcoin-digital-gold/
(visited 2026-09-13, see knowledge_base/visited_pages.jsonl). Source uses
GLD/IBIT with weekly (Wednesday close) rebalancing over Dec 2018-Apr 2026
(no transaction costs modeled).

Source's fully disclosed rule, at each weekly rebalance:
    Long BTC-proxy if: (BTC return over X weeks > GLD return over X weeks)
                        AND (BTC return over X weeks > 0%)
    Long GLD       if: (GLD return over X weeks > BTC return over X weeks)
                        AND (GLD return over X weeks > 0%)
    Flat (cash)    otherwise
Plus a volatility-targeting overlay: position weight = min(1.0, 20% /
annualized_vol_of_selected_asset), where annualized_vol uses the selected
asset's trailing 12-week (60 trading-day) daily-return stdev * sqrt(252)
(this repo substitutes daily-bar realized vol for the source's own
weekly-bar 12-week/sqrt(52) computation, since this repo's loaders are
daily-bar; directionally equivalent volatility-cap mechanic).

Source's own reported results (Dec 2018-Apr 2026, pure/uncapped, 8-week
lookback): 79.91% annualized return, Sharpe 1.64. Volatility-capped
composite (avg of 4/8/12-week lookbacks, 20% vol cap): 12.01% return,
8.77% vol, Sharpe 1.37, MDD -12.27% (vs pure composite MDD -49.40%).

This is architecturally distinct from every prior GLD/BTC entry in this
repo: 2026-09-08-082 (BTC/GLD RATIO z-score PAIRS mean-reversion, long
BTC only on cheap-ratio dips, no gold leg ever held) and the accepted
Silicon-vs-Satoshi QQQ/BTC Donchian-BREAKOUT rotation (2026-09-08-161,
different asset pair -- QQQ not GLD, and breakout not momentum). This
strategy instead ROTATES between GLD and BTC/USDT themselves using a
relative+absolute weekly MOMENTUM signal plus a volatility-targeting
position-sizing overlay (first vol-targeting position sizer in this repo
-- all prior strategies use fixed 100%/0% binary sizing).

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1}, 1 whenever
        ANY of GLD/BTC is held with nonzero weight, 0 when fully in cash)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns, vol-targeted weight applied to whichever asset the weekly
        momentum signal selects)

The primary asset (`price_df`) is expected to be GLD; BTC/USDT is fetched
internally via data/loaders.py.load_crypto (same pattern as
2026-09-08_silicon_vs_satoshi_donchian_rotation.py).
"""

from __future__ import annotations

import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_partner_close(partner_symbol: str, start, end) -> pd.Series:
    df = load_crypto(partner_symbol, start, end, interval="1d")
    df = _prep(df)
    return df["close"]


def _simulate(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_weeks: int = 8,
    vol_cap: float = 0.20,
    vol_window_days: int = 60,
    rebalance_weekday: int = 2,  # 0=Mon, 2=Wed (source's own choice)
) -> pd.DataFrame:
    df = _prep(price_df)
    gold_close = df["close"]
    start, end = df.index.min(), df.index.max()

    btc_close = _load_partner_close(partner_symbol, start, end)
    btc_close = btc_close.reindex(gold_close.index, method="ffill")

    lookback_days = lookback_weeks * 5  # approx trading days per week

    gold_mom = gold_close.pct_change(lookback_days)
    btc_mom = btc_close.pct_change(lookback_days)

    gold_daily_ret = gold_close.pct_change().fillna(0.0)
    btc_daily_ret = btc_close.pct_change().fillna(0.0)

    gold_vol = gold_daily_ret.rolling(vol_window_days).std() * np.sqrt(252)
    btc_vol = btc_daily_ret.rolling(vol_window_days).std() * np.sqrt(252)

    is_rebalance_day = pd.Series(df.index.weekday == rebalance_weekday, index=df.index)

    holding = pd.Series("cash", index=df.index, dtype=object)
    weight = pd.Series(0.0, index=df.index)

    long_btc = (btc_mom > gold_mom) & (btc_mom > 0)
    long_gold = (gold_mom > btc_mom) & (gold_mom > 0)

    holding_raw = pd.Series("cash", index=df.index, dtype=object)
    holding_raw[long_btc.fillna(False)] = "btc"
    holding_raw[long_gold.fillna(False)] = "gold"

    weight_raw = pd.Series(0.0, index=df.index)
    btc_w = (vol_cap / btc_vol).clip(upper=1.0).fillna(0.0)
    gold_w = (vol_cap / gold_vol).clip(upper=1.0).fillna(0.0)
    weight_raw[holding_raw == "btc"] = btc_w[holding_raw == "btc"]
    weight_raw[holding_raw == "gold"] = gold_w[holding_raw == "gold"]

    # Only update the held state / weight on rebalance days; hold prior
    # state on non-rebalance days (weekly-rebalance mechanic).
    holding_state = holding_raw.where(is_rebalance_day)
    holding_state = holding_state.ffill().fillna("cash")
    weight_state = weight_raw.where(is_rebalance_day)
    weight_state = weight_state.ffill().fillna(0.0)

    # Apply the decision made at a rebalance day's close starting the NEXT
    # trading day (avoid using today's own close-derived signal on today's
    # return).
    holding_applied = holding_state.shift(1).fillna("cash")
    weight_applied = weight_state.shift(1).fillna(0.0)

    strat_ret = pd.Series(0.0, index=df.index)
    is_btc = holding_applied == "btc"
    is_gold = holding_applied == "gold"
    strat_ret[is_btc] = btc_daily_ret[is_btc] * weight_applied[is_btc]
    strat_ret[is_gold] = gold_daily_ret[is_gold] * weight_applied[is_gold]

    position = (holding_applied != "cash").astype(int)
    return pd.DataFrame({"position": position, "returns": strat_ret}, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_weeks: int = 8,
    vol_cap: float = 0.20,
    vol_window_days: int = 60,
    rebalance_weekday: int = 2,
) -> pd.Series:
    result = _simulate(price_df, partner_symbol, lookback_weeks, vol_cap, vol_window_days, rebalance_weekday)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_weeks: int = 8,
    vol_cap: float = 0.20,
    vol_window_days: int = 60,
    rebalance_weekday: int = 2,
) -> pd.Series:
    result = _simulate(price_df, partner_symbol, lookback_weeks, vol_cap, vol_window_days, rebalance_weekday)
    return result["returns"]
