# Backtest Report: Kaufman Adaptive Moving Average (KAMA) Crossover + Slope Confirmation

**Strategy file:** `strategies/2026-09-04_kama_crossover_slope.py`
**Knowledge base id:** 2026-09-04-048

## Hypothesis

Per a Google AI-overview synthesis (Definedge Securities / Darwinex /
Arrow Algo et al.): the Kaufman Adaptive Moving Average (KAMA) speeds up
in smooth trending conditions and slows down in choppy/noisy conditions
via an Efficiency Ratio. Standard params: ER period=10, fast EMA
constant=2, slow EMA constant=30. Long entry: close above KAMA AND KAMA's
own slope rising; exit when close closes back below a flattening/falling
KAMA.

Source: Google AI-overview (`web_search` failed with a DDGS/Yahoo TLS
connection error, fell back to `browser_exec` immediately).

## Grid test summary (Step 6)

Grid: `er_period` in {10, 20} x `slow_ema_const` in {20, 30} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 48 cells.

- `pass_fraction`: 0.25 (12/48)
- `by_asset_class`: equity 12/24, crypto 0/24
- `by_vol_regime`: low 8/16, mid 4/16, high 0/16
- `best_cell` (low-vol-tercile artifact): QQQ, er_period=20,
  slow_ema_const=30, Sharpe 2.44

## Full-sample sweep (QQQ / SPY)

| er_period | slow_ema_const | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|---|
| 10 | 20 | 0.781 (143) | 0.850 (140) |
| 10 | 30 | 0.805 (133) | 0.795 (135) |
| 20 | 20 | 1.169 (98)  | 1.080 (97)  |
| 20 | 30 | **1.230** (86) | **1.137** (91) |

Primary config: `er_period=20, slow_ema_const=30` — best full-sample
Sharpe on both symbols (source's own default er_period=10 underperforms
the longer 20-period ER window on this sample, consistent with other
strategies in this repo where longer smoothing windows generalize
better).

## Primary config validators

### QQQ (er_period=20, slow_ema_const=30)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.230 | 1.0 |
| Max drawdown | ❌ | 0.284 | 0.25 |
| Transaction cost survival | ✅ | 1.101 (86 trades @ 10bps) | 0.5 |
| Parameter sensitivity | ✅ | rel.std 0.205 | 0.5 |

**QQQ fails MDD** (13.6% over budget) — not accepted at this config.

### SPY (same config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.137 | 1.0 |
| Max drawdown | ✅ | 0.210 | 0.25 |
| Transaction cost survival | ✅ | 0.957 (91 trades @ 10bps) | 0.5 |
| Walk-forward (4 splits, manual date-slice fallback) | ✅ | 0.75 (3/4 splits positive) | 0.75 |
| Parameter sensitivity | ✅ | rel.std 0.151 | 0.5 |

**All 5 validators pass on SPY.**

### Crypto

0/24 grid cells passed — decisively rejected.

## Outcome

**Accepted for SPY only** (unusual in this repo — most volume/trend
accepts have been QQQ-only; this is the accepted-SPY-not-QQQ case). QQQ
fails max drawdown at the shared primary config. Crypto rejected
decisively.

## Notes

Walk-forward used the manual date-slice fallback per the documented
`vectorbt.utils.splitting` API bug; split 1 (~2020-2021) was the sole
negative split for SPY. First KAMA (self-adjusting-smoothing-constant
moving average, distinct from every fixed-window or reduced-lag-weighted
MA already tested — SMA/EMA/HMA all use fixed windows or weighting
schemes independent of realized trend efficiency) strategy tested in this
repo. QQQ's higher volatility/larger drawdowns relative to SPY (a
recurring pattern across accepted strategies in this log, e.g. 2026-09-
04-033 MFI, 2026-09-03-005 RSI2) is the likely driver of QQQ's MDD
failure here despite a higher raw Sharpe.
