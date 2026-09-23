# Backtest Report: McGinley Dynamic Price-Crossover + RSI>50 (2026-09-24)

**Strategy file:** `strategies/2026-09-24_mcginley_dynamic_crossover.py`
**Hypothesis source:** https://www.angelone.in/knowledge-center/online-share-trading/mcginley-dynamic-indicator (visited 2026-09-24T09:10:00Z)

## Hypothesis
The McGinley Dynamic (John R. McGinley, 1997) is an adaptive moving average
whose smoothing speed self-adjusts via a 4th-power price-divergence ratio,
reacting faster during trends and slower during consolidation than a
fixed-period SMA/EMA. Per the source's Price-Crossover + RSI composite
rule: buy on a confirmed crossover of price above the MD line with RSI>50
momentum confirmation; exit when price closes decisively back below the
MD line.

## Grid test summary (Step 6)
- Grid: `md_period` [14,20,30] x `rsi_threshold` [45,50,55] x
  `max_hold_days` [15,20], symbols SPY/QQQ (equity) + BTC/USDT/ETH/USDT
  (crypto), vol_regime_splits=3.
- 216 total cells, 73 passed (pass_fraction = 0.338).
- By asset class: equity 55/108 (0.509); crypto 18/108 (0.167).
- By vol regime: low 54/72 (0.75), mid 17/72 (0.236), high 2/72 (0.028).
- By symbol: QQQ 35/54 (0.648), SPY 20/54 (0.370), BTC/USDT 18/54 (0.333),
  ETH/USDT 0/54 (0.0) -- ETH decisively fails at all tested configs.
- Best cell: QQQ, md_period=30/rsi_threshold=55/max_hold_days=15, low-vol,
  Sharpe=2.833.

## Single-config validation (Step 7)

### QQQ: md_period=30, rsi_threshold=55, max_hold_days=15
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.424 | >= 1.0 |
| Max drawdown | PASS | 0.180 | <= 0.25 |
| Transaction cost survival (186 trades) | PASS | net Sharpe 1.096 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.115 | <= 0.5 |

### SPY: md_period=30, rsi_threshold=50, max_hold_days=15
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.029 | >= 1.0 |
| Max drawdown | PASS | 0.183 | <= 0.25 |
| Transaction cost survival (233 trades) | PASS | net Sharpe 0.545 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 pass_fraction (3/4 positive) | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.174 | <= 0.5 |

Both equity symbols pass all 5 validators (SPY passes narrowly on Sharpe/
TC-survival/walk-forward).

## Decision: ACCEPT (equity: QQQ and SPY, both all 5 validators pass);
crypto out of scope (ETH/USDT 0/54 grid cells decisively fail; BTC/USDT
grid pass_fraction 0.333, not individually pursued this iteration).
