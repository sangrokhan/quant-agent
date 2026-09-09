# SMA(10/100) Crossover, RVI(10)>50 Confirmed (QQQ accepted; SPY rejected)

**Strategy file:** `strategies/2026-09-09_sma_crossover_rvi_confirmed.py`
**Knowledge base id:** 2026-09-09-080

## Hypothesis + source

Per a Scribd-hosted RVI trading-rules document (surfaced via Google search
snippet, browser_exec fallback since web_search DDGS backend errored this
iteration), Donald Dorsey's own published six-rule system explicitly states:
"Only take buy signals from moving average crossover when RVI>50." This
tests RVI as a pure confirmation gate on an independent fast/slow SMA
crossover, distinct from the already-accepted plain RVI midline-crossover
(2026-09-05-003), which uses RVI itself (not an SMA cross) as the trigger.

## Grid test (Step 6)

`param_grid={"fast_window": [10,20], "slow_window": [50,100], "rvi_period": [10,14]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- **pass_fraction: 0.229** (22/96 cells)
- by_asset_class: equity 22/48, crypto 0/48 (decisive crypto rejection)
- by_vol_regime: low 16/32, mid 6/32, high 0/32
- best_cell: QQQ, low-vol, fast_window=10/slow_window=100/rvi_period=10, Sharpe 3.04

## Single-config validators (Step 7), config: fast_window=10, slow_window=100, rvi_period=10

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **1.590 PASS** | 0.766 FAIL |
| Max drawdown (<=0.25) | 0.074 PASS | 0.072 PASS |
| Transaction-cost survival (net Sharpe >=0.5) | 1.562 PASS | 0.733 PASS |
| Walk-forward (4 splits, >=75% positive) | 4/4 PASS | 4/4 PASS |
| Parameter sensitivity (relative_std <=0.5) | 0.214 PASS | 0.339 PASS |

QQQ: all 5 validators pass, with a strong Sharpe (1.59), very low MDD (7.4%),
and only 13 trades over 7.7yr (low turnover, robust cost survival). SPY:
4/5 pass but Sharpe (0.766) is a clear miss (not a near-miss) -- the
confirmation gate produces a genuinely weaker signal on SPY than on QQQ.

## Decision

**Accept for QQQ only.** Reject SPY (clear Sharpe miss). Crypto rejected
decisively (0/48 grid cells).
