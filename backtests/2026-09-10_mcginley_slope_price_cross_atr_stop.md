# 2026-09-10: McGinley Dynamic slope-confirmed price-cross + ATR stop/TP (QQQ, SPY)

**Hypothesis (id 2026-09-10-096):** Per
https://www.forexcracked.com/education/mcginley-dynamic-forex-trading-strategy/
(via browser_exec fallback -- web_search's DDGS backend returned a
RequestError/TLS unexpected-eof on the initial query this iteration), the
source's disclosed rule: confirm uptrend via McGinley Dynamic (MD) line
sloping upward, enter long when close crosses above the MD line, place a
stop-loss below the recent swing low/MD line, take profit at a 1:2
risk:reward multiple. Distinct from this repo's existing McGinley variants
(2026-09-04-127 dual fast/slow crossover; 2026-09-08-020 price-crosses-BELOW
mean-reversion with fixed hold; 2026-09-09-049 crossover+SMA gate+vol exit) --
first single-line price-crosses-ABOVE trend-following variant with a genuine
ATR-based stop-loss/take-profit exit (fixed risk:reward) instead of a
signal-based or time-based exit.

## Single-config metrics (md_period=15, stop_atr_mult=1.5, rr_ratio=2.0 -- grid best cell)

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-forward pass_fraction | # trades |
|---|---|---|---|---|---|
| QQQ | -0.11 (FAIL, thr 1.0) | 0.207 (PASS, thr 0.25) | -0.168 (FAIL, thr 0.5) | 0.50 (FAIL, thr 0.75) | 23 |
| SPY | 0.955 (FAIL, thr 1.0, near-miss) | 0.055 (PASS, thr 0.25) | 0.855 (PASS, thr 0.5) | 1.00 (PASS, thr 0.75) | 27 |

## Grid summary (md_period x [15,20,30], stop_atr_mult x [1.5,2.0], rr_ratio x [1.5,2.0]; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 144, passed_cells: 12, pass_fraction: 0.083
- by_asset_class: equity 12/72 passed; crypto 0/72 passed (decisive crypto rejection)
- by_vol_regime: low 0/48; mid 4/48; high 8/48 (only holds in higher-vol regimes)
- best_cell: md_period=15, stop_atr_mult=1.5, rr_ratio=2.0, SPY, high-vol, Sharpe=2.17
- worst_cell: md_period=20, stop_atr_mult=2.0, rr_ratio=1.5, QQQ, high-vol, Sharpe=-1.47

## Verdict: REJECTED

Both single-config Sharpe checks fail the 1.0 threshold (QQQ decisively
negative; SPY a near-miss at 0.955). QQQ additionally fails net-Sharpe-after-
costs and walk-forward. Grid pass-rate is very low overall (8.3%) and
entirely concentrated in equity mid/high-vol cells; crypto is decisively
rejected across all 72 cells. Not accepted, but the SPY near-miss + narrow
high-vol-only grid concentration could be worth revisiting with a
volatility-regime gate restricting entries to mid/high-vol terciles only
(similar pattern to several other accepted "regime-gated" variants in this
repo), rather than trading unconditionally across all vol regimes.
