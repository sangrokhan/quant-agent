# 2026-09-07: Three Black Crows Contrarian Reversal (SPY/QQQ/BTC/ETH)

## Hypothesis
The classic "Three Black Crows" bearish reversal candlestick pattern (three
consecutive long bearish candles, each opening within the prior candle's
real body, each closing at a new lower low, with little/no lower wicks,
occurring after an established uptrend) typically marks a sharp,
potentially overextended short-term selloff. Tested CONTRARIAN: go long at
the close of the third crow (gated by close>SMA200 at pattern start), exit
on a close back above the 3-bar pattern high or a `max_hold_days` time-stop.

Source: https://quantstrategy.io/blog/understanding-the-three-black-crows-candlestick-pattern-for-successful-trading/
(mechanical shape criteria used directly; no numeric backtest published by
the source itself — this repo supplies the actual backtest).

Distinct from 2026-09-05-051 (Heikin-Ashi N-red-candle contrarian, looser
"N consecutive red" rule on smoothed candles) — here we use raw OHLC and the
literature-documented strict shape rule (body containment, monotonic lower
closes, small lower wicks).

## Strategy file
`strategies/2026-09-07_three_black_crows_reversal.py`

## Grid test (Step 6)
`param_grid={"min_body_ratio": [0.3, 0.5, 0.7], "max_hold_days": [5, 8, 12]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **72 total cells, 3 passed (pass_fraction = 0.0417)**
- By asset class: equity 3/54 passed, **crypto 0/18 (complete failure)**
- By vol regime: low 0/18, mid 0/18, **high 3/18** (only high-vol slices
  passed at all), n/a (empty/no-trade slices) 0/18
- Best cell: `min_body_ratio=0.3, max_hold_days=8`, SPY, high-vol regime,
  Sharpe 1.198
- Worst cell: `min_body_ratio=0.3, max_hold_days=5`, SPY, mid-vol regime,
  Sharpe -1.101

The pattern is genuinely rare with the strict shape rule (containment +
monotonic-lower-close + small-wick criteria), so most grid cells (esp.
crypto, whose 24h candles rarely satisfy the "little/no lower wick"
condition) had few or zero completed patterns.

## Single-config validation (Step 7) — SPY, `min_body_ratio=0.3, max_hold_days=8` (grid's best cell config)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full period) | ❌ FAIL | 0.160 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 0.0347 | ≤ 0.25 |
| Transaction cost survival (10bps/trade) | ❌ FAIL | 0.149 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback — `vbt.utils.splitting` repo-wide bug, see prior iterations' notes) | ✅ PASS | 4/4 splits positive | ≥ 0.75 |
| Parameter sensitivity | ❌ FAIL | NaN (mean Sharpe ≈ 0 across the 9-combo grid, several near-zero-trade cells) | ≤ 0.5 relative std |

**Only 1 completed trade over the full 2019-2026 SPY sample** at this
config — the grid's "high-vol regime" 1.2 Sharpe cell is not a robust full-
sample edge, just one lucky trade landing in a high-vol slice. Full-period
Sharpe (0.16) and net-of-cost Sharpe (0.15) both decisively miss threshold,
and parameter sensitivity is degenerate (mean near zero, some cells have
zero trades) so relative_std is NaN/undefined -- treated as fail.

## Decision: REJECTED

Decisive rejection — pattern is too rare (strict candle-shape criteria)
to generate enough trades for a statistically meaningful edge; the one
grid cell that "passed" was a single lucky high-vol-regime trade, not a
repeatable edge. Complete failure on crypto (0/18). Not revisiting this
exact rule; a looser version already exists and was also rejected
(2026-09-05-051, Heikin-Ashi N-red-candle variant).
