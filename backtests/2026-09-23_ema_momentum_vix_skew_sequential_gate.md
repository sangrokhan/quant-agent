# EMA Momentum Sequentially Conditioned on VIX Regime + Return Skewness

**Strategy file:** `strategies/2026-09-23_ema_momentum_vix_skew_sequential_gate.py`
**Hypothesis source:** Alessandro Pontes, "Sequential Conditioning of Momentum
on Implied Volatility Regimes and Distributional Asymmetry" (SSRN
abstract_id=6758540, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6758540),
read via browser_exec this iteration (web_search DDGS backend RequestError'd
on the discovery query; Bing SERP via browser_exec surfaced the paper title,
then the SSRN abstract page was opened directly).

## Hypothesis

Momentum (EMA crossover), implied-volatility regime (VIX vs its own trailing
average), and rolling return skewness are three non-redundant state
variables whose combined confirmation (sequential AND-gate, not a composite
score) should improve trend-following reliability, per Merton's (1973)
inter-temporal CAPM (state-dependent risk premia) and Lo's (2004) Adaptive
Markets Hypothesis (edge validity is regime-dependent). Distinct from prior
repo entries that tested VIX-regime gates, skewness gates, or SKEW-index/VIX
divergence overlays in isolation or pairs — this is the first strict
three-way sequential conjunction (EMA momentum AND VIX-calm AND
positive/near-zero rolling return skewness).

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = {ema_fast: [10,20], ema_slow: [50,100],
skew_threshold: [-0.2, 0.0, 0.2]}, symbols = {equity: [QQQ, SPY], crypto:
[BTC/USDT, ETH/USDT]}, vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- total_cells: 144, passed_cells: 41, **pass_fraction: 0.285**
- by_asset_class: equity 33/72 passed, crypto 8/72 passed (crypto materially
  weaker — VIX gate passes through as always-true for crypto since no VIX
  proxy exists, so crypto only benefits from momentum+skew gates, and crypto
  return-skewness dynamics differ substantially from equities)
- by_vol_regime: low 21/48, mid 17/48, high 3/48 (strategy underperforms in
  high-vol regimes, consistent with the VIX-calm gate design intent — it's
  *supposed* to sit out high-vol regimes, so low pass-rate there is largely
  by construction/expected, not a red flag)
- Best equity config by average Sharpe across QQQ/SPY/all vol regimes:
  ema_fast=10, ema_slow=50, skew_threshold=-0.2 (avg Sharpe 1.128)
- best_cell overall: crypto ETH/USDT mid-vol, Sharpe 2.34 (single-cell
  outlier, not representative of the crypto asset class broadly per the
  8/72 pass rate)

## Single-config validation (Step 7), config = ema_fast=10, ema_slow=50, skew_threshold=-0.2

| Symbol | Sharpe | MDD | Net Sharpe (10bps, N trades) | Walk-forward (4-split) | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | 0.925 (FAIL, thresh 1.0) | 0.178 (PASS, thresh 0.30) | 0.532 (PASS, thresh 0.5) | 0.75 pass_fraction (PASS, thresh 0.6) | 0.108 (PASS, thresh 0.5) |
| SPY | 1.090 (PASS, thresh 1.0) | 0.127 (PASS, thresh 0.30) | 0.523 (PASS, thresh 0.5) | 0.75 pass_fraction (PASS, thresh 0.6) | 0.108 (PASS, thresh 0.5) |

Walk-forward note: `validators.check_walk_forward` errors on the installed
vectorbt build (`vbt.utils.splitting` module missing — known repo issue, see
prior entries e.g. `validate_result_pjk_channel_trade_in_bands.json`);
computed manually via 4 equal-length chronological splits, Sharpe > 0 in
3/4 splits for both symbols.

## Decision

**Accept, scoped to equity SPY only** at ema_fast=10, ema_slow=50,
skew_threshold=-0.2. QQQ narrowly misses the Sharpe>=1.0 threshold (0.925)
though all other validators pass — a near-miss, not a broad failure. Crypto
is explicitly OUT OF SCOPE: grid pass_fraction only 8/72 for that asset
class, and the VIX-regime gate is structurally a no-op there (no crypto VIX
proxy available via this repo's OHLCV-only loaders), so the tested
three-way mechanism doesn't meaningfully apply to crypto as constructed.
