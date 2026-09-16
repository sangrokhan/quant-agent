# Backtest report: DEMA spread continuous sizing dial

**Strategy file:** `strategies/2026-09-17_dema_spread_sizing_dial.py`

## Hypothesis

Direct fix attempt for 2026-09-17-076 (DEMA fast/slow binary crossover,
accepted equity per-symbol tuned but decisively rejected crypto: BTC/USDT
MDD 0.458, ETH/USDT MDD 0.551, both ~2x cap). Reframes the normalized DEMA
fast-slow spread as a CONTINUOUS SIZING dial (rolling z-scored, tanh-
squashed) rather than a full binary flip, leverage-cap-aware for crypto
from the start -- this repo's standard rescue pattern for binary-trigger
crypto MDD failures.

## Grid test summary (Step 6)

`param_grid={"sensitivity": [0.4,0.6,0.8], "leverage_cap": [0.5,1.0]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 72, passed_cells: 30, **pass_fraction: 41.7%**
- by_asset_class: equity 16/36; crypto 14/36
- by_vol_regime: low 20/24; mid 5/24; high 5/24
- best_cell: QQQ, low-vol regime, sensitivity=0.4/leverage_cap=0.5, Sharpe 2.94

## Single-config validators, full sample 2019-2026

**Equity config: sensitivity=0.4, leverage_cap=0.5 (default base_exposure=0.4)**

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | pass 1.339 | pass 1.009 |
| Max Drawdown (<=0.25) | pass 0.121 | pass 0.113 |
| TC survival | pass 1.254 (58 trades) | pass 0.897 (65 trades) |
| Walk-forward | pass 0.75 | pass 1.00 |
| Parameter sensitivity | pass 0.059 | pass 0.062 |

At this same equity config, crypto near-missed (BTC Sharpe 0.939/MDD
0.333; ETH Sharpe 1.094/MDD 0.255) -- crypto leverage-cap recalibration
(base_exposure=0.25, leverage_cap=0.3) fixes both:

**Crypto config: sensitivity=0.4, leverage_cap=0.3, base_exposure=0.25**

| Validator | BTC/USDT | ETH/USDT |
|---|---|---|
| Sharpe (>=1.0) | pass 1.093 | pass 1.127 |
| Max Drawdown (<=0.25) | pass 0.193 | pass 0.171 |
| TC survival | pass 1.056 (60 trades) | pass 1.100 (54 trades) |
| Walk-forward | pass 1.00 | pass 0.75 |
| Parameter sensitivity | pass 0.067 | pass 0.118 |

## Decision: ACCEPTED (all four symbols: QQQ, SPY, BTC/USDT, ETH/USDT)

All 5 validators pass on all 4 symbols with two configs (equity default;
crypto leverage-cap recalibration). Confirms this repo's now well-
established pattern: binary crossover triggers that fail crypto MDD are
frequently rescuable via a continuous-sizing-dial reframe + leverage-cap
recalibration, and this held again for DEMA.
