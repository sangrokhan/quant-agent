# Backtest Report: 3-Horizon Composite Momentum Absolute Gate (QQQ)

**Strategy file:** `strategies/2026-09-22_composite_momentum_absolute_gate.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-040

## Hypothesis

Per Travis Giffin's description of the AllocateSmartly "Optimum 3" TAA model
mechanics (https://travisgiffin.com/my-allocatesmartly-tactical-asset-allocation-2025-2026/,
read via browser_exec since web_extract's DDGS backend cannot fetch article
bodies): `Score = w1*Return(3mo) + w2*Return(6mo) + w3*Return(12mo)`; go long
when Score > 0, cash otherwise. Monthly rebalance. Implemented as a
3-horizon (63d/126d/252d) weighted-blend absolute-momentum single-asset
gate, rebalanced every 21 trading days.

## Grid Test Summary (Step 6)

- Total cells: 48 (2 params x 2 values + fixed rebalance_days, 3 vol
  regimes, 4 symbols: QQQ/SPY equity, BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.25 (12/48)
- By asset class: equity 12/24 passed, crypto 0/24 passed
- By vol regime: low 8/16, mid 4/16, high 0/16 -- edge concentrated in
  low-vol regimes, decays in high-vol
- Best cell: QQQ, w3=0.5/w12=2.0, low-vol regime, Sharpe 2.42
- Worst cell: SPY, w3=0.5/w12=2.0, mid-vol regime, Sharpe -0.037

## Single-Config Validation (Step 7), QQQ, w3=0.5/w6=1.0/w12=2.0, rebalance_days=21

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | true | 1.005 | 1.0 |
| Max drawdown | **false** | 0.286 | 0.25 |
| Transaction cost survival (10bps/trade, 5 trades) | true | net Sharpe 1.001 | 0.5 |
| Walk-forward (manual 4-equal-slice, vectorbt splitter API unavailable) | true | 4/4 splits positive (1.10, 0.18, 2.01, 1.10) | 0.75 |
| Parameter sensitivity | true | relative std 0.055 | 0.5 |

## Outcome: REJECTED

Full-sample Sharpe just clears the 1.0 bar (1.005) but max drawdown (0.286)
decisively fails the 0.25 threshold -- consistent with this being an
unconditional trend/cash switch with no dedicated crash-brake mechanism
(unlike 2026-09-22-038's TSMOM+stop-loss rescue). A future iteration could
attempt the same "add a faster daily-reacting stop-loss overlay" rescue
pattern used successfully for 2026-09-22-037/038.
