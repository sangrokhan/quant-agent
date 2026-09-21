# 2026-09-22 — Variance-Changepoint Trend Kill-Switch (SMA trend + BOCPD-inspired proxy)

**Source:** https://www.quantbeckman.com/p/with-code-switch-off-bayesian-online
("[WITH CODE] Switch-Off: Bayesian online changepoint detection" — a
probabilistic de-allocation framework distinguishing stochastic-noise
drawdowns from structural regime decay)

**Hypothesis:** Layer a variance-ratio changepoint "kill switch" on top of a
simple SMA trend-following base signal: go flat (override the trend signal)
when short-window realized variance spikes well above its typical
relationship to long-window variance (z-scored vs its own trailing
history), for a fixed cooldown period, then resume trend-following. This is
a simplified proxy for the source's full Bayesian online changepoint
detection (BOCPD) machinery, which requires a dedicated recursive
run-length posterior not reimplementable in one iteration.

## Grid test (Step 6)

`cp_threshold` in [1.5, 2.0, 2.5] x `cooldown_days` in [5, 10, 20],
symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto), vol_regime_splits=3,
2018-01-01 to 2026-09-01. 108 total cells.

- pass_fraction: 0.333 (36/108)
- by_asset_class: equity 27/54, crypto 9/54 (some structure, not decisive
  reject unlike most prior crypto attempts)
- by_vol_regime: low 27/36, mid 9/36, high 0/36 (kill-switch protects
  during low/mid-vol but the strategy still fails outright in high-vol
  regimes — consistent with expectations, a kill-switch reduces but doesn't
  eliminate high-vol pain)
- best_cell: QQQ, cp_threshold=2.5/cooldown_days=10, low-vol regime, Sharpe
  2.688
- Best average equity config: cp_threshold=2.5, cooldown_days=5 (mean
  Sharpe 1.18 across 6 equity cells)
- Crypto also shows decent average Sharpes (~1.1-1.2) at several configs
  (e.g. cp_threshold=2.0/cooldown_days=20 mean 1.223), unusual for this
  repo where crypto is almost always decisively rejected — worth a
  dedicated crypto-tuned follow-up iteration.

## Single-config validators (Step 7): cp_threshold=2.5, cooldown_days=5

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.081 PASS | 0.970 **FAIL** |
| Max drawdown (<=0.25) | 0.189 PASS | 0.212 PASS |
| TC survival (net Sharpe >=0.5, 10bps, 134/133 trades) | 0.900 PASS | 0.730 PASS |
| Walk-forward (4-split, >=0.75 pass) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (relative_std <=0.5) | 0.050 PASS | 0.778 **FAIL** |

## Decision: ACCEPTED for QQQ only; SPY rejected (near-miss)

QQQ passes all 5 validators cleanly, including a very low parameter
sensitivity (0.050 — Sharpe is remarkably stable across the cp_threshold/
cooldown_days grid, all clustering around ~1.1-1.2). SPY narrowly fails
Sharpe (0.970 vs 1.0) and fails parameter sensitivity (0.778) — the SPY
Sharpe varies more across the grid than QQQ's.

**Strategy file kept live** (accepted for QQQ). SPY is out of scope for this
config; a future loop could retune cp_threshold/cooldown_days specifically
for SPY following this repo's per-symbol-retune pattern (e.g. the CUSUM
QQQ/SPY retune precedent, ids 2026-09-10-072/075).

**Note for future loops:** crypto (BTC/ETH) showed unusually strong average
Sharpes (~1.1-1.2) at several parameter configs despite only 9/54 grid
cells passing outright — this is atypical for this repo (crypto is almost
always decisively 0/N rejected) and worth a dedicated crypto-focused
follow-up validating cp_threshold=2.0/cooldown_days=20 or similar directly
on BTC/USDT and ETH/USDT full-sample.
