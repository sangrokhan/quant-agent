# ATR Channel Breakout — short-baseline retune (2026-09-10)

**Hypothesis**: Follow-up to near-miss 2026-09-09-096 (ATR Channel Breakout,
baseline_window=350). Its own `notes` suggested shortening the baseline
window with a wider ATR mult to raise trade frequency (~2-3/yr) and possibly
clear the Sharpe threshold. Source: TradingCode/TradingBlox/StockGro
synthesis, originally read via browser_exec Google-search fallback in
2026-09-09-096 (re-used here since this is a pure parameter retune, no new
external research needed).

**Grid** (`scripts/run_iter_atr_channel_shortbaseline.py`):
`baseline_window=[50,100]`, `atr_mult=[3.0,4.0,5.0]`, `max_hold_days=[40]`,
equity (QQQ, SPY) x crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3,
2018-01-01 to 2026-09-01.

- total_cells=72, passed=14, pass_fraction=0.194
- by_asset_class: equity 14/36 (0.389), crypto 0/36 (decisive fail)
- by_vol_regime: low 12/24 (0.500), mid 2/24 (0.083), high 0/24 (0.0)
- best_cell: baseline_window=100/atr_mult=4.0, SPY low-vol Sharpe=2.588
- worst_cell: baseline_window=100/atr_mult=4.0, QQQ high-vol Sharpe=-1.532

Best config selected for single-config validation: `baseline_window=100,
atr_mult=4.0, max_hold_days=40` (top full-sample-level combo from the grid).

## Single-config validator results (best config)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.396 (FAIL, thr 1.0) | 28.3% (FAIL, thr 25%) | 0.360 (FAIL, thr 0.5) | 0.75 (PASS) | 0.218 (PASS) |
| SPY | 0.677 (FAIL, thr 1.0) | 15.0% (PASS) | 0.623 (PASS) | 0.75 (PASS) | 0.148 (PASS) |

## Decision: REJECT

Shortening the baseline window from 350 to 100 days did **not** rescue the
near-miss — it made things worse. Both QQQ and SPY still decisively fail
full-sample Sharpe (0.40 / 0.68, both further from the 1.0 threshold than
the original 350-baseline variant's 0.73/0.68), and QQQ now additionally
fails max-drawdown (28.3% vs the original 350-baseline's 26.0%) as well as
transaction-cost survival. Crypto remains a decisive 0/36 fail across the
board, same as the original. The by_vol_regime concentration (low-vol only)
persists identically to the parent strategy — shortening the baseline did
not change which regime the edge lives in, it just amplified whipsaw in
mid/high-vol regimes (mid-vol pass rate dropped from the parent's ~14% down
to 8%).

**Conclusion for future loops**: the ATR-Channel-breakout family (both
baseline_window=350 original and this 100-day retune) appears to have a
structural ceiling around Sharpe 0.4-0.75 on QQQ/SPY, not overcome by
window-length tuning alone. A future revisit should try a genuinely
different lever (e.g. a trend/regime co-filter, or restricting entries to
the already-identified low-vol regime explicitly) rather than another
baseline-window sweep.
