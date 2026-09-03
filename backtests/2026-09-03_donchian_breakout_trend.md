# Backtest Report: Donchian Channel Breakout + 200d Trend Filter (Long-Only)

**Strategy file:** `strategies/2026-09-03_donchian_breakout_trend.py`
**Date:** 2026-09-03
**Hypothesis id:** 2026-09-03-008

## Hypothesis

Source: https://secuora.net/strategy/donchian-breakout — an original-research
backtest of the classic Turtle-style 20-bar Donchian channel breakout
(bidirectional long+short, no trend filter, 1.5xATR(14) stop, 2R target) on
BTC/ETH 1h candles (Jun 2025 - Jun 2026, Binance data) found it net-losing on
both symbols (BTC: profit factor 0.76, MDD 52.2%, net -51.1%; ETH: profit
factor 0.97, MDD 27.3%, net -9.7%; overall win rate 33.9% across 803 trades),
explicitly attributed to breakout systems only working when the instrument
actually trends — taking every breakout bidirectionally with no filter eats
whipsaws during chop.

This strategy tests a narrower, long-only **daily** variant: only take
Donchian upside breakouts (N-day high) that occur while `close > 200-day SMA`
(established uptrend); exit on either a symmetric N/2-day-low breakout
(trailing channel stop) or the trend filter flipping. Hypothesis: filtering
out counter-trend breakouts removes most of the whipsaw that hurt the raw
bidirectional version while preserving the "ride established trends" edge.

## Step 6 — Grid test summary

Grid: `entry_window ∈ {15, 20, 30}` × `exit_window ∈ {5, 10}` (trend_window
fixed at 200) × symbols `{QQQ, SPY} (equity)`, `{BTC/USDT, ETH/USDT} (crypto)`
× 3 realized-vol terciles (low/mid/high). 72 cells total, period
2019-01-01 to 2026-09-01.

| Slice | Passed / Total |
|---|---|
| Overall | 18 / 72 (25.0%) |
| Equity | 18 / 36 (50.0%) |
| Crypto | 0 / 36 (0.0%) |
| Low-vol regime | 12 / 24 (50.0%) |
| Mid-vol regime | 6 / 24 (25.0%) |
| High-vol regime | 0 / 24 (0.0%) |

Best cell: `entry_window=15, exit_window=10`, QQQ, low-vol regime, Sharpe
2.49. Worst cell: `entry_window=30, exit_window=10`, SPY, high-vol regime,
Sharpe -0.63.

**Honest scope: this strategy only clears the bar on equity (QQQ/SPY), and
only in low/mid realized-vol regimes — it fails universally on crypto
(BTC/USDT, ETH/USDT) across all vol regimes, and fails on equity during
high-vol regimes.** This mirrors the source article's own finding (breakout
systems need the instrument to actually trend) — crypto's whipsaw-heavy 24/7
microstructure and equity high-vol regimes (crash/rate-hike periods) don't
provide clean enough trends for this rule.

## Step 7 — Single-config validation (best config: QQQ, entry_window=15, exit_window=10, trend_window=200, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.25 | ≥ 1.0 |
| Max drawdown | ✅ | 14.7% | ≤ 25% |
| Transaction cost survival (10bps/trade, 29 trades) | ✅ | net Sharpe 1.21 | ≥ 0.5 |
| Walk-forward (4 contiguous OOS windows) | ✅ | 3/4 splits positive Sharpe (75%) | ≥ 75% |
| Parameter sensitivity (6-point grid, entry×exit combos on QQQ) | ✅ | relative std 0.15 | ≤ 0.5 |

Note: `validation/validators.py::check_walk_forward` currently raises
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` on
the installed vectorbt version (`vectorbt.utils.splitting.RangeSplitter` does
not exist in this build) — worked around with a manual 4-window contiguous
date-slice fallback replicating the same n_splits/min_pass_fraction contract
(see script notes). A future iteration should either pin/patch vectorbt or
fix `check_walk_forward` to use whatever splitter API the installed version
actually exposes.

## Decision: **ACCEPT** (scoped to equity, QQQ/SPY, long-only)

All 5 validators pass for the primary QQQ config. Scope is narrower than
"works everywhere" — per RESEARCH_LOOP.md Step 6 guidance, a
narrower-but-honest accepted strategy is kept live with its scope
documented rather than rejected outright: **do not deploy/paper-trade this
strategy against crypto symbols or during high realized-vol regimes** — the
grid shows it fails there. Equity/low-mid-vol only.
