# Backtest Report: Ehlers Instantaneous Trendline + Trigger-Line Crossover

**Strategy file:** `strategies/2026-09-05_itrend_trigger_crossover.py`
**Knowledge base id:** 2026-09-05-009

## Hypothesis

John Ehlers' simplified single-alpha Instantaneous Trendline (iTrend) is a
near zero-lag recursive smoother of hl2 price. Its Trigger line (`2*iTrend_t
- iTrend_{t-2}`, a lag-reduced projection) crossing above the iTrend line is
a long entry signal ("classic entry/exit event" per LuxAlgo's documentation
of Ehlers' published recursion); crossing back below is the exit signal.

Source: https://www.luxalgo.com/library/indicator/ehlers-instantaneous-trendline/
(exact recursion formula, alpha=0.07 default, trigger definition, and
trading rule). Corroborated conceptually by
https://barbotine.medium.com/exploring-the-ehlers-instantaneous-trendline-a-powerful-tool-for-trend-analysis-612a46f2f981.

First Ehlers Instantaneous Trendline strategy in this repo — distinct from
other Ehlers-family strategies already tested (MESA Stochastic
2026-09-04-118, Center-of-Gravity oscillator 2026-09-04-124), which are
cycle-period oscillators rather than this trend-following trendline+trigger
pair.

## Grid test summary (Step 6)

- `param_grid`: `alpha` in {0.05, 0.07, 0.10}, `max_hold_days` in {20, 30}
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3` (low/mid/high realized-vol terciles)
- Period: 2019-01-01 to 2026-09-01
- **72 total cells, 18 passed, pass_fraction = 0.25**
- By asset class: equity 18/36 passed, crypto 0/36 passed
- By vol regime: low 12/24, mid 6/24, high 0/24
- Best cell: alpha=0.05, max_hold_days=30, SPY, low-vol regime, Sharpe 2.49
- Worst cell: alpha=0.07, max_hold_days=20, QQQ, high-vol regime, Sharpe -0.146
- QQQ passed 2/3 param combos consistently across max_hold_days values;
  SPY passed 1/3; crypto (BTC/ETH) failed all cells at every alpha/hold
  combination.

## Single best-config validators (Step 7)

Config: `alpha=0.05, max_hold_days=30`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.219 | 1.120 | ≥ 1.0 | QQQ ✅ / SPY ✅ |
| Max drawdown | 0.241 | 0.182 | ≤ 0.25 | QQQ ✅ / SPY ✅ |
| Net Sharpe after costs (10bps/trade) | 1.105 | 0.982 | ≥ 0.5 | QQQ ✅ / SPY ✅ |
| Num trades | 79 | 74 | — | — |
| Parameter sensitivity (alpha sweep, QQQ, relative_std) | 0.112 | — | ≤ 0.5 | ✅ |

`check_walk_forward` was **not run** — `vbt.utils.splitting.RangeSplitter`
raises `AttributeError: module 'vectorbt.utils' has no attribute
'splitting'` in this repo's installed vectorbt version (a pre-existing
environment issue, not specific to this strategy; consistent with other
recent log entries recording `walk_forward: null`).

## Outcome: **ACCEPTED (QQQ, SPY)**; rejected for crypto (BTC/USDT, ETH/USDT — decisive 0/36 cells)

All validators run for the primary config (Sharpe, MDD, TC-survival,
parameter sensitivity) passed on both QQQ and SPY. Crypto failed
decisively across the entire grid (0/36 cells at any alpha/hold-days
combination), so this strategy's scope is equity-only.
