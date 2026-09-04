# Backtest Report: Inside Bar Breakout with EMA Trend Filter

**Strategy file:** `strategies/2026-09-04_inside_bar_breakout_trend.py`
**Hypothesis ID:** 2026-09-04-090

## Hypothesis

An Inside Bar (IB) is a bar fully contained within the prior "Mother Bar"
(MB): high[t] <= high[t-1] AND low[t] >= low[t-1] -- signaling a
consolidation pause. Per StrategyQuant/Secuora/TradingView guides: enter
long on breakout above the Mother Bar's high, gated by an EMA trend filter
(price above the EMA), with the setup expiring if breakout doesn't trigger
within N bars of the inside bar forming. Approximated for daily OHLCV (no
intrabar stop orders) as a close-above-MB-high trigger within
`breakout_expiry_bars`, exit on trend-filter break or `max_hold_days`.

Source: https://www.google.com/search?q=inside+bar+breakout+trading+strategy+concrete+rules+backtest
(Google AI-overview + StrategyQuant/Secuora/TradingView snippets)

## Single-config validator results (QQQ, ema_window=50/breakout_expiry_bars=2/max_hold_days=20 -- best full-sample config found)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.809 | 1.0 |
| Max drawdown | ✅ | 0.219 | 0.25 |
| Transaction cost survival (10bps/trade, 41 trades) | ✅ | net Sharpe 0.737 | 0.5 |

Walk-forward / parameter-sensitivity not run since Sharpe already fails at
the full-sample level (Step 7 minimum: Sharpe + MDD).

## Step 6 grid summary (ema_window ∈ {20,50}, breakout_expiry_bars ∈ {2,3}, max_hold_days ∈ {10,20}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 96, passed_cells: 13, pass_fraction: 0.135
- by_asset_class: equity 13/48, crypto 0/48
- by_vol_regime: low 11/32, mid 2/32, **high 0/32**
- best_cell: SPY, ema_window=50/breakout_expiry_bars=3/max_hold_days=20, low-vol regime, Sharpe 2.27
- worst_cell: SPY, ema_window=50/breakout_expiry_bars=3/max_hold_days=20, high-vol regime, Sharpe -1.50 (same param set, opposite regime -- large regime-dependent swing)

**Interpretation:** grid passes concentrate almost entirely in the low-vol
tercile and vanish in high-vol (0/32) -- opposite of the just-tested IBS
strategy (2026-09-04-089, which needed high-vol). Consolidation-breakout
logic apparently only works in calm markets where breakouts are cleaner
signals, not noisy high-vol whipsaw. However, full-sample Sharpe (blending
all regimes) never clears 1.0 for any tested config on either SPY or QQQ --
the low-vol edge isn't strong enough to carry the whole sample period.
Crypto rejected decisively (0/48 grid cells).

## Decision

**REJECT (all assets/configs).** Best full-sample config (QQQ,
ema_window=50/breakout_expiry_bars=2/max_hold_days=20) Sharpe 0.809, below
the 1.0 threshold, despite passing max drawdown (0.219) and
transaction-cost survival (0.737) comfortably on only 41 trades over
7.7yr. No tested config on SPY/QQQ clears 1.0 full-sample. Grid
pass_fraction 0.135, concentrated entirely in low-vol regime (0/32 high-vol
passes). Crypto rejected decisively (0/48 grid cells). A future loop could
try an explicit low-vol-regime-only filter (mirroring the successful
KVO-min-hold and IBS high-vol-only findings) as the next targeted fix, since
this strategy's edge -- unlike most others tested in this repo -- appears
concentrated in LOW-vol conditions specifically.
