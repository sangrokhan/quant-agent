# Crypto Weekend Effect (Friday-Monday hold) — Backtest Report (2026-09-04-029)

**Hypothesis:** Per QuantifiedStrategies.com's Bitcoin weekend-effect
article (https://www.quantifiedstrategies.com/weekend-effect-in-bitcoin/):
BTC/ETH tend to show positive price movement from late Friday through
late Monday (24/7 crypto market, reduced institutional weekend
volume/liquidity drives retail-driven upward drift). Source's own
(paywalled/undisclosed exact rules) premium strategy backtest reports BTC
avg gain 2.6%/trade, win rate 60%, MDD 19%; ETH avg gain 2.2%/trade, win
rate 53%. Implemented here as the literal qualitative rule: long from
Friday's daily close through Monday's daily close (position held through
Sat+Sun bars).

## Full-sample sanity check (BTC/USDT, ETH/USDT, 2019-2026, 400 trades each)

| Symbol | entry_weekday | hold_days | Sharpe |
|---|---|---|---|
| BTC/USDT | Fri | 2 | 0.117 |
| BTC/USDT | Fri | 3 | 0.117 |
| BTC/USDT | Sat | 2 | 0.038 |
| BTC/USDT | Sat | 3 | 0.130 |
| ETH/USDT | Fri | 2 | 0.132 |
| ETH/USDT | Fri | 3 | 0.119 |
| ETH/USDT | Sat | 2 | 0.069 |
| ETH/USDT | Sat | 3 | 0.134 |

All 8 configs tested on the actual target assets (BTC/USDT, ETH/USDT)
cluster near-zero Sharpe (0.04-0.13), decisively below the 1.0 threshold
-- no full validator suite run given the unambiguous magnitude of the
shortfall (Step 7 guidance: run at minimum Sharpe+MDD; skip the rest when
already decisively failing).

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `entry_weekday x {Fri,Sat}`, `hold_days x {2,3}`, symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 48 cells total.

- pass_fraction: 0.167 (8/48), but ALL passing cells are on EQUITY
  (QQQ/SPY), which is expected noise since equity's weekday-only trading
  calendar means this position rule degenerates to something close to a
  generic Friday-only exposure there -- not evidence for the crypto
  hypothesis this iteration actually tested.
- crypto (the asset class the hypothesis is actually about): **0/24
  passing cells**, consistent with the full-sample sanity check above.

## Decision: **REJECTED**

Full-sample Sharpe on BOTH target crypto assets (BTC/USDT, ETH/USDT)
across all 4 parameter combinations tested clusters near zero (0.04-0.13),
decisively failing the 1.0 Sharpe threshold. The equity-side grid passes
are not meaningful evidence for this hypothesis (the mechanism is
explicitly crypto-native per the source; equity has no weekend bars to
capture). A likely confound: the source's exact numeric rule is paywalled
(strategy #96) and almost certainly narrower/more selective than "hold
every single weekend" (e.g. a specific hour-of-day entry/exit, a
volatility or volume filter, or a specific subset of weekends) --
implementing the qualitative description literally (every Friday-Monday,
unconditionally) is far too broad/naive relative to what the source
likely actually tested, given their own reported low ~9-10% time-invested
figure vs this implementation's ~43% time invested (3/7 days every week).

Future loop idea: this qualitative "weekend effect" premise is directionally
plausible (source's own claimed statistics, if genuine, are strong) but
the paywalled exact rule is the real blocker -- a future loop could try
gating entries to only the LOWEST-liquidity/volume weekends (closer to the
source's ~10% time-invested selectivity) rather than every weekend
unconditionally, or search for a non-paywalled source with the exact
numeric rule (e.g. Santiment's day-of-week backtest, also surfaced in this
search, reports Monday/Saturday as top days by average return -- a
narrower single-day rule rather than a full Friday-Monday hold).
