# Three Outside Down Short — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/three-outside-down-candlestick-pattern/
(read via browser_exec fallback). 3-candle bearish reversal, extension of
bearish engulfing: small bullish candle 1, large bearish engulfing candle
2, bearish confirmation candle 3 opening/closing below both prior candles'
lows/close. Source claims ~70% backtested accuracy in its own 75-pattern
study (one of the higher-reliability patterns cited) but discloses no
specific numeric stop/target -- this repo's standard ATR stop/target used.

Strategy file: `strategies/2026-09-21_three_outside_down_short.py`

## Step 6 — Grid test summary
`grid_summary_three_outside_down_short.json` /
`grid_cells_three_outside_down_short.json`

- Grid: `trend_window` in {30, 50, 100}, `small_body_max_pct` in {0.3,
  0.4, 0.5}, `target_atr_mult` in {1.5, 2.0, 3.0}; symbols QQQ/SPY
  (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3; 324 total
  cells.
- **pass_fraction: 0.0** (0/324 cells passed Sharpe>=1.0 and MDD<=0.25).
- by_asset_class: equity 0/162, crypto 0/162. by_vol_regime: low 0/108,
  mid 0/108, high 0/108.
- Best cell: QQQ, mid-vol-regime, `trend_window=50, small_body_max_pct=0.4,
  target_atr_mult=3.0`, Sharpe 0.911 -- a moderate miss (not razor-thin
  like some other iterations this cron trigger, but not clearly worth a
  rescue attempt either).
- Notably, this pattern occurs far more frequently than the other
  candlestick patterns tested this cron trigger (57 non-zero position
  bars for QQQ at default params over 2018-2026, vs single digits for
  most others), consistent with the source's claim that it is "quite
  common" -- but higher signal frequency did not translate into edge here.

## Step 7 — Single-config validation
Skipped a full validators.py run: the grid gives a decisive, uniform 0%
pass_fraction across every asset class and vol regime, and the best cell
(Sharpe 0.911) is a moderate, non-borderline miss.

## Step 8 — Decision: **REJECT**

Rejection reason: 0/324 grid cells pass; best cell (QQQ mid-vol) Sharpe
0.911, uniformly missing across every asset class and vol regime despite
this being the most frequently-occurring candlestick pattern tested this
cron trigger. The source's own claimed 70% "accuracy" (a raw hit-rate
statistic, not a Sharpe-adjusted or cost-adjusted backtest result)
evidently does not translate into a risk-adjusted trading edge once ATR
stop/target exits and realistic thresholds are applied.

Strategy file and this report are kept as a record of a rejected attempt.
