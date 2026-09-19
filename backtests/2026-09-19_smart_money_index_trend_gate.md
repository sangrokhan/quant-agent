# Smart Money Index (SMI) Trend-Confirmation Gate — REJECTED (near-miss, both IWM and ETH)

**Hypothesis:** Per Grokipedia's "Smart Money Index" page
(https://grokipedia.com/page/Smart_money_index), the Smart Money Index
(SMI, Lynn Elgert 1988 / Don Hays 1990s) is a cumulative price-based
sentiment index: Today's SMI = Yesterday's SMI - (gain/loss in the first
30 min) + (gain/loss in the last hour), on the theory that retail ("dumb
money") trades near the open and institutions ("smart money") trade near
the close. Adapted to 1h bars (first-hour replaces first-30-min, ~2yr
data history via data/loaders.py) as a trend-confirmation gate: long the
primary asset only while its own price is in an uptrend AND the SMI
itself is above its own trailing SMA (smart-money flow confirms the
uptrend). Distinct from this same cron trigger's earlier first-hour/
last-hour SIGN-PREDICTION strategy (2026-09-19-054, which trades the SAME
day's last-hour return conditioned on that day's own first-hour sign) —
SMI is a CUMULATIVE multi-day running index used here as a trend filter,
not a same-day directional bet. Also distinct from the already-tested
Fosback/Dysart Negative Volume Index (2026-09-04-139/2026-09-14-131),
which is volume-based.

## Step 6 — Grid test summary

Grid: `trend_window` in {50,100} x `smi_window` in {10,20,30}, symbols
equity={SPY,IWM} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3
(~700-day lookback constrained by 1h-bar history availability). 72 total
cells.

- `pass_fraction`: 23/72 = **0.319** (second-strongest grid result of
  this cron trigger's 6 iterations so far, after Dual-KAMA's 0.347)
- `by_asset_class`: equity 13/36 passed, crypto 10/36 passed (both
  reasonably represented, unlike prior narrow-artifact iterations)
- `by_vol_regime`: low 8/24, mid 12/24, high 3/24 (spans all three
  regimes, strongest in mid-vol)
- `best_cell`: SPY, trend_window=50, smi_window=10, low-vol regime,
  Sharpe=2.65
- `worst_cell`: SPY, trend_window=50, smi_window=20, mid-vol regime,
  Sharpe=-3.03 (SPY at smi_window=20/30 was consistently poor full-sample
  too, see below — this config only works at smi_window=10)

## Step 7 — Single-config validation (full sample, ~700-day window)

### IWM, trend_window=100, smi_window=10

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.108 | >= 1.0 | pass |
| Max drawdown | 0.089 | <= 0.25 | pass |
| Tx-cost survival (5bps/trade, 60 trades) | net Sharpe 0.909 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | pass_fraction 0.5 | >= 0.75 | **FAIL** (splits 1-2 positive, 3-4 negative) |
| Parameter sensitivity (6-cell sweep) | relative_std 0.323 | <= 0.5 | pass |

### ETH/USDT, trend_window=50, smi_window=20

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.221 | >= 1.0 | pass |
| Max drawdown | 0.146 | <= 0.25 | pass |
| Tx-cost survival (5bps/trade, 39 trades) | net Sharpe 1.184 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | pass_fraction 0.5 | >= 0.75 | **FAIL** (splits 1,3 negative; 2,4 positive) |
| Parameter sensitivity (6-cell sweep) | relative_std 0.215 | <= 0.5 | pass |

Both configs are genuine near-misses: 4 of 5 validators pass cleanly
(Sharpe well above 1.0, tight drawdowns, tx-cost-robust, low parameter
sensitivity), but BOTH fail walk-forward identically at exactly 0.5 (2 of
4 chronological splits positive, 2 negative) -- suggesting the edge is
real but not stable across all sub-periods of the ~2-year sample
available (a longer lookback would help distinguish "genuinely
regime-dependent" from "insufficient walk-forward granularity", but 1h
bars are capped at ~2yr by yfinance).

## Decision: REJECTED (near-miss on both accepted-candidate configs;
walk-forward is the sole blocker)

Per this repo's all-validators-must-pass criterion, both configs are
rejected. This is flagged as a strong near-miss candidate for a future
loop to revisit: (a) test more/finer walk-forward splits to see if the
2/4 pattern is a genuine regime split (e.g. specific sub-period like a
2024 vs 2025 divergence) that could be explicitly gated on, or (b) retest
once a longer 1h-bar history window becomes available (yfinance's ~2yr
cap is the binding constraint here, not the strategy's own design).
Strategy file kept in `strategies/` as a record (not live) but flagged as
a near-miss worth revisiting, not a dead end -- similar treatment to
2026-09-19-054 earlier this trigger.
