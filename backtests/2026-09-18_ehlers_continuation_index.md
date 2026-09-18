# Ehlers Continuation Index (CI) Crossover — SPY accepted / QQQ+crypto rejected

**Date:** 2026-09-18
**Strategy file:** `strategies/2026-09-18_ehlers_continuation_index.py`
**Source:** [TASC Sept 2025 Traders' Tips — "The Continuation Index"](https://traders.com/Documentation/FEEDbk_docs/2025/09/TradersTips.html)
(John F. Ehlers). WealthLab's own disclosed mechanical rule: *"Buy when CI
crosses above -0.9. Sell when CI crosses below 0."*

## Hypothesis

CI is the variance-normalized, Inverse-Fisher-Transform-compressed
difference between `UltimateSmoother(close, length/2)` and an 8th-order
Laguerre filter (built atop `UltimateSmoother(close, length)`). When the
fast smoother pulls away from the laggier Laguerre filter, CI swings toward
+1 (trend onset/continuation); when they reconverge, CI reverts toward 0
(trend exhaustion). Default params from source: `gama=0.8, order=8,
length=40, buy_level=-0.9, sell_level=0.0`.

## Grid test summary (gama∈{0.4,0.8} × length∈{30,40,60} × buy_level∈{-0.9,-0.7}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- 144 cells, 50 passed (**34.7%**)
- by_asset_class: equity 44/72 (**61.1%**), crypto 6/72 (8.3%)
- by_vol_regime: low 30/48 (62.5%), mid 10/48 (20.8%), high 10/48 (20.8%)
- Best cell: `gama=0.8, length=40, buy_level=-0.9` (the source's own default
  params), QQQ low-vol, Sharpe=2.89
- Worst cell: `gama=0.4, length=30, buy_level=-0.7`, ETH/USDT high-vol,
  Sharpe=-0.59

## Single-config validators (full sample 2019-01-01–2026-09-01, default params)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| QQQ | 1.114 PASS | 30.5% **FAIL** (>25%) | 1.061 PASS | 0.75 PASS | 0.046 PASS | 50 |
| SPY | 1.010 PASS | 19.6% PASS | 0.943 PASS | 0.75 PASS | 0.025 PASS | 47 |

QQQ fails only on max-drawdown (30.5% vs the 25% threshold) — every other
validator passes decisively, including walk-forward and parameter
sensitivity (relative std ~4.6%, very stable across length=30/40/60).

## Decision

- **SPY: ACCEPT.** All 5 validators pass with the source's disclosed
  default parameters, no re-tuning needed.
- **QQQ: REJECT** (single-config MDD 30.5% > 25% threshold, despite passing
  grid-test in low/mid vol regimes and passing every other validator).
- **Crypto (BTC/USDT, ETH/USDT): REJECT.** Grid pass fraction only 8.3%
  (6/72 cells), no config found with acceptable Sharpe/MDD tradeoff broadly
  across vol regimes.

Strategy file is kept live in `strategies/` for SPY use; QQQ/crypto are
explicitly out of scope per the grid findings — a future iteration could
retune (e.g. widen buy_level or add a drawdown-based exit) to try to rescue
QQQ's MDD specifically, since every other QQQ validator already passes.
