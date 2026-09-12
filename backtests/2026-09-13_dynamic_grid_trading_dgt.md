# Dynamic Grid-based Trading (DGT), daily-bar adaptation

**Strategy file:** `strategies/2026-09-13_dynamic_grid_trading_dgt.py`
**Hypothesis id:** 2026-09-13-039

## Source

Chen, Chen & Jang, "Dynamic Grid Trading Strategy: From Zero Expectation
to Market Outperformance" (arXiv:2506.11921, June 2025), read this
iteration via browser_exec (full HTML text). First grid-trading strategy
of any kind tested in this repo.

Core mechanism: unlike a traditional grid strategy that TERMINATES (and
is proven to have zero expected value under a random-walk assumption)
when price exits the grid's bounds, DGT instead RESETS the grid
(re-centers on the current price) on every boundary breach -- liquidating
to cash if price broke above the top, or treating the position as fully
invested and using the accumulated grid arbitrage profit as new principal
if price broke below the bottom.

Daily-bar adaptation: grid-level crossings are approximated using each
day's high/low range rather than true 1-minute granularity (the paper's
own backtest uses 1-minute BTC/ETH bars); this repo's hourly-native
loader data is resampled to daily OHLC.

## Full-sample parameter sweep (BTC/USDT, 2019-2026)

`n_grids` in [4,5,6,7,8,10,14] x `grid_size` in [0.01-0.05] x `m_above` in
[2,3,4,5], ~50 combos tested across two rounds:

| n_grids | grid_size | m_above | Sharpe | MDD |
|---|---|---|---|---|
| 4 | 0.04 | 4 | 0.955 (best) | 0.766 (fails badly) |
| 6 | 0.035 | 3 | 0.946 (best balanced) | 0.470 |
| 6 | 0.03 | 3 | 0.834 | 0.473 |

No configuration found clears BOTH the Sharpe>=1.0 threshold AND the
MDD<=0.25 cap simultaneously. The best balanced near-miss (n_grids=6,
grid_size=0.035, m_above=3) reaches Sharpe 0.946 but MDD 0.470 (nearly
2x the cap); configs with even higher Sharpe (n_grids=4, m_above=4) have
so little downside buffer (only 1 grid level below center) that MDD
balloons to 0.766.

## Outcome

**Rejected -- persistent near-miss on Sharpe, decisive fail on MDD.**
The daily-bar granularity approximation (vs. the paper's native 1-minute
data) likely understates the true arbitrage-capture frequency the DGT
mechanism relies on, while the MDD exposure from being fully invested
during extended downtrends (per the "hold through lower-bound breaches"
design) is a structural feature of the mechanism, not a parameterization
artifact -- reducing grid_size or n_grids trades Sharpe for MDD along a
consistent frontier that never crosses both thresholds simultaneously in
this repo's daily-bar sample. Not pursued further given the fundamental
granularity mismatch between this repo's daily loaders and the paper's
1-minute design; logging this as a genuinely tested-and-rejected first
attempt at a grid-trading mechanism, should a future iteration have
access to intraday data.
