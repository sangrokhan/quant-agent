# 2026-09-22 — Inside Day + ATR Compression Breakout (EMA50 trend)

**Hypothesis**: Source: https://algobars.com/strategy-templates/volatility/inside-day-low-atr/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). "Double compression" setup: an inside day (today's H<yesterday's
H, today's L>yesterday's L) combined with ATR(14) near a 20-day rolling
LOW (volatility compressed), gated by price above EMA(50) (uptrend context),
is a "coiled spring" -- trade the breakout of the inside day's own range for
outsized moves, targeting 2x the inside day's range. Distinct from this
repo's 6 prior Inside Day entries (2026-09-04-090 plain EMA-filtered
breakout with no volatility-compression gate; 2026-09-07-006/007 gap-down
pullback same-bar-close entry; 2026-09-08-069 Fakey false-breakout reversal;
2026-09-22-014 StochRSI+Chaikin confirmation) via the explicit
double-compression (inside day AND ATR-at-rolling-low) gate combined with a
breakout-of-range entry and a fixed 2x-range profit target.

**Strategy file**: `strategies/2026-09-22_inside_day_atr_compression_breakout.py`

**Grid test** (`run_grid_inside_day_atr_compression_breakout.py`):
param_grid = `{atr_compress_pct: [0.05, 0.10, 0.20], target_mult: [1.5, 2.0, 3.0]}`,
symbols = equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=108, passed_cells=21, pass_fraction=0.194
- by_asset_class: equity 11/54, crypto 10/54
- by_vol_regime: low 1/36, **mid 14/36**, high 6/36 — edge concentrated
  heavily in the mid-volatility tercile
- best_cell: equity QQQ, atr_compress_pct=0.05/target_mult=2.0, mid-vol,
  Sharpe 1.51 (per-tercile, not full-sample)

**Single-config validators** (best QQQ/SPY config: `atr_compress_pct=0.05`,
`target_mult=2.0`; crypto best config: `atr_compress_pct=0.10`,
`target_mult=2.0`/`3.0`), full-sample 2019-2026:

| Metric | QQQ | SPY | BTC/USDT (tm=3.0) | ETH/USDT (tm=3.0) | Threshold |
|---|---|---|---|---|---|
| Sharpe ratio | 0.669 | 0.075 | 0.690 | 0.634 | ≥1.0 (all FAIL) |
| Max drawdown | 0.058 (pass) | 0.055 (pass) | 0.187 (pass) | 0.259 (FAIL) | ≤0.25 |
| TX-cost survival (net Sharpe, 10bps/trade) | 0.283 (FAIL) | -0.225 (FAIL) | 0.621 (pass) | 0.573 (pass) | ≥0.5 |
| Walk-forward (4-split, manual fallback — vbt.utils.splitting unavailable) | 0.75 pass | 0.50 FAIL | not run | not run | ≥0.75 |
| Parameter sensitivity | 0.248 pass | 1.38 FAIL | not run | not run | ≤0.5 rel-std |

**Decision**: REJECTED (all symbols). The grid's promising mid-vol-tercile
performance (best_cell Sharpe 1.51, 14/36 mid-vol passes) does NOT
generalize to the full sample — every symbol's full-sample Sharpe stays
well below 1.0 (0.075-0.690), and QQQ/SPY additionally fail transaction-cost
survival at realistic 10bps/trade costs. This is a clear case of the grid's
regime-slicing surfacing an artifact concentrated in one vol tercile rather
than a genuine broad edge (consistent with this repo's recurring finding
pattern for narrow-regime-only setups, e.g. Nadaraya-Watson envelope
2026-09-08-014, MA Envelope 2026-09-06-106). SPY additionally fails
walk-forward (0.50 < 0.75) and has catastrophic parameter sensitivity
(rel-std 1.38), indicating a curve-fit-fragile config rather than a robust
edge. Crypto (BTC/ETH) shows a modest improvement at the wider target_mult
but never clears the Sharpe bar full-sample; ETH additionally fails MDD.
