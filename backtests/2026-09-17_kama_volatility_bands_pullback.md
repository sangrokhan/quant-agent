# KAMA + Volatility Bands, Pullback Mode

Hypothesis: per PyQuantLab's "Adaptive MA Volatility Bands (KAMA): Pullback vs Breakout"
Medium article (confirmed via Google AI Overview synthesis this iteration, browser_exec
fallback after web_search DDGS backend returned "No results found" for multiple queries):
KAMA + std-dev volatility bands, pullback mode -- long entry when in an uptrend (close>KAMA,
KAMA slope>0) and price dips below the lower band then recovers above it; exit when close
falls below KAMA. Distinct from this repo's prior plain dual-KAMA crossover (2026-09-04-048,
no volatility bands).

## Grid summary (n_std x [1.5,2.0,2.5], band_window x [15,20], QQQ+SPY equity, BTC/USDT+ETH/USDT crypto, 3 vol terciles)
- total_cells=72, passed=0, pass_fraction=0.0 (decisive reject across all cells)
- by_asset_class: equity 0/36, crypto 0/36
- by_vol_regime: low 0/24, mid 0/24, high 0/24

## Full-sample check (default params: er_window=10, fast=2, slow=30, band_window=20, n_std=2.0, slope_window=5)
All 4 symbols (QQQ, SPY, BTC/USDT, ETH/USDT) generated ZERO trades over the full sample at
default params -- the conjunction of (uptrend regime AND price dips below lower band AND
recovers) is an extremely rare/near-empty signal at these parameter settings. This explains
the grid's decisive 0/72 rejection: most grid cells likely have too few or zero trades to
generate a meaningful Sharpe, and where trades do occur (e.g. the grid's best cell,
BTC/USDT mid-vol at n_std=1.5, Sharpe 0.97), it falls just short of the 1.0 threshold anyway.

## Decision
REJECTED across all symbols and vol regimes (decisive, 0/72 grid cells pass). The core issue
is signal sparsity: requiring BOTH an uptrend-with-positive-KAMA-slope AND a below-lower-band
dip-and-recovery is an overly restrictive conjunction that rarely fires. A future revisit could
loosen the uptrend gate (e.g. just close>KAMA without the slope requirement) or widen n_std
further, but this exact PyQuantLab-sourced pullback-mode rule set as disclosed does not clear
the bar.
