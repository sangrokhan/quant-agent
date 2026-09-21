# Backtest Report: Bullish TriStar Doji Reversal

**Strategy file:** `strategies/2026-09-21_tristar_doji_bullish_reversal.py`
**Knowledge base id:** 2026-09-21-247

## Hypothesis

Per QuantifiedStrategies.com's "Bullish TriStar Doji Candlestick Pattern"
(https://www.quantifiedstrategies.com/bullish-tristar-doji-candlestick-pattern/),
3 consecutive doji candles in a downtrend signal peak indecision. Source's
own rule: entry confirmed by a close breaking above the pattern's high,
stop below the pattern's low, risk-reward >= 1:2.

## Single-config validation (best grid cell: trend_lookback=10, doji_body_pct=0.15, reward_ratio=1.5)

| Symbol | Trades | Sharpe | MDD | TC-survival |
|---|---|---|---|---|
| QQQ | 0 | undefined | 0.0 | undefined |
| SPY | 2 | 0.610 (fail, near-miss) | 0.010 (pass) | 0.559 (pass) |
| BTC/USDT | 4 | -0.315 (fail) | 0.175 (pass) | -0.326 (fail) |
| ETH/USDT | 2 | 0.485 (fail, near-miss) | 0.025 (pass) | 0.475 (fail, borderline) |

## Grid summary (Step 6)

Grid: `trend_lookback in {10,20} x doji_body_pct in {0.10,0.15,0.20} x
reward_ratio in {1.5,2.0,3.0}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction: 0.056 (12/216)**
- by_asset_class: equity 12/108 (11%), crypto 0/108 (decisive fail)
- by_vol_regime: low 0/72, mid 12/72 (17%), high 0/72
- best_cell: SPY, mid-vol regime, Sharpe 1.207 -- but full-sample SPY
  (2 trades) is only 0.610.

## Decision

**Rejected.** The 3-consecutive-doji requirement is too rare a conjunction
to trade meaningfully (0-4 trades per symbol over 7+ years). Every metric
is statistically unreliable at this sample size, and the full-sample
Sharpe fails on every symbol that has any trades at all.
