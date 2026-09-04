# Backtest Report: Polarized Fractal Efficiency (PFE) Buy/Sell-Zone Crossover

**Strategy file:** `strategies/2026-09-05_pfe_buysell_zone_crossover.py`
**Knowledge base id:** 2026-09-05-014

## Hypothesis

Polarized Fractal Efficiency (PFE, Hannula 1994): a fractal-geometry
ratio of the straight-line (Euclidean) distance price traveled over N
bars versus the actual bar-to-bar path length, signed by trend direction
and EMA-smoothed. Per Omega Research's original 1997 EasyLanguage code,
StockSpotter's own threshold convention treats smoothed PFE crossing
above +50 ("BUYZONE") as a long entry and crossing below -50
("SELLZONE") as an exit signal.

Sources:
https://www.newtraderu.com/polarized-fractal-efficiency-pfe-backtest-strategy-trading-rules-returns/
(overview) and
https://www.multicharts.com/trading-software/index.php/Fractals_%3E_PFE_(Polarized_Fractal_Efficiency)
(exact original EasyLanguage formula + BUYZONE/SELLZONE thresholds).

First PFE strategy in this repo — a fractal-efficiency Euclidean-ratio
construction distinct from all prior oscillators.

## Grid test summary (Step 6)

- `param_grid`: `n` in {9, 14}, `buy_zone` in {40, 50}, `max_hold_days` in {20, 30} (sell_zone fixed at -50)
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3`
- Period: 2019-01-01 to 2026-09-01
- **96 total cells, 20 passed, pass_fraction = 0.208**
- By asset class: equity 20/48, crypto 0/48
- By vol regime: low 16/32, mid 4/32, high 0/32
- Best cell: n=9, buy_zone=40, max_hold_days=30, QQQ, low-vol, Sharpe 3.00
- QQQ's best consistent combo (n=14, buy_zone=50) passed 2/3 vol-regime cells

## Single best-config validators (Step 7)

Config: `n=14, buy_zone=50, sell_zone=-50, max_hold_days=20`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.738 | 0.117 | ≥ 1.0 | ❌ / ❌ |
| Max drawdown | 0.248 | 0.385 | ≤ 0.25 | QQQ ✅ (marginal) / SPY ❌ |
| Net Sharpe after costs (10bps/trade) | 0.680 | 0.062 | ≥ 0.5 | QQQ ✅ / SPY ❌ |
| Num trades | 40 | 43 | — | — |
| Parameter sensitivity (n x buy_zone sweep, QQQ, relative_std) | 0.148 | — | ≤ 0.5 | ✅ (not the failure mode here) |

`check_walk_forward` not run (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED**

Full-sample Sharpe decisively fails on both QQQ (0.738) and SPY (0.117)
against the 1.0 threshold, despite the grid's isolated low-vol-tercile
passes (best cell Sharpe 3.00). SPY additionally fails max drawdown
(0.385) and net-of-cost Sharpe. Not an overfitting problem (parameter
sensitivity is fine, relative_std 0.148) — same lesson as the Roofing
Filter iteration: a genuinely weak full-sample edge concentrated in the
low-vol regime. Crypto rejected decisively (0/48 grid cells).
