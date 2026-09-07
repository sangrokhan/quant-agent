# 2026-09-08 Kase Peak Oscillator Contrarian Reversal (QQQ) — REJECTED

**Hypothesis:** Cynthia Kase's Peak Oscillator (KPO), per the exact
PRT/MT4-derived formula at
https://www.prorealcode.com/prorealtime-indicators/kase-peak-oscillator-v2/,
produces a volatility-normalized "peak-out" event when a dual
max-over-lookback-range statistic (log(High/Low)/sqrt(k), scanned k=8..64
bars forward- and backward-looking) exceeds an adaptive deviation band. For
a long-only implementation (SAFETY.md), a NEGATIVE peak-out (bearish
momentum statistically exhausted) is read as a contrarian buy signal; a
POSITIVE peak-out (bullish momentum exhausted) triggers exit, with a
`max_hold_days` time-stop as a backstop.

Source: https://www.prorealcode.com/prorealtime-indicators/kase-peak-oscillator-v2/
(full ProRealTime source code transcription of the MT4-ported KPO v2
indicator). First Kase Peak Oscillator strategy in this repo.

## Grid test (Step 6)

`param_grid = {sensitivity: [30, 40, 50], max_hold_days: [5, 10]}`,
`symbols = {equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Overall pass fraction: 6/72 (8.3%)**
- By asset class: equity 6/36, crypto 0/36 (decisive crypto rejection)
- By vol regime: low 0/24, mid 4/24, high 2/24
- Best cell: QQQ, mid-vol, `sensitivity=40, max_hold_days=10`, Sharpe 1.756
- Worst cell: SPY, high-vol, `sensitivity=40, max_hold_days=5`, Sharpe -0.471

## Single-config validators (Step 7): QQQ, sensitivity=40, max_hold_days=10, full sample 2019-2026

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ FAIL | 0.886 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 8.77% | ≤ 25% |
| Transaction cost survival (10bps/trade, 5 trades) | ✅ PASS | net Sharpe 0.868 | ≥ 0.5 |
| Walk-forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` unavailable in this install, consistent with prior entries) | ✅ PASS | 3/4 splits positive (75%) | ≥ 75% |
| Parameter sensitivity (6-point sweep: sensitivity×max_hold_days) | ❌ FAIL | relative_std 0.665 | ≤ 0.5 |

Only 5 trades over the full ~7.7yr QQQ sample — the negative-peak-out entry
condition (requiring the oscillator to exceed an adaptive ±90-floor
deviation band) is rare and highly parameter-sensitive, matching the grid's
low mid-vol-only, equity-only pass pattern.

## Decision: REJECTED

Full-sample Sharpe misses (0.886 < 1.0) and parameter sensitivity is
decisively outside tolerance (0.665 vs 0.5 threshold) despite MDD/TC/WF all
passing — a near-miss on Sharpe but a genuine fragility issue on parameter
sensitivity given how few trades the peak-out condition produces. Crypto is
rejected decisively (0/36). Equity mid/high-vol slices show promise (best
single cell Sharpe 1.76) but the overall config does not hold up broadly
enough to accept. Left in `strategies/` as a rejected record.
