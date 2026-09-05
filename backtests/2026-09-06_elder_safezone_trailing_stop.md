# Elder SafeZone Stop — trailing exit on EMA-trend breakout (2026-09-06)

**Hypothesis id:** 2026-09-06-118
**Strategy file:** `strategies/2026-09-06_elder_safezone_trailing_stop.py`
**Source:** https://pineify.app/algorithmic-trading/elder-safezone-stop (Dr. Alexander Elder's SafeZone Stop concept; ICE Data Services eSignal reference implementation cited on the page)

## Hypothesis

Dr. Alexander Elder's SafeZone Stop estimates directional market "noise" as
the average recent counter-trend penetration (for longs: `average(max(previous_low - current_low, 0))`
over a lookback window), then trails a stop `factor` × that noise below the
reference price, moving only in the tightening direction. Because it adapts
to counter-trend penetration specifically (not overall range like ATR), it
should sit tighter in smooth trends and widen automatically in choppy ones.
Tested here as the exit mechanism for a simple EMA-trend breakout entry
(long when close > 50-EMA and price makes a new N-day high), held until the
SafeZone trailing stop is hit, the trend EMA flips, or a time-stop.

First Elder SafeZone strategy in this repo — distinct from all previously
tested Elder-family strategies (Elder-Ray Bull/Bear Power, Force Index,
Impulse System, Triple Screen) since none of those use a noise-adaptive
trailing stop as the exit rule.

## Step 6 — Grid test summary

`param_grid={sz_factor:[1.5,2.5,3.5], breakout_window:[10,20], trend_span:[50]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01..2026-09-01.

- Overall pass_fraction = 19/72 = 0.264
- by_asset_class: equity 19/36 (0.528), crypto 0/36 (0.0) — decisive crypto rejection
- by_vol_regime: low 12/24 (0.5), mid 6/24 (0.25), high 1/24 (0.042) — edge concentrated in low/mid-vol, degrades sharply in high-vol (consistent with a trend-breakout entry whipsawing in choppy/high-vol conditions)
- best_cell (single low-vol tercile): QQQ sz_factor=1.5/breakout_window=20 Sharpe=1.98
- Full-sample sweep across QQQ configs (sz_factor × breakout_window): Sharpe ranges 1.07–1.98 in low-vol tercile; full-sample (all regimes combined) best config was sz_factor=2.5/breakout_window=10.

## Step 7 — Single-config validators (QQQ, sz_factor=2.5, breakout_window=10, trend_span=50)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.113 | ≥ 1.0 | ✅ |
| Max drawdown | 8.47% | ≤ 25% | ✅ |
| Transaction cost survival (10bps/trade, 159 trades) | net Sharpe 0.739 | ≥ 0.5 | ✅ |
| Walk-forward (4 contiguous windows, manual fallback — `vectorbt.utils.splitting.RangeSplitter` broken in this env, same known bug as prior iterations) | 4/4 = 100% | ≥ 75% | ✅ |
| Parameter sensitivity (6-cell sweep, relative std) | 0.039 | ≤ 0.5 | ✅ |

**All 5 validators pass for QQQ.** SPY same config: Sharpe 0.839 (fail), MDD 9.05% (pass), TC net Sharpe 0.339 (fail), WF 3/4=0.75 (pass), param-sensitivity 0.164 (pass) — SPY fails on Sharpe + TC-survival.

## Decision: **ACCEPT — QQQ only**

Scope: QQQ, sz_factor=2.5, breakout_window=10, trend_span=50, max_hold_days=40 (default).
SPY does not qualify at this config (fails Sharpe + TC-survival). Crypto (BTC/USDT, ETH/USDT)
rejected decisively — 0/36 grid cells passed. Edge is concentrated in low/mid volatility
regimes; degrades in high-vol (1/24 grid cells passing), consistent with a breakout entry
whipsawing when markets are choppy.

## Notes for future iterations

- SPY near-miss (Sharpe 0.839) could potentially be revisited with a tighter sz_factor or
  a volatility-regime gate excluding high-vol periods (similar to the 2026-09-03
  BB-meanrev regime filter pattern already in this repo).
- The manual walk-forward fallback (contiguous 4-way date split, Sharpe>0 per split) is
  used because `vectorbt.utils.splitting.RangeSplitter` is broken in this environment's
  vectorbt==1.1.0 — a scaffold-level bug documented since 2026-09-03, unfixed.
