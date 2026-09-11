# Backtest Report: MADH (Moving Average Difference, Hann) Zero-Line Crossover

**Strategy file:** `strategies/2026-09-12_madh_zerocross_trend.py`
**Status:** REJECTED

## Hypothesis
John Ehlers' MAD oscillator (SMA(price,short)/SMA(price,long)-1)*100, with
each SMA fed a Hann-windowed FIR-filtered price series (MADH variant, TASC
Nov 2021 Traders' Tips), crossing above zero signals fresh short-term uptrend
acceleration. Gated by close > SMA(trend_window) to avoid whipsaws in a
downtrend. Exit on MADH crossing back below zero, trend filter breaking, or
a max_hold_days time-stop.

Sources:
- https://www.tradingview.com/scripts/tasc/page-4/ (TASC 2021.11 MADH overview)
- https://financial-hacker.com/the-mad-indicator/ (exact MAD/MADH Zorro/C formulas)

Default params per Ehlers' own article: short_len=8, long_len=23.

## Grid test summary (Step 6)
- Grid: short_len ∈ {8,10}, long_len ∈ {23,30}, trend_window ∈ {50,100};
  symbols QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3
  (low/mid/high realized-vol terciles).
- Total cells: 96, passed: 13, **pass_fraction = 0.135**
- By asset class: equity 13/48 passed, crypto 0/48 (decisive reject)
- By vol regime: low 13/32, mid 0/32, high 0/32 — edge exists only in
  low-vol tercile slices.
- Best cell: short_len=10, long_len=30, trend_window=50, QQQ, low-vol
  tercile, Sharpe=1.81
- Worst cell: short_len=10, long_len=23, trend_window=100, SPY, high-vol
  tercile, Sharpe=-0.74

## Single-config validation (Step 7), best grid config full-sample (2015-2026)
Params: short_len=10, long_len=30, trend_window=50, max_hold_days=20

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.89 FAIL | 0.48 FAIL |
| Max Drawdown (<=0.25) | 0.092 PASS | 0.109 PASS |
| TC survival (net Sharpe >=0.5, 10bps/trade) | 0.84 PASS (30 trades) | 0.40 FAIL (33 trades) |

`check_walk_forward` errored on an unrelated infra bug in
`validation/validators.py` (`vbt.utils.splitting.RangeSplitter` attribute
missing in the installed vectorbt version) — not evaluated this iteration;
noted for a future loop to fix the validator helper itself.

## Decision
**Reject.** The grid's best per-tercile cell (Sharpe 1.81, low-vol only) does
not hold up full-sample: QQQ and SPY both fail the Sharpe>=1.0 threshold when
tested over the entire 2015-2026 window with the same best-grid config, and
SPY additionally fails transaction-cost survival. Crypto is decisively
rejected (0/48 cells). Consistent with this cron trigger's broader pattern:
narrow low-vol-tercile-only edges rarely survive full-sample validation.
