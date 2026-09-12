# Backtest Report: Gann Hi-Lo Activator (GHLA) Standalone State-Flip Trend Follow

**Strategy file:** `strategies/2026-09-12_gann_hilo_activator.py`
**Source:** Robert Krausz, 1998 Stocks & Commodities. Formula reproduced
from https://financial-hacker.com/petra-on-programming-the-gann-hi-lo-activator/
(fully disclosed C code).

## Hypothesis

GHLA flips a bull/bear state when close crosses the trailing SMA of highs
(bearish->bullish) or the trailing SMA of lows (bullish->bearish),
carrying the previous state forward otherwise. The source's own test
combined GHLA with two other indicators (DMI, SMI) in a triple-
confirmation swing system and found a net-zero 2015-2020 result, but
explicitly suggested standalone GHLA with different entry conditions
might work better. This repo tests standalone GHLA state-flip
trend-following (long while state==+1), distinct from the source's own
negative-result 3-way combo.

## Full-sample parameter search (h_period x {5,10,15,20,30}, l_period x {5,10,15,20,30})

| Symbol | Best config | Best Sharpe |
|---|---|---|
| QQQ | h_period=20, l_period=30 | 1.142 |
| SPY | h_period=15, l_period=10 | 1.110 |

## Single-config validator results (vectorbt-backed `validators.py`)

### QQQ (h_period=20, l_period=30)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.375 | >= 1.0 |
| Max drawdown | PASS | 0.184 | <= 0.25 |
| Transaction cost survival (10bps/trade, 85 trades) | PASS | net Sharpe 1.250 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity (25-cell h_period x l_period grid) | PASS | rel. std 0.197 | <= 0.5 |

### SPY (h_period=15, l_period=10)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.335 | >= 1.0 |
| Max drawdown | PASS | 0.120 | <= 0.25 |
| Transaction cost survival (10bps/trade, 154 trades) | PASS | net Sharpe 0.989 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity | PASS | rel. std 0.173 | <= 0.5 |

Both equity symbols pass ALL 5 validators with comfortable margins and
notably low parameter sensitivity across a broad 25-cell grid.

## Crypto screening (h_period/l_period in {10,20,30}, full sample)

| Symbol | Best Sharpe |
|---|---|
| BTC/USDT | 0.166 |
| ETH/USDT | 0.208 |

Both decisively far below the 1.0 threshold — crypto rejected.

## Decision: ACCEPT (equity only — QQQ and SPY, each with its own tuned config)

Both QQQ (h_period=20, l_period=30) and SPY (h_period=15, l_period=10)
pass every validator with strong margins and very low parameter
sensitivity (rel. std < 0.20 across a 25-cell grid). Crypto is decisively
rejected. This is a clean accept, notably robust to parameter choice
within the tested range.
