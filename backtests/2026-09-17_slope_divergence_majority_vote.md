# Backtest Report: Slope Divergence (Majority-Vote Stochastic/Price Slope)

**Strategy file:** `strategies/2026-09-17_slope_divergence_majority_vote.py`
**Source:** https://traders.com/documentation/feedbk_docs/2014/06/traderstips.html
(TASC June 2014 Traders' Tips, "Slope Divergence: Capitalizing On
Uncertainty" by Perry J. Kaufman; MetaStock formula credited to William
Golson/MetaStock Technical Support; read this iteration via `browser_exec`).

## Hypothesis

Compute a raw stochastic %K of price over `stoch_period` (25 in the
source). Take the linear-regression slope of that stochastic over 3
different short lookbacks (5, 12, 14 bars), and the slope of price (close)
over the SAME 3 lookbacks. Long entry fires when a majority (>=2 of 3) of
the momentum slopes are NEGATIVE while a majority of the price slopes are
POSITIVE -- price still rising while underlying stochastic-momentum turns
down across multiple windows. Exit when either all 6 slopes turn positive
or all 6 turn negative (full directional agreement). Distinct from repo's
existing single-indicator divergence entries via the majority-vote,
multi-window construction.

## Grid test summary (Step 6)

`param_grid={"stoch_period": [15,25,35]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01.

- **total_cells:** 36, **passed_cells:** 11, **pass_fraction:** 0.306
- **by_asset_class:** equity 9/18 (0.5), crypto 2/18 (0.111)
- **by_vol_regime:** low 7/12 (0.583), mid 4/12 (0.333), high 0/12 (0.0)
- **best_cell:** stoch_period=15, QQQ, low-vol regime, Sharpe=2.76
- **worst_cell:** stoch_period=25, SPY, high-vol regime, Sharpe=-0.58

## Single-config validators (Step 7) — best grid config: stoch_period=15

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.412 | **PASS** 1.152 |
| Max Drawdown (<=0.25) | PASS 0.124 | PASS 0.098 |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **PASS** 0.963 (166 trades) | **PASS** 0.635 (164 trades) |
| Walk-forward (manual 4-way contiguous split; `check_walk_forward`'s vectorbt `RangeSplitter` API absent — manual fallback per repo convention) | PASS 1.0 (4/4) | PASS 1.0 (4/4) |
| Parameter sensitivity (relative std <=0.5, 3-cell stoch_period sweep) | PASS 0.115 | PASS 0.187 |

## Decision: ACCEPT (equity only: QQQ, SPY)

All 5 validators pass on both QQQ and SPY at stoch_period=15. Higher trade
frequency (164-166 round trips over 7.5 years) keeps net-of-cost Sharpe
somewhat compressed vs gross (especially SPY: 1.15 -> 0.63) but still
clears the 0.5 net-Sharpe floor comfortably. Crypto (BTC/USDT, ETH/USDT) is
explicitly OUT OF SCOPE: the grid shows only 2/18 crypto cells passing, and
high-vol regimes fail entirely across the board (0/12) -- this strategy
should be read as a calm/normal-vol equity strategy, not a broadly robust
one.
