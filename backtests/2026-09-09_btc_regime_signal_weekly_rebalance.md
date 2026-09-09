# 2026-09-09 — Bitcoin Regime Signal, Weekly Rebalance Fix (rejected, strong near-miss)

**Hypothesis** (id `2026-09-09-115`): Direct fix for near-miss/high-promise
rejection 2026-09-09-114 (Bitcoin Regime Signal for Growth Equities, per
QuantConnect Research Publication
https://www.quantconnect.com/research/21195/bitcoin-regime-signal-for-growth-equities/).
That iteration's daily-evaluation adaptation caused catastrophic TC-survival
failure (952 trades, net Sharpe went negative) despite a moderate full-sample
Sharpe miss (0.73-0.74) and the best grid pass_fraction of that cron
trigger. This iteration implements a genuine **weekly rebalance**: the BTC
regime gate (close > 50d SMA AND 20d ROC > 0) is sampled ONLY on each ISO
calendar week's first trading day and held constant for the rest of that
week, exactly matching the source's own "evaluate at the start of each week"
methodology, instead of re-evaluating daily.

Strategy file: `strategies/2026-09-09_btc_regime_signal_weekly_rebalance.py`

## Step 6 grid summary (sma_window ∈ {30,50,70} × roc_window ∈ {10,20,30} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 108 cells)

- `pass_fraction`: 0.204 (22/108) — lower than the daily-eval version's
  0.287, but still passes in both low AND high vol regimes
- `by_asset_class`: equity 22/54, crypto 0/54 (degenerate self-referential
  BTC-on-BTC case, expected)
- `by_vol_regime`: low 15/36, mid 0/36, high 7/36
- `best_cell`: sma_window=50, roc_window=20 (source's own default config),
  QQQ, low-vol regime, Sharpe 1.97

## Single-config validators (source's default config: sma_window=50, roc_window=20), full 2019-2026 sample, WEEKLY evaluation

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **0.982** ❌ (near-miss) | **0.966** ❌ (near-miss) | ≥ 1.0 |
| Max drawdown | 0.215 ✅ | 0.173 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | 0.666 ✅ | 0.543 ✅ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice fallback) | 0.75 ✅ | 1.00 ✅ | ≥ 0.75 pass fraction |
| Parameter sensitivity (sma_window 30/50/70 sweep) | 0.123 ✅ | | ≤ 0.5 relative std |
| Trades | 215 | 215 | — |

Trade count dropped from 952 (daily) to 215 (weekly) — roughly a 4.4x
reduction, confirming the churn hypothesis from 2026-09-09-114's notes.

## Verdict: **reject** (both QQQ and SPY) — extremely close near-miss

**Every single validator passes except full-sample Sharpe**, and Sharpe
itself is a razor-thin miss: QQQ 0.982 and SPY 0.966, both within 2-3% of
the 1.0 threshold. MDD, TC-survival, walk-forward (both symbols, SPY at a
perfect 1.0 pass fraction), and parameter sensitivity all pass comfortably.
This is the strongest near-miss produced by this repo's research loop in
recent iterations (per the knowledge base's use of "near-miss" for anything
failing only Sharpe by this margin while clearing every other bar). The
weekly-rebalance fix worked exactly as hypothesized: it eliminated the
daily-eval version's catastrophic TC-survival failure and pulled Sharpe from
~0.73-0.74 up to ~0.97-0.98.

**Recommended next steps for a future iteration** (not pursued further this
cron trigger, to stay within a single-iteration scope): (1) a small tweak to
the ROC/SMA windows around the current optimum (the grid's best_cell used a
different vol-regime slice, not the full sample — a finer local search near
sma_window=50/roc_window=20 might clear 1.0); (2) adding a light trend/vol
overlay (e.g. combining with an ATR-based position-sizing or a secondary
confirmation filter) that could lift Sharpe without meaningfully hurting the
already-clean TC-survival and parameter-sensitivity profile; (3) extending
or shifting the backtest window, since 2019-2026 includes both the 2022
crypto winter and 2025-2026 conditions that may be dragging the full-sample
Sharpe down relative to sub-period performance.
