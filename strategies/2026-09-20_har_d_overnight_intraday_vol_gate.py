"""Strategy: HAR-D (Heterogeneous Autoregressive, overnight/intraday
Decomposed) realized-variance forecast, long/flat vol-threshold gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-100):
Per a Rutgers MQF student project (Annigeri/Aryan/Raya/Hemanth, "Overnight
vs Intraday Volatility", https://github.com/zaid282802/HAR-Overnight-Intraday-Vol,
read this iteration): splitting each day's realized variance into an
OVERNIGHT component (close[t-1]->open[t]) and an INTRADAY component
(open[t]->close[t]), then fitting Corsi's classic HAR (Heterogeneous
Autoregressive) model separately on each component's own daily/weekly/
monthly lag structure (HAR-D, "decomposed"), out-forecasts a single pooled
HAR-RV model fit on total daily realized variance alone (source's own
disclosed result: HAR-D beats HAR-RV on out-of-sample QLIKE on all 5 tested
tickers). The source's own disclosed trading rule: go long the underlying
when the HAR-D model's one-day-ahead forecast annualized volatility falls
below a fixed threshold (20% in the source), else hold cash; source's own
backtest result on SPY: HAR-D-gated Sharpe 0.77 / MDD -16.8% vs raw
buy-and-hold Sharpe 0.84 / MDD -24.2% (materially better risk-adjusted
drawdown control, if a lower absolute Sharpe).

This is the first HAR/Corsi-family volatility-forecasting strategy in this
repo (Stage-1 index search this iteration found zero prior "HAR model" /
"Corsi" / "HAR-RV" entries) -- distinct from this repo's many existing
realized-vol-PERCENTILE or GARCH/EGARCH regime gates (which use raw
rolling-window realized vol or a fitted conditional-heteroskedasticity
model, not the HAR term-structure-of-lags regression specifically, and none
decompose overnight vs. intraday components).

Implementation notes (adapted to this repo's data/loaders.py OHLC-only,
single-symbol architecture, simplified vs. the source's full walk-forward
setup for tractability within one loop iteration):
- overnight_var[t] = log(open[t]/close[t-1])^2
- intraday_var[t]  = log(close[t]/open[t])^2
- HAR-D features per component: lag1 (yesterday's value), meanlag5 (mean of
  the trailing 5 days), meanlag22 (mean of the trailing 22 days) -- 6
  features total (3 per component) regressing next-day TOTAL realized
  variance (overnight_var + intraday_var), via OLS (numpy.linalg.lstsq),
  refit every ``refit_every`` trading days on an EXPANDING window (all data
  up to the refit point), forecasting forward until the next refit --
  same walk-forward-refit spirit as the source, simplified to a fixed
  refit cadence rather than the source's exact 20-day expanding-window
  schedule (which this repo's grid-test harness cannot easily replicate
  cell-by-cell without a much heavier custom loop).
- Position: long (1) while forecast annualized vol (sqrt(forecast_daily_var
  * 252)) <= vol_threshold, else flat (0) -- source's own disclosed rule,
  no hysteresis band (matching the source exactly, distinct from this
  repo's many hysteresis-gated regime strategies).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _har_features(var_series: pd.Series) -> pd.DataFrame:
    lag1 = var_series.shift(1)
    mean5 = var_series.shift(1).rolling(5).mean()
    mean22 = var_series.shift(1).rolling(22).mean()
    return pd.DataFrame({"lag1": lag1, "mean5": mean5, "mean22": mean22})


def _har_d_forecast(
    df: pd.DataFrame,
    min_train: int = 250,
    refit_every: int = 20,
) -> pd.Series:
    """Walk-forward (expanding-window, periodic-refit) HAR-D one-day-ahead
    total-realized-variance forecast."""
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close.shift(1)

    overnight_var = np.log(open_ / close.shift(1)).clip(-1, 1) ** 2
    intraday_var = np.log(close / open_).clip(-1, 1) ** 2
    total_var = overnight_var + intraday_var

    feat_on = _har_features(overnight_var)
    feat_in = _har_features(intraday_var)
    feats = pd.concat(
        [feat_on.add_suffix("_on"), feat_in.add_suffix("_in")], axis=1
    )
    feats["const"] = 1.0

    n = len(df)
    forecast = pd.Series(np.nan, index=df.index)
    if n < min_train + 5:
        return forecast

    coefs = None
    for t in range(min_train, n):
        if coefs is None or (t - min_train) % refit_every == 0:
            train_idx = range(0, t)
            X_train = feats.iloc[list(train_idx)].values
            y_train = total_var.iloc[list(train_idx)].values
            valid = ~np.isnan(X_train).any(axis=1) & ~np.isnan(y_train)
            if valid.sum() > feats.shape[1] + 5:
                try:
                    coefs, *_ = np.linalg.lstsq(X_train[valid], y_train[valid], rcond=None)
                except Exception:
                    coefs = None
        if coefs is not None:
            x_t = feats.iloc[t].values
            if not np.isnan(x_t).any():
                forecast.iloc[t] = max(float(x_t @ coefs), 0.0)
    return forecast


def generate_signals(
    price_df: pd.DataFrame,
    vol_threshold: float = 0.20,
    min_train: int = 250,
    refit_every: int = 20,
) -> pd.Series:
    """Long (1) while HAR-D forecast annualized vol <= vol_threshold, else flat (0)."""
    df = _prep(price_df)
    forecast_var = _har_d_forecast(df, min_train=min_train, refit_every=refit_every)
    forecast_annual_vol = np.sqrt(forecast_var * 252.0)
    position = (forecast_annual_vol <= vol_threshold).astype(int)
    position = position.where(~forecast_annual_vol.isna(), 0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
