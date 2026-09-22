# 2026-09-22 — Al Brooks "Always-In" Trend Bar + Follow-Through (EMA-gated)

**Hypothesis**: Source: https://algobars.com/strategy-templates/al-brooks/brooks-always-in/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Al Brooks' "always-in" concept: the market is always either
always-in-long or always-in-short (no flat state); flip when a strong
trend bar (closing on its extreme) is followed by a same-direction
follow-through bar, confirmed by price on the correct side of EMA(20).
First direct implementation of this specific trend-bar+follow-through+EMA
mechanic in this repo (existing KB "always_in"-tagged entries use different
constructions: Donchian SAR, ATR-ratchet, TTF hysteresis, LBR 3/10, COG
crossover -- none match Brooks' explicit trigger).

**Strategy file**: `strategies/2026-09-22_brooks_always_in.py`

**Grid test** (`run_grid_brooks_always_in.py`): param_grid =
`{trend_bar_pctile: [0.65, 0.75, 0.85], ema_window: [10, 20, 50]}`,
symbols = equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=108, passed_cells=14, pass_fraction=0.130
- by_asset_class: equity 14/54, **crypto 0/54**
- by_vol_regime: **low 13/36**, mid 1/36, high 0/36 -- edge almost entirely
  confined to the low-volatility tercile
- best_cell: QQQ trend_bar_pctile=0.65/ema_window=50, low-vol, Sharpe 2.63
  (per-tercile)

**Single-config validators** (full-sample 2019-2026, QQQ,
`trend_bar_pctile=0.65, ema_window=50`):

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 0.005 | ≥1.0 | FAIL (decisive) |
| Max drawdown | 0.478 | ≤0.25 | FAIL (decisive, ~2x the cap) |
| TX-cost survival | -0.029 | ≥0.5 | FAIL (decisive) |
| Trade count | 51 | -- | -- |

**Decision**: REJECTED (all symbols/configs). The grid's very strong
low-vol-tercile-only best cell (Sharpe 2.63) completely evaporates
full-sample (Sharpe 0.005, essentially zero edge), with a catastrophic
0.478 max drawdown nearly double the acceptance ceiling. This is the same
regime-concentration artifact pattern seen repeatedly this cron trigger
(Inside Day ATR Compression, Elliott Wave 3) -- a strategy that looks
excellent in one narrow vol regime but has no genuine broad edge. Crypto
fails completely (0/54 grid cells) -- the always-in stop-and-reverse
mechanic with no flat state appears especially costly on crypto's higher
baseline volatility (frequent whipsaw reversals with no ability to sit out
choppy periods).
