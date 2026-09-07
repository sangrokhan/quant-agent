# Backtest Report: Bullish Engulfing (Volume-Confirmed) — 2026-09-08

## Hypothesis

Bullish Engulfing candlestick pattern (Day1 bearish, Day2 bullish, Day2 body
fully engulfs Day1 body), gated by close > SMA200 uptrend filter AND a
volume-expansion confirmation on the engulfing candle
(volume >= volume_ratio * mean(volume over preceding vol_lookback_days)).

Source: https://tradingstrategyguides.com/complete-guide-to-the-bullish-and-bearish-engulfing-candle-strategy/
("Volume expansion on the engulfing candle significantly increases the
probability of a genuine trend reversal"; "the volume on the second candle
must be noticeably higher than the volume of the preceding 3-5 candles").

Distinct from prior id=2026-09-04-102 (plain Bullish Engulfing + SMA200,
rejected, notes said "likely needs a confirming ... extreme-reading input")
by adding exactly this volume-confirmation gate.

## Single-config metrics (QQQ, best grid cell: vol_lookback_days=3, volume_ratio=1.3)

| Metric | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | -0.199 | >= 1.0 | FAIL |
| Max drawdown | 3.8% | <= 25% | PASS |
| Net Sharpe after costs (10bps/trade, 4 trades) | -0.238 | >= 0.5 | FAIL |

Only 4 trades over the full 2018-09-01 window — the volume-confirmation
gate is extremely restrictive on top of the already-strict engulfing
pattern, making the sample statistically very thin.

## Step 6 grid summary (param x symbol x vol-regime)

- Grid: vol_lookback_days in [3,5], volume_ratio in [1.3, 1.5, 2.0],
  symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3.
- **72 total cells, 0 passed (pass_fraction 0.0)** — decisive rejection.
- By asset class: equity 0/36, crypto 0/36.
- By vol regime: low 0/24, mid 0/24, high 0/24.
- Best cell: QQQ, vol_lookback_days=3, volume_ratio=1.3, mid-vol regime,
  Sharpe 0.476 (still below the 1.0 threshold).
- Worst cell: SPY same params, mid-vol regime, Sharpe -0.739.

## Validators run (full sample QQQ, best grid config)

- Sharpe: FAIL (-0.199 vs 1.0)
- Max drawdown: PASS (3.8% vs 25%) — trivial to pass given how rarely the
  strategy trades.
- Transaction cost survival: FAIL (-0.238 net Sharpe vs 0.5 threshold)
- Walk-forward: not run — decisive full-sample and grid failure already
  makes this uninformative (workload=normal, but grid pass_fraction=0.0
  is conclusive).
- Parameter sensitivity: not separately run — grid IS the parameter sweep;
  relative std is high (best cell 0.476 vs decisively negative cells
  elsewhere), i.e. fails on inspection.

## Decision: REJECTED

Adding the volume-confirmation gate that the source itself recommends did
not rescue the plain Bullish Engulfing idea (2026-09-04-102) — if anything
it performed *worse* on full-sample Sharpe than the ungated version, likely
because the extra filter cuts trade count to near-zero (4 trades over 8+
years on QQQ) without improving per-trade quality. This further supports
the notes from -102: single/two-candle patterns, even with a volume
confirmation layer, do not show standalone statistical edge in this
repo's daily-bar equity/crypto universe.
