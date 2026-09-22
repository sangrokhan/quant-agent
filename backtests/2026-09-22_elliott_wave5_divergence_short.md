# 2026-09-22 — Elliott Wave 5 Momentum Divergence (short at exhausted top)

**Hypothesis**: Source: https://algobars.com/strategy-templates/elliott/elliott-wave-5-divergence/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Wave 5 of an Elliott impulse often terminates with momentum
divergence: price makes a new extreme above the Wave 3 peak while RSI/MACD
show weaker readings than at the Wave 3 peak, signaling trend exhaustion.
Short entry on a bearish confirmation candle at the divergent Wave 5 peak,
targeting the Wave 4 low first (then Wave 1 territory), stop above the
Wave 5 extreme. First short-side Elliott strategy in this repo, distinct
from this cron trigger's Wave 3 breakout (long, impulse continuation) and
ABC Correction (long, corrective completion).

**Strategy file**: `strategies/2026-09-22_elliott_wave5_divergence_short.py`

**Grid test** (`run_grid_elliott_wave5_divergence_short.py`): param_grid =
`{pivot_window: [3, 5, 8], rsi_div_min: [3.0, 5.0, 8.0]}`, symbols =
equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=108, passed_cells=15, pass_fraction=0.139
- by_asset_class: equity 6/54, crypto 9/54
- by_vol_regime: low 10/36, mid 5/36, **high 0/36** -- expected for a
  short-only strategy (high-vol regimes in this sample skew toward strong
  bull continuations, punishing shorts)
- best_cell: BTC/USDT pivot_window=8/rsi_div_min=3.0, low-vol, Sharpe 1.61
  (per-tercile)
- BTC/USDT pivot_window=8 passed 2/3 vol regimes consistently across all
  3 tested rsi_div_min values -- the most cross-regime-consistent
  parameter found this cron trigger

**Single-config validators** (full-sample 2019-2026, BTC/USDT,
`pivot_window=8`):

| rsi_div_min | Sharpe | MDD | TX-cost survival | Trades |
|---|---|---|---|---|
| 3.0 | 0.822 (FAIL) | 0.197 (pass) | 0.800 (pass) | 22 |
| 5.0 | 0.822 (FAIL) | 0.197 (pass) | 0.800 (pass) | 22 |
| 8.0 | 0.539 (FAIL) | 0.300 (FAIL) | 0.519 (pass) | 18 |

**Decision**: REJECTED (all configs, all symbols). Despite a promising
cross-regime-consistent grid signal (BTC/USDT pivot_window=8 passing 2/3
vol terciles), full-sample Sharpe stays below the 1.0 threshold at every
tested `rsi_div_min` (best 0.822 at rsi_div_min=3.0/5.0 -- a genuine
near-miss, not a decisive failure, but still short of acceptance).
Transaction-cost survival and MDD are largely fine at the tighter
divergence threshold. This is a legitimate near-miss worth a future
targeted BTC/USDT-specific parameter retune (e.g. finer rsi_div_min sweep
between 3-5, or adding a trend/momentum-strength pre-filter) rather than a
decisively falsified hypothesis.
