# Chaikin Volatility trough-reversal + SMA trend filter — backtest report

**Strategy file:** `strategies/2026-09-04_chaikin_volatility_trough_reversal.py`
**Hypothesis id:** 2026-09-04-133

## Hypothesis

Marc Chaikin's Volatility indicator (CV): percentage rate-of-change of an
EMA-smoothed high-low range. Per
[trendspider.com](https://trendspider.com/learning-center/chaikin-volatility/):
"a trader might enter a long position when the indicator rises from a low
value... exit... when the indicator begins to fall from a high value."
Since CV carries no directional signal on its own, combined with a
directional SMA trend filter (source community's own recommendation to
"always pair with a directional indicator for entry"): long entry when CV
is near a trailing 60-day low and turns up, AND close is above a 50/100-day
SMA; exit when CV is near a trailing high and turns down, or a
max_hold_days time-stop.

Source: https://trendspider.com/learning-center/chaikin-volatility/ (via
browser_exec Google-search fallback).

## Grid summary (Step 6)

`pctile_threshold` in {15,20} x `trend_window` in {50,100} x
`max_hold_days` in {10,15}, symbols QQQ/SPY/BTC/USDT/ETH/USDT,
vol_regime_splits=3:

- 96 cells total, 13 passed (pass_fraction=0.135)
- by_asset_class: equity 13/48, crypto 0/48
- by_vol_regime: low 13/32, mid 0/32, high 0/32 (only low-vol cells pass at all)
- best_cell: pctile_threshold=20, trend_window=50, max_hold_days=10, QQQ, low-vol, Sharpe=1.99
- worst_cell: pctile_threshold=20, trend_window=100, max_hold_days=10, QQQ, mid-vol, Sharpe=-1.20

## Primary config validators (pctile_threshold=20, trend_window=50, max_hold_days=10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | -0.056 **FAIL** | 0.266 **FAIL** |
| Max drawdown (<=0.25) | 0.230 PASS | 0.152 PASS |
| Net Sharpe after costs (>=0.5, 10bps/trade) | -0.127 **FAIL** (37 trades) | 0.167 **FAIL** (43 trades) |

Walk-forward/parameter-sensitivity skipped given decisive Sharpe/TC
failure on both symbols and the strategy passing ONLY in the low-vol
regime (0/32 in both mid and high vol).

## Decision

**Reject (both QQQ and SPY).** Full-sample Sharpe fails decisively on
both (negative on QQQ), and net-of-cost Sharpe fails both. Crypto
rejected outright (0/48 grid cells). The grid's exclusively-low-vol
pass pattern (13/32 low, 0/32 mid, 0/32 high) mirrors this log's most
common rejection signature: an attractive best-cell figure that is
purely a low-volatility-regime artifact, not a broadly robust edge.
