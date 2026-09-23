# Backtest Report: WAD (Williams Accumulation/Distribution) Divergence Swing-Breakout (2026-09-24)

**Strategy file:** `strategies/2026-09-24_wad_divergence_swing_breakout.py`
**Hypothesis source:** https://help.ctrader.com/indicators/built-in/other/williams-accumulation-distribution (visited 2026-09-24T10:15:00Z)

## Hypothesis
WAD (Larry Williams) is a purely price-derived cumulative accumulation/
distribution measure (no volume term, using prior-close-referenced true
high/low). Bullish divergence (price lower low, WAD higher low) triggers a
long entry on a confirmed breakout above the intervening swing high, with
an ATR stop and 2R target -- reusing this repo's established OBV-divergence
swing-breakout construction (2026-09-23-030) applied to WAD for the first
time.

## Grid test summary (Step 6)
- Grid: `swing_window` [3,5,8] x `reward_risk` [1.5,2.0,3.0] x
  `max_hold_bars` [15,25], symbols SPY/QQQ + BTC/USDT/ETH/USDT,
  vol_regime_splits=3.
- 216 total cells, 31 passed (pass_fraction = 0.144) -- notably weaker than
  this iteration's other candidates.
- By asset class: equity 21/108 (0.194); crypto 10/108 (0.093).
- By symbol: QQQ 8/54 (0.148), SPY 13/54 (0.241), BTC/USDT 4/54 (0.074),
  ETH/USDT 6/54 (0.111).
- Best cell: SPY, swing_window=3/reward_risk=1.5/max_hold_bars=15,
  high-vol, Sharpe=1.645.

## Single-config validation (Step 7): SPY, swing_window=3, reward_risk=1.5, max_hold_bars=15
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS (barely) | 1.001 | >= 1.0 |
| Max drawdown | PASS | 0.020 | <= 0.25 |
| Transaction cost survival (8 trades) | PASS | net Sharpe 0.941 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.404 | <= 0.5 |

All 5 validators nominally pass, but **only 8 trades over the full
2019-2026 sample** (~7.7 years) -- a sample size too thin to trust
(this divergence-swing-breakout setup is rare by construction: it requires
a specific 2-swing-low WAD divergence AND a subsequent confirmed breakout).
Per this repo's established precedent (2026-09-10-018 Bitcoin Rainbow
rejection for 2-5 trades despite nominal Sharpe>1.0), a strategy validated
on single-digit trade counts cannot be trusted regardless of nominal
validator pass status -- the Sharpe/walk-forward/param-sensitivity
statistics are not meaningfully estimated from so few independent events.

## Decision: REJECT (SPY: nominal all-5-pass but only 8 trades, insufficient
sample per repo precedent; QQQ/BTC/ETH grid pass_fractions weaker still,
0.074-0.148, not pursued). Overall grid pass_fraction (0.144) also
decisively weaker than this iteration's other 5 candidates, consistent
with the low-frequency-signal concern.
