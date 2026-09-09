# Backtest report: Wyckoff Spring (volume-confirmed)

**Strategy file:** `strategies/2026-09-09_wyckoff_spring_volume_confirmed.py`
**Knowledge base id:** 2026-09-09-106
**Outcome:** REJECTED (direct follow-up to rejected 2026-09-09-105)

## Hypothesis

Per algobars.com's dedicated Wyckoff Spring strategy template: "Volume on
the spring is LOW (no real selling)... The key to identifying a Spring vs
a genuine breakdown is volume. A true Spring occurs on diminishing
volume." Added a volume-confirmation gate (probe bar's volume <=
`vol_ratio_max` x its trailing `vol_ma_window`-day average) to the
identical probe/reclaim mechanism as the parent (rejected) strategy.

## Grid test summary (Step 6)

- Grid: `range_window` in [10, 20, 30] x `vol_ratio_max` in [0.6, 0.8,
  1.0] x `max_hold_days` in [15, 25] x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3
  vol terciles = 216 cells.
- `pass_fraction`: **0.005** (1/216) -- worse than the parent's 0.049
- `by_asset_class`: equity 1/108, crypto 0/108
- `by_vol_regime`: high 1/72, low/mid 0/72 each
- Best cell: SPY, high-vol tercile, `range_window=30, vol_ratio_max=1.0,
  max_hold_days=15`, Sharpe 1.280

## Single-config validation (Step 7), best grid config

| Symbol | Sharpe (full sample) | Threshold | Passed | Max Drawdown | Threshold | Passed |
|---|---|---|---|---|---|---|
| SPY | 0.618 | 1.0 | No | 0.040 | 0.25 | Yes |
| QQQ | 0.278 | 1.0 | No | 0.139 | 0.25 | Yes |

## Verdict

The volume filter DID fix the max-drawdown failure mode from the parent
strategy (0.040/0.139 vs parent's 0.346/0.305) -- confirming the source's
diagnosis that volume separates genuine springs from real breakdowns.
However, Sharpe still fails decisively on both symbols: the filter cuts
opportunity/trade count so severely that whatever edge remains isn't
enough to clear the 1.0 threshold. Crypto rejected outright (0/108). Not
accepted -- this closes out the Wyckoff Spring family for this repo.
