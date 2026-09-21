# Downside Tasuki Gap Short — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/downside-tasuki-gap-candlestick-pattern/
(read via browser_exec fallback). 3-candle bearish continuation: bearish
candle 1, bearish candle 2 gapping down below candle 1's low, bullish
candle 3 closing within the gap. Source's disclosed confirmation: a 4th
bar closing below candle 3's low triggers short entry; stop above candle
3's high; trailing stop to ride the continuation (no fixed target
disclosed).

Strategy file: `strategies/2026-09-21_downside_tasuki_gap_short.py`

## Step 6 — Grid test summary
`grid_summary_downside_tasuki_gap_short.json` /
`grid_cells_downside_tasuki_gap_short.json`

- Grid: `trend_window` in {30, 50, 100}, `trail_atr_mult` in {1.5, 2.5,
  3.5}, `max_hold_days` in {10, 15, 25}; symbols QQQ/SPY (equity),
  BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3; 324 total cells.
- **pass_fraction: 0.0** (0/324 cells passed Sharpe>=1.0 and MDD<=0.25).
- by_asset_class: equity 0/162, crypto 0/162. by_vol_regime: low 0/108,
  mid 0/108, high 0/108.
- Best cell: QQQ, mid-vol-regime, `trend_window=30, trail_atr_mult=1.5,
  max_hold_days=10`, Sharpe 0.712 -- well below the 1.0 threshold, not a
  near-miss.

## Step 7 — Single-config validation
Skipped a full validators.py run: the grid gives a decisive, uniform 0%
pass_fraction across every asset class and vol regime, and the best cell
(Sharpe 0.712) is not even a near-miss (unlike the Pennant/Bearish-Kicker
iterations this cron trigger, which had cells right at/near the 1.0
threshold) -- there is no borderline result here worth a full validator
suite.

## Step 8 — Decision: **REJECT**

Rejection reason: 0/324 grid cells pass; best cell Sharpe 0.712, a clear
miss rather than a near-miss, uniformly across every asset class and vol
regime. The 3-candle-plus-confirmation conjunction (bearish, gap-down
bearish, gap-filling bullish pullback, then 4th-bar re-confirmation) is
rare (11 non-zero position bars for QQQ over 2018-2026 at default params)
and the trades that do occur don't produce a meaningful edge.

Strategy file and this report are kept as a record of a rejected attempt.
