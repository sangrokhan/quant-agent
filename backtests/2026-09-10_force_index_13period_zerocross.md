# 2026-09-10: Elder Force Index 13-period zero-line crossover (QQQ, SPY)

**Hypothesis (id 2026-09-10-097):** Per Google AI-overview synthesis
(Definedge Securities/StockCharts.com ChartSchool/Deepvue, browser_exec
fallback): Raw Force Index = (close-prev_close)*volume; 13-period EMA of
this raw series is the standard trend filter; buy when it crosses above
zero (bulls in control), exit when it crosses back below zero. Distinct
from this repo's 3 existing Force Index variants (dual-EMA pullback
2026-09-04-049, FI(39) divergence 2026-09-05-048, FI(2)+STC confirmation
2026-09-09-086) -- first plain single-EMA zero-line-crossover test.

## Single-config metrics (fi_period=13, max_hold_days=60 -- grid best cell)

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-forward | # trades |
|---|---|---|---|---|---|
| QQQ | 0.910 (FAIL, thr 1.0, near-miss) | 0.309 (FAIL, thr 0.25) | 0.714 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75) | 135 |
| SPY | 0.852 (FAIL, thr 1.0, near-miss) | 0.209 (PASS, thr 0.25) | 0.574 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75) | 138 |

## Grid summary (fi_period x [8,13,20], max_hold_days x [15,30,60]; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 108, passed_cells: 29, pass_fraction: 0.269
- by_asset_class: equity 29/54 passed; crypto 0/54 passed (decisive crypto rejection)
- by_vol_regime: low 18/36; mid 9/36; high 2/36 (strongly concentrated in low-vol, degrades sharply in high-vol)
- best_cell: fi_period=13, max_hold_days=60, QQQ, low-vol, Sharpe=2.67
- worst_cell: fi_period=8, max_hold_days=30, QQQ, high-vol, Sharpe=-0.32

## Verdict: REJECTED

Full-sample single-config Sharpe fails on both QQQ (0.910) and SPY (0.852) --
both close near-misses but below the 1.0 threshold. QQQ additionally fails
max drawdown (0.309 > 0.25 threshold), driven by unbounded 60-day holds
letting losing positions run through the 2022 rate-hike drawdown. Net-Sharpe-
after-costs and walk-forward both pass on both symbols, so this is not a
decisive rejection -- the edge is real but concentrated almost entirely in
low-vol equity regimes (18/36 low-vol cells passed vs only 2/36 high-vol).
Crypto is decisively rejected (0/54 cells). A future iteration could revisit
with an explicit low-vol regime gate (restricting entries to when 20d
realized vol <= trailing median, matching this repo's repeated successful
pattern elsewhere) and a tighter max_hold_days or ATR-based stop to fix the
QQQ MDD failure, rather than the unconditional 60-day hold used here.
