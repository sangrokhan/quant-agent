# Backtest Report: Random Walk Index (RWI) Trend-Confirmation (2026-09-24)

**Strategy file:** `strategies/2026-09-24_rwi_trend_confirmation.py`
**Hypothesis source:** https://www.strike.money/technical-analysis/random-walk-index (visited 2026-09-24T11:01:00Z)

## Hypothesis
The Random Walk Index tests whether a price move over a lookback is
statistically distinguishable from a random walk's expected range
(ATR-normalized, sqrt(n)-scaled). RWI High crossing above a "strong trend"
threshold (1.0) while dominating RWI Low signals a genuine (non-random)
uptrend worth entering; exit when RWI High drops below the trend-initiation
floor (0.5) or RWI Low overtakes RWI High (reversal).

## Grid test summary (Step 6)
- Grid: `rwi_period` [10,14,20] x `entry_threshold` [0.8,1.0,1.2] x
  `max_hold_days` [15,20], symbols SPY/QQQ + BTC/USDT/ETH/USDT,
  vol_regime_splits=3.
- 216 total cells, 75 passed (pass_fraction = 0.347) -- broad, works
  across both asset classes.
- By asset class: equity 46/108 (0.426); crypto 29/108 (0.269).
- By vol regime: low 51/72 (0.708), mid 24/72 (0.333), high 0/72 (0.0).
- By symbol: QQQ 30/54 (0.556), SPY 16/54 (0.296), BTC/USDT 23/54 (0.426),
  ETH/USDT 6/54 (0.111).
- Best cell: QQQ, rwi_period=20/entry_threshold=1.2/max_hold_days=20,
  low-vol, Sharpe=2.848.

## Single-config validation (Step 7)

### QQQ: rwi_period=20, entry_threshold=1.2, max_hold_days=20
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.231 | >= 1.0 |
| Max drawdown | PASS | 0.190 | <= 0.25 |
| Transaction cost survival (80 trades) | PASS | net Sharpe 1.051 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.219 | <= 0.5 |

**All 5 pass for QQQ.**

### BTC/USDT: rwi_period=10, entry_threshold=1.2, max_hold_days=15
Initial validation (leverage_cap=1.0 implicit): Sharpe 1.472 PASS, MDD
0.333 **FAIL**, TC-survival PASS, walk-forward PASS, param-sensitivity
PASS. Leverage-cap rescue scan found leverage_cap=0.7 clears MDD:

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.472 | >= 1.0 |
| Max drawdown | PASS | 0.242 | <= 0.25 |
| Transaction cost survival (96 trades) | PASS | net Sharpe 1.381 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.155 | <= 0.5 |

**All 5 pass for BTC/USDT at leverage_cap=0.7.**

## Decision: ACCEPT (QQQ, all 5 validators pass at leverage_cap=1.0);
ACCEPT (BTC/USDT, all 5 validators pass at leverage_cap=0.7 rescue).
SPY/ETH/USDT not individually validated this iteration despite non-trivial
grid pass_fractions (0.296/0.111) -- flagged for future pursuit. High-vol
regime is a decisive 0/72 failure across the whole grid.
