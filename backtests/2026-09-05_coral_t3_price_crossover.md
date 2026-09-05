# Coral Trend (T3) Price-Crossover Trend Strategy — ACCEPTED (SPY only)

**Strategy file:** `strategies/2026-09-05_coral_t3_price_crossover.py`
**Knowledge base id:** 2026-09-05-090
**Source:** https://in.tradingview.com/scripts/coraltrend/

## Hypothesis

Close price crossing above LazyBear's Coral Trend line (Tim Tillson's T3
moving average, a sextuple-cascaded-EMA construction with a fixed
polynomial recombination for reduced lag) signals a long entry; exit on
close crossing back below the Coral Trend line or a time-stop. Distinct
from the already-tested T3/Coral "slope_flip" variant (2026-09-04-131,
near-miss QQQ Sharpe 0.935) which used T3's own slope direction as the
trigger instead of price-crossing.

## Grid test summary (72 cells: equity QQQ/SPY + crypto BTC/ETH, params
t3_period in {10,20,30} x max_hold_days in {20,30}, vol_regime_splits=3)

- pass_fraction: 0.278 (20/72)
- by_asset_class: equity 20/36, crypto 0/36
- by_vol_regime: low 11/24, mid 9/24, high 0/24
- best_cell: QQQ, t3_period=20, max_hold_days=30, low-vol Sharpe 2.183

## Full-sample re-check (best params per symbol)

| Symbol | Best params | Full-sample Sharpe |
|---|---|---|
| QQQ | t3_period=20, hold=30 | 0.965 (near-miss) |
| SPY | t3_period=20, hold=20 | 1.141 (PASS) |
| BTC/USDT | t3_period=20, hold=20 | 0.181 (FAIL) |
| ETH/USDT | t3_period=20, hold=20 | 0.301 (FAIL) |

## Validators (SPY, t3_period=20, max_hold_days=20 -- shared config with
QQQ fails: QQQ Sharpe only 0.756 at this exact config, so QQQ is NOT
accepted; SPY-only primary config)

- Sharpe ratio: PASS (1.141 > 1.0)
- Max drawdown: PASS (0.128 < 0.25)
- Transaction cost survival: PASS (net Sharpe 0.590 > 0.5, 258 trades,
  10bps/trade)
- Walk-forward (4 manual date-slice splits, vbt.utils.splitting bug
  workaround): PASS (4/4 splits positive, Sharpe 0.806/1.002/0.921/2.023)
- Parameter sensitivity (t3_period in {10,20,30}, max_hold_days=20 fixed):
  PASS (relative std 0.164 < 0.5; sharpes 0.758/1.141/1.009)

## Verdict: ACCEPTED (SPY only)

QQQ at the shared config (t3_period=20, max_hold_days=20) only reaches
Sharpe 0.756 -- a clear miss, not a razor-thin pass, so QQQ is explicitly
NOT accepted despite passing in some grid cells at other param combos
(QQQ's own best full-sample config, t3_period=20/hold=30, is a near-miss
at 0.965). Crypto rejected decisively (0/36 grid cells, full-sample
Sharpe 0.18-0.30). The price-crossover trigger performs meaningfully
better than the previously-tested slope-flip trigger on SPY specifically.
