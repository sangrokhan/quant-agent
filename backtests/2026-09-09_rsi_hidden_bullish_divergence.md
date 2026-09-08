# RSI Hidden Bullish Divergence — QQQ/SPY/BTC/ETH

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_rsi_hidden_bullish_divergence.py`
**Outcome:** REJECTED (all symbols, decisive)

## Hypothesis

Per AlchemyMarkets' "Hidden Bullish Divergence Comprehensive Guide"
(https://alchemymarkets.com/education/strategies/hidden-bullish-divergence/):
in an established uptrend, a pullback swing low where PRICE forms a HIGHER
low while RSI forms a LOWER low is a trend-continuation signal ("hidden"
divergence), as opposed to REGULAR/classic divergence (price lower low +
oscillator higher low) which signals reversal. This is the mirror-image
construction of every divergence strategy previously tested in this repo
(all classic/regular divergence: 2026-09-03-019 RSI, 2026-09-04-088 OBV,
2026-09-05-047 CMF, 2026-09-05-048 Force Index, 2026-09-05-057 RVI,
2026-09-04-160 AO Twin Peaks) -- never tested here before.

## Grid test (Step 6)

`param_grid`: swing_lookback in [3, 5, 8], max_hold_days in [10, 15, 20]
`symbols`: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
`vol_regime_splits`: 3
Total cells: 108, passed: 5, **pass_fraction: 0.046**

By asset class: equity 5/54, crypto 0/54 (decisive).
By vol regime: low 4/36, mid 1/36, high 0/36.
Average Sharpe per param combo (equity) ranged from -0.24 to +0.28, none
consistently positive -- no combo shows a robust edge.
Best cell: swing_lookback=5/max_hold_days=10, SPY, mid-vol, Sharpe 1.31
(isolated, not representative of the combo's average -0.03).
Worst cell: swing_lookback=5/max_hold_days=20, SPY, high-vol, Sharpe -1.54.

## Single-config validation (Step 7), best-pass-count config swing_lookback=5/max_hold_days=10

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | -0.379 (FAIL) | 0.209 (FAIL) | >= 1.0 |
| Max drawdown | 0.184 (PASS) | 0.116 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | -0.434 net Sharpe (FAIL) | 0.125 net Sharpe (FAIL) | >= 0.5 |

Trade counts very low (15 QQQ / 17 SPY over 7.5yr) -- the swing-pivot +
divergence-confirmation construction is a rare-signal setup, and full-sample
Sharpe is decisively negative or near-zero on both symbols. Walk-forward
and parameter sensitivity were skipped given the decisive Sharpe/TC failure
already disqualifies the strategy (consistent with RESEARCH_LOOP.md Step 7
guidance to run at minimum Sharpe + MDD, and skip further validators when
time/compute isn't warranted by a near-miss).

## Decision

**REJECTED (decisive).** Full-sample Sharpe fails on both symbols (-0.38
QQQ, 0.21 SPY vs 1.0 threshold), grid pass_fraction only 0.046 with no
param combo showing a consistently positive average Sharpe across vol
regimes, and crypto rejected decisively 0/54. The swing-pivot detection +
divergence-confirmation construction produces too few, too weak signals to
clear this repo's thresholds -- the theoretical mechanism (absorption of
selling pressure during a pullback) doesn't translate into an exploitable
mechanical daily-bar edge in this backtest.

## Source

https://alchemymarkets.com/education/strategies/hidden-bullish-divergence/
