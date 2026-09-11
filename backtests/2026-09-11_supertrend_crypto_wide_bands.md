# Backtest Report: SuperTrend, Crypto-Widened ATR Bands (fix attempt)

**Strategy file:** `strategies/2026-09-03_supertrend_atr_longonly.py` (reused,
existing accepted equity strategy -- this iteration only re-grids it with
a crypto-focused wider parameter set, no new strategy file)
**Grid script:** `scripts/run_iter_supertrend_crypto_wide.py`
**Knowledge base id:** 2026-09-11-103

## Hypothesis

Direct fix attempt for `2026-09-04-053` (standard SuperTrend ATR
period=10/multiplier=3.0, accepted on QQQ/SPY but rejected decisively on
crypto, 0/54 grid cells). Per a Google AI-overview synthesis (TrendSpider/
Quantzee, visited this iteration via `browser_exec` Google SERP): "Adjusting
the SuperTrend multiplier higher during high-volatility Bitcoin regimes
widens the indicator bands to filter out market noise and prevent false
breakout signals... Increase the ATR Multiplier from 3.0 to 3.5 or 4.0... or
lengthen the ATR Period (e.g., from 10 to 14)". This iteration re-tests the
SAME existing (already-accepted-on-equity) strategy code with a wider,
crypto-tuned grid, specifically checking whether widening the bands rescues
BTC/ETH performance.

## Step 6 grid summary (`grid_test.run_strategy_grid`)

Grid: `atr_period` in {14,21} x `multiplier` in {3.5,4.0,5.0}, symbols equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, `vol_regime_splits=3`. 72 total cells.

- **pass_fraction: 0.222** (16/72)
- by_asset_class: equity 16/36, **crypto 0/36** (still decisively zero even
  at the widest tested multiplier of 5.0x)
- by_vol_regime: low 12/24, mid 4/24, high 0/24
- best_cell: `atr_period=14, multiplier=5.0`, SPY, low-vol regime, Sharpe 2.70
- worst_cell: `atr_period=14, multiplier=5.0`, QQQ, high-vol regime, Sharpe -0.96

## Decision: REJECT (crypto scope only; equity scope already live)

Widening the ATR multiplier up to 5.0x (well beyond the source's suggested
3.5-4.0x ceiling) and lengthening the ATR period to 14/21 still produces
**zero passing crypto cells out of 36** -- the same decisive rejection as
the original standard-parameter test. This is not a narrow-miss; band width
alone is not the mechanism holding SuperTrend back on BTC/ETH. No further
single-config validator run needed given the grid's unambiguous 0/36 result
(consistent with this repo's practice of skipping Step 7 when Step 6 is
already decisive).

This closes out the "does SuperTrend just need wider bands for crypto"
question definitively -- a future revisit would need a structurally
different fix (e.g. a trend-strength/ADX co-filter as already tested at
`2026-09-10-120`, or abandoning SuperTrend for crypto trend-following
entirely in favor of already-accepted crypto strategies elsewhere in this
repo).
