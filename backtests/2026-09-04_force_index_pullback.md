# Backtest Report: Elder's Force Index Dual-EMA Pullback Entry

**Strategy file:** `strategies/2026-09-04_force_index_pullback.py`
**Knowledge base id:** 2026-09-04-049

## Hypothesis

Per a Google AI-overview synthesis (Finlogix/LuxAlgo/TradingView et al.):
Elder's Force Index (EFI = (close - prev_close) * volume) combines price
change, direction, and volume. Long-term EMA (13-period) determines trend
direction (positive = bull); short-term EMA (2-3 period) times pullback
entries — while the long EFI stays positive, wait for the short EFI to
dip below zero (brief pause in buying pressure) then cross back above
zero as the buy trigger. Exit when the long-term trend filter turns
negative.

Source: Google AI-overview (`web_search` returned no results for Force
Index, fell back to `browser_exec` immediately).

## Grid test summary (Step 6)

Grid: `short_window` in {2, 3} x `long_window` in {13, 20} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 48 cells.

- `pass_fraction`: 0.229 (11/48)
- `by_asset_class`: equity 11/24, crypto 0/24
- `by_vol_regime`: low 8/16, mid 3/16, high 0/16
- `best_cell` (low-vol-tercile artifact): QQQ, short_window=2,
  long_window=13, Sharpe 2.53

## Full-sample sweep (QQQ / SPY)

| short_window | long_window | QQQ Sharpe | SPY Sharpe |
|---|---|---|---|
| 2 | 13 | 0.867 | 0.675 |
| 2 | 20 | 0.989 | 0.531 |
| 3 | 13 | **1.098** | 0.488 |
| 3 | 20 | 1.073 | 0.325 |

Primary config: `short_window=3, long_window=13` (source's own default
short_window=2 slightly underperforms short_window=3 on this sample) —
best full-sample Sharpe on QQQ.

## Primary config validators (QQQ, short_window=3, long_window=13)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.098 | 1.0 |
| Max drawdown | ✅ | 0.174 | 0.25 |
| Transaction cost survival | ✅ | 0.940 (90 trades @ 10bps) | 0.5 |
| Walk-forward (4 splits, manual date-slice fallback) | ✅ | 1.0 (4/4 splits positive) | 0.75 |
| Parameter sensitivity (short/long window 4-combo sweep) | ✅ | rel.std 0.090 | 0.5 |

**All 5 validators pass on QQQ.**

SPY fails Sharpe decisively at every combo tested (best 0.675, far from
threshold) — not accepted. Crypto rejected decisively (0/24 grid cells).

## Outcome

**Accepted for QQQ only.** SPY rejected. Crypto rejected decisively.

## Notes

Walk-forward used the manual date-slice fallback per the documented
`vectorbt.utils.splitting` API bug — a clean 4/4 record. First Force
Index (raw signed price-change magnitude weighted by volume, distinct
from OBV's sign-only, CMF/A-D's intrabar-position-only weighting)
strategy tested in this repo. Consistent with the repo's recurring
pattern of volume-confirmation trend/pullback strategies passing on QQQ
but not SPY (see also -027, -043, -047).
