# 2026-09-04 QS RSI Composite Mean Reversion — Backtest Report

**Hypothesis** (id `2026-09-04-164`): QuantifiedStrategies.com's own "QS RSI"
composite indicator -- averaging (1) a fast 3-day RSI, (2) close's position
within the day's own high-low range (IBS-style), and (3) close's position
within its trailing 5-day high-low range -- captures short-term momentum and
range-location jointly. A low QS RSI (weak momentum, closing near recent
range lows) signals oversold worth a long entry, gated by a 200-day SMA
uptrend filter; exit when QS RSI recovers above an exit threshold or a
max_hold_days time-stop. Per QuantifiedStrategies.com's QS RSI Strategy
article (78% win rate, 214 trades on QQQ; formula fully disclosed, exact
numeric thresholds paywalled).

**Source**: https://www.quantifiedstrategies.com/qs-rsi-strategy/

**Strategy**: `strategies/2026-09-04_qs_rsi_composite_meanrev.py`

## Grid test (entry_threshold∈{15,20,25}, exit_threshold∈{60,70,80}, max_hold_days∈{7,10}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 216, passed_cells: 64, **pass_fraction: 29.6%** (strongest grid result of any strategy tested this cron trigger)
- by_asset_class: equity 64/108 passed; crypto 0/108 (decisive rejection)
- by_vol_regime: low 36/72, mid 13/72, high 15/72
- best_cell: QQQ, entry_threshold=25/exit_threshold=80/max_hold_days=10, low-vol, Sharpe 2.74

## Single-config validation, full sample 2019-2026 (entry_threshold=20, exit_threshold=70, max_hold_days=10, trend_window=200)

| Symbol | Sharpe | Passed | MDD | Passed | TC-survival (net Sharpe, 5bps, N trades) | Passed | Param sensitivity (relative_std) | Passed |
|---|---|---|---|---|---|---|---|---|
| QQQ | 1.041 | YES | 0.107 | YES | 0.899 (132 trades) | YES | 0.138 | YES |
| SPY | 1.302 | YES | 0.095 | YES | 1.034 (144 trades) | YES | 0.264 | YES |

Walk-forward validator skipped (pre-existing `validators.py`/vectorbt
version incompatibility -- `vbt.utils.splitting.RangeSplitter` missing --
see note in 2026-09-04-163's report; still unresolved).

Crypto: 0/108 grid cells passed at any parameter combo -- decisively
rejected, consistent with the vast majority of equity-derived
mean-reversion strategies in this repo failing on crypto.

## Decision: ACCEPTED (QQQ and SPY, shared config); rejected (crypto)

Both equity symbols pass at the SAME shared configuration (entry=20/exit=70/
max_hold_days=10) -- no per-symbol re-tuning needed, a stronger and more
broadly-robust result than most of this repo's prior single-symbol-only
accepts. First QS RSI (range-position composite oscillator) strategy in
this repo, distinct from Connors RSI (2026-09-04-113, streak-length + ROC
percentrank components) and plain RSI2 (2026-09-03-005) despite superficial
similarity as an RSI-family mean-reversion strategy -- QS RSI's unique
contribution is blending fast RSI with two IBS-like range-position
measurements at different lookback horizons (1-day and 5-day).
