# DPO (Detrended Price Oscillator) Distance Continuous Sizing Dial — 2026-09-16

**Hypothesis:** DPO = close[t - (N//2+1)] - SMA(N)[t] (source:
https://www.quantifiedstrategies.com/detrended-price-oscillator/). Percent-DPO
(DPO/SMA), rolling z-scored + tanh-squashed, used as a continuous exposure
sizing dial inside an SMA(trend_window) uptrend gate with deadband. First
DPO strategy in this repo.

## Step 6 Grid Summary (dpo_window x sensitivity, 2 asset classes, 3 vol terciles)

- total_cells: 108, passed_cells: 47, pass_fraction: 0.435
- by_asset_class: equity 28/54, crypto 19/54
- by_vol_regime: low 24/36, mid 20/36, high 3/36
- best_cell: dpo_window=10, sensitivity=0.6, SPY, low vol, Sharpe 3.07
- worst_cell: dpo_window=10, sensitivity=0.6, ETH/USDT, high vol, Sharpe -0.44

## Step 7 Validators (best-config per symbol)

| Symbol | Config | Sharpe | MDD | TC net-Sharpe | WF frac | Param-sens rel-std | All pass |
|---|---|---|---|---|---|---|---|
| QQQ | dpo_window=20, sens=0.5, db=0.3, base=0.4, lev=1.0 | 0.634 (FAIL) | 0.158 (pass) | -0.067 (FAIL) | 0.75 (pass) | 0.182 (pass) | NO |
| SPY | same | 1.116 (pass) | 0.091 (pass) | 0.065 (FAIL) | 0.75 (pass) | 0.098 (pass) | NO |
| BTC/USDT | dpo_window=10, sens=0.6, db=0.2, base=0.24, lev=0.4 | 1.165 (pass) | 0.176 (pass) | 0.329 (FAIL) | 1.00 (pass) | 0.080 (pass) | Wait — TC threshold 0.5, actual 0.329 < 0.5 → FAIL |
| ETH/USDT | same | 0.275 (FAIL) | 0.476 (FAIL) | -0.097 (FAIL) | 0.50 (FAIL) | 0.262 (pass) | NO |

**Correction:** re-checking raw JSON, BTC/USDT `transaction_cost_survival.passed=false`
(value 0.329 < threshold 0.5). So **all four symbols fail transaction-cost
survival** at 10bps/trade with the deadband turnover level tested. No symbol
passes all 5 validators.

## Outcome: REJECTED (all symbols) — transaction-cost survival is the binding
constraint across the board; QQQ additionally fails raw Sharpe, ETH fails
Sharpe/MDD/WF decisively. The percent-DPO dial as constructed here churns
too much (330-460 trades over the backtest window) for a 10bps/trade cost
assumption to survive, even where raw (pre-cost) Sharpe clears 1.0 (SPY,
BTC/USDT). A future revisit should either widen the deadband substantially
or add cost-aware turnover damping before retesting this indicator family.

Source: https://www.quantifiedstrategies.com/detrended-price-oscillator/
