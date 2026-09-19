# SMA-Crossover with Self-Paced Hold (hold_days = sma_window) — ACCEPTED (SPY only)

**Hypothesis:** Per QuantifiedStrategies.com's "Simple Moving Average
Trading Strategy: Backtest, Trading Rules And Statistics"
(https://www.quantifiedstrategies.com/simple-moving-average-trading-strategy/),
the source's own disclosed finding: "The highest average gain per trade
was observed when buying after the price crosses above the 200-day SMA
and HOLDING FOR 200 DAYS" (10.93% avg per trade). This pairs the hold
period exactly to the SMA's own lookback window — a specific,
source-highlighted combination distinct from every other SMA-crossover
strategy in this repo (which either exit on the opposite crossover or
use an independently-tuned fixed time-stop unrelated to the indicator's
own window). First strategy in this repo using this "hold period tied
to the indicator's own lookback" construction.

## Step 6 — Grid test summary

Grid: `sma_window` in {50, 100, 150, 200} (hold_days mechanically pinned
to sma_window per the source's rule), symbols equity={SPY,QQQ}
crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3. 48 total cells.

- `pass_fraction`: 13/48 = **0.271**
- `by_asset_class`: equity 13/24 passed, crypto 0/24 passed
- `by_vol_regime`: low 8/16, mid 4/16, high 1/16
- `best_cell`: sma_window=50, SPY, low-vol regime, Sharpe=2.675
- `worst_cell`: sma_window=100, SPY, mid-vol regime, Sharpe=-0.180

Full-sample sweep found QQQ sma_window=100 gives Sharpe 1.112 (passes
Sharpe/tx-cost/walk-forward/param-sensitivity) but FAILS max drawdown
(0.292 > 0.25 threshold) — decisively rejected on that validator alone
despite otherwise strong metrics. SPY sma_window=50 gives Sharpe 1.021
and clears all 5 validators including MDD (0.236, just under the 0.25
ceiling).

## Step 7 — Single-config validation (full sample 2018-01 to 2026-09)

### SPY, sma_window=50 (21 trades)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.021 | >= 1.0 | pass |
| Max drawdown | 0.236 | <= 0.25 | pass |
| Tx-cost survival (10bps/trade, 21 trades) | net Sharpe 1.000 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | pass_fraction 1.0 | >= 0.75 | pass (4/4 splits positive) |
| Parameter sensitivity (4-value sma_window sweep, SPY) | relative_std 0.068 | <= 0.5 | pass |

**All 5 validators pass on SPY.** Notably low trade count (21 over
~8.7 years) since positions only open on discrete crossover events with
non-overlapping holds — very low turnover, which helps tx-cost survival
substantially (net Sharpe barely below gross).

### QQQ, BTC/USDT, ETH/USDT, same construction

QQQ at its own best config (sma_window=100, Sharpe 1.112) fails ONLY
max drawdown (0.292 vs 0.25 threshold) — a genuine near-miss, not a
decisive rejection; a future loop could explore a volatility-scaled
position size or an early-exit stop-loss overlay to cut QQQ's drawdown
without abandoning the core self-paced-hold mechanism. Crypto
decisively rejected in the grid (0/24 cells) — a 50-200 day fixed hold
is far too slow for crypto's regime-shifting volatility.

## Decision: ACCEPTED (SPY only, sma_window=50)

All 5 validators pass for SPY. QQQ is a genuine near-miss (drawdown-only
failure at its own best config) worth revisiting with a risk overlay;
crypto is decisively rejected. Strategy file kept live in `strategies/`
for SPY scope only.

Source: https://www.quantifiedstrategies.com/simple-moving-average-trading-strategy/.
