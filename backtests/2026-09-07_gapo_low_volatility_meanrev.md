# Gopalakrishnan Range Index (GAPO) Low-Volatility Mean Reversion — Backtest Report

**Date:** 2026-09-07
**Strategy file:** `strategies/2026-09-07_gapo_low_volatility_meanrev.py`
**Source:** technicalresources.in, "Comprehensive Guide to Trading Strategies
Using Gopalakrishnan Range Index (GAPO)" (Dec 2024). Source's own "Strategy
2: Mean Reversion Strategy in Low Volatility Markets": "Low GAPO values
(below 0.3) indicate stability, which favors mean-reversion strategies...
Combine GAPO with oscillators like RSI or Stochastic to identify
overbought/oversold conditions... Exit when the price returns to the mean."

## Hypothesis
GAPO(gapo_window) < gapo_threshold (low-vol regime, Chande's log-fractal-
dimension volatility index) combined with RSI(rsi_window) <= rsi_oversold
signals a long mean-reversion entry; exit when close crosses back above its
own exit_sma_window-day SMA ("return to the mean") or a max_hold_days
time-stop.

## Grid test (Step 6)
`param_grid={"gapo_threshold": [0.25, 0.3, 0.35], "rsi_oversold": [15, 20, 25]}`
(gapo_window=20, rsi_window=3, exit_sma_window=10, max_hold_days=10 fixed),
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total: 5/108 pass (4.6%)**
- By asset class: equity 5/54 (9.3%), crypto 0/54 (0%)
- By vol regime: low 3/36 (8.3%), mid 1/36 (2.8%), high 1/36 (2.8%)
- Best cell: `gapo_threshold=0.35, rsi_oversold=25`, QQQ, low-vol tercile,
  Sharpe 2.01
- Worst cell: `gapo_threshold=0.3, rsi_oversold=15`, QQQ, mid-vol tercile,
  Sharpe -1.04

## Single-config validation (Step 7), best grid config `gapo_threshold=0.35, rsi_oversold=25`

| Symbol | Sharpe | Threshold | Pass | MDD | Threshold | Pass | TC net Sharpe | Threshold | Pass | Param sensitivity (rel std) | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 0.443 | 1.0 | No | 0.251 | 0.25 | No | 0.405 | 0.5 | No | 0.076 | Yes |
| SPY | 0.313 | 1.0 | No | 0.188 | 0.25 | Yes | 0.281 | 0.5 | No | 3.445 | No |

Walk-forward: skipped (repo-wide pre-existing tooling bug,
`vectorbt.utils.splitting` missing).

## Decision: REJECTED

Full-sample Sharpe fails decisively on both QQQ (0.443) and SPY (0.313),
both well below the 1.0 threshold. QQQ also fails max-drawdown (0.251 just
over the 0.25 cap) and transaction-cost survival; SPY fails
parameter-sensitivity (relative std 3.44, Sharpe flips from positive to
near-zero across gapo_threshold 0.25/0.3/0.35 — the strategy's edge is not
robust to this parameter). The grid's apparent 9.3% equity pass rate is
concentrated entirely in the low-vol tercile with a single standout QQQ
cell (Sharpe 2.01) — not a broadly reproducible edge; full-sample results
do not confirm the source's regime-specific claim once combined across the
whole test window. Crypto rejected decisively (0/54 grid cells) — the
24/7/no-overnight-gap crypto price structure appears to make GAPO's
range-envelope construction behave very differently than on equities'
gapped daily bars.
