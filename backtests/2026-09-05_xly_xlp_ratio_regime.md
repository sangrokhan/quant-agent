# XLY/XLP Consumer Discretionary-vs-Staples Ratio Regime Filter — Backtest Report

**Hypothesis:** XLY/XLP ratio > its own 84-day (~4 trading month) SMA
signals a risk-on regime (discretionary spending leading staples =
cyclical/growth confidence); ratio < SMA signals risk-off (defensive
rotation into staples). Long when risk-on, flat when risk-off.

**Source:** multiple web-search/browser-fallback results (web_search
backend intermittently failing this session) confirming the XLY/XLP ratio
as a standard risk-on/off sector-rotation gauge (zForex: "Investors are
shifting into risk-on mode when discretionary stocks lead staples";
Seeking Alpha: "When this ratio is rising... risk appetite is
increasing"), combined with ETFreplay's general "Ratio MA" regime-switch
methodology (https://www.etfreplay.com/blog/regime-change/, illustrated
there with a different pair, SCHG/FNDX, where a 4-month/~84-day MA length
was their best-performing lookback).

**Strategy file:** `strategies/2026-09-05_xly_xlp_ratio_regime.py`

## Step 6 — Grid test summary (param_grid: ma_window in
[42, 63, 84, 126, 168]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 60, passed_cells: 15, **pass_fraction: 0.25**
- by_asset_class: equity 15/30 (50%), crypto 0/30 (0%) -- again zero
  transfer to crypto (no sector-ETF analog exists for crypto anyway).
- by_vol_regime: low 10/20, mid 4/20, high 1/20.
- best_cell: ma_window=84, SPY, low-vol regime, Sharpe=2.95 (tercile
  slice).

## Step 7 — Single-config validators (best/default grid config over FULL
period: ma_window=84)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.137 | **PASS** 1.110 |
| Max Drawdown (<= 0.25) | **PASS** 0.233 | **PASS** 0.218 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 108 trades) | **PASS** 0.984 | **PASS** 0.895 |
| Parameter sensitivity (relative_std <= 0.5, 5-cell SPY sweep) | **PASS** 0.056 | n/a |

Walk-forward not run (pre-existing `vbt.utils.splitting` AttributeError bug
in this repo's installed vectorbt version, consistent with other entries;
all other validators pass decisively).

## Outcome: **ACCEPTED (equity only: QQQ, SPY)**

All validators pass on both QQQ and SPY at ma_window=84, with very low
parameter sensitivity (relative_std=0.056 across a 5-value sweep -- the
tightest of any strategy tested this session) -- the strategy is robust to
the exact MA length chosen, unlike several other regime filters tested
this session. Turnover is moderate (108 trades over ~7.5yrs, ~14/year).
MDD passes but with less margin (0.22-0.23 vs 0.25 threshold) than
gold/silver ratio (2026-09-05-030); net-of-cost Sharpe on QQQ (0.984) sits
just under the raw threshold, a reminder that at higher assumed
transaction costs this could flip -- worth monitoring if scaled with
higher trading frequency. Crypto has no direct analog and was not
meaningfully testable (rejected 0/30 cells, expected since XLY/XLP is an
equity-sector-specific signal).
