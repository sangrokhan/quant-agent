# Volatility-adjusted multi-horizon cross-sectional crypto momentum portfolio

**Strategy file:** `strategies/2026-09-13_crypto_vol_adj_momentum_portfolio.py`
**Hypothesis id:** 2026-09-13-037

## Source

GitHub VASUDHA-SRIPERAMBUDURU/volatility-adjusted-crypto-momentum
(https://github.com/VASUDHA-SRIPERAMBUDURU/volatility-adjusted-crypto-momentum),
full Python source read this iteration via browser_exec. Disclosed
formula: combined 7/14/30-day momentum divided by rolling 20-day
volatility, clipped to [-5,5], normalized into cross-sectional portfolio
weights (adapted long-only here per SAFETY.md), 50% exposure scale, an
additional 50% de-rate in high-volatility regimes (market avg vol above
its own 75th percentile), weekly rebalance. Source's own reported
full-period numbers: Sharpe ~1.08, MDD ~-26% (2021-2026, BTC/ETH/BNB/SOL,
yfinance data).

Architecturally distinct from this cron trigger's earlier rejected 3-way
rotation entries (2026-09-13-035/036, winner-take-all single-asset
concentration) -- this holds a WEIGHTED portfolio across BTC/ETH/SOL
simultaneously, with an explicit market-wide vol-regime de-risking overlay.

## Full-sample parameter sweep

`vol_window` in [10,20,30] x `exposure_scale` in [0.3,0.5,0.7,1.0] x
`high_vol_derate` in [0.3,0.5,0.7], 36 combos:

- Best Sharpe across the entire sweep: **0.327** (vol_window=30,
  exposure_scale=0.7, high_vol_derate=0.7) -- far below the 1.0 threshold.
- Sharpe is essentially FLAT across every exposure_scale tested (0.321
  regardless of scaling from 0.1 to 1.0) since Sharpe ratio is scale-
  invariant for a fixed-shape weighted portfolio with no risk-free-rate
  offset -- confirming this is a structural, non-fixable-by-de-leveraging
  Sharpe shortfall, not an MDD-vs-leverage tradeoff like the earlier
  SuperTrend+vol-targeting SOL success (2026-09-13-030).
- At exposure_scale=0.1 (vol_window=10, high_vol_derate=0.7), MDD drops to
  0.109 (passes) but Sharpe stays at 0.321 (decisive fail) -- confirming
  this repo's own long-only, BTC/ETH/SOL-only, daily-rebalance adaptation
  of this GitHub source's momentum/vol-ratio construction does not
  reproduce anywhere near the source's own claimed Sharpe ~1.08 (source
  uses yfinance BTC-USD/ETH-USD/BNB-USD/SOL-USD from Jan 2021, includes
  BNB, and allows short positions via signed weight normalization -- none
  of which are reproduced exactly here).

## Outcome

**Rejected -- decisive.** Sharpe fails by a wide, scale-invariant margin
(0.32 vs 1.0 threshold) across the entire parameter sweep. The long-only
adaptation (zeroing negative scores instead of shorting) and the
narrower 3-asset (vs. source's 4-asset) universe are the most likely
causes of the large gap from the source's own claimed Sharpe ~1.08 --
logged for a future iteration that might want to test the mean-reversion
short-leg contribution separately, though full long/short is out of scope
per this repo's SAFETY.md and general long-only convention.
