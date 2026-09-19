# Factor-Sleeve Momentum-Rank Gate (MTUM/QUAL/IWD/IWM) (ACCEPTED, QQQ + SPY)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_factor_sleeve_momentum_rank_gate.py`
**Source:** https://theintrinsicinvestor.com/research/etf-factor-sector-rotation-strategy/

## Hypothesis
The Intrinsic Investor's disclosed two-sleeve monthly ETF rotation study
(60 parameter combinations, Compustat/WRDS data, July 2014-March 2026)
uses a "Factor sleeve" of four style-factor ETFs (MTUM momentum, QUAL
quality, IWD value, IWM small-cap) ranked by trailing N-month total
return, allocating to the top-ranked ETF, gated by a SPY drawdown
filter. Adapted into a single-asset momentum-RANK GATE (same adaptation
pattern already validated for the existing 9-sector-ETF basket,
2026-09-11-118, accepted): only take the primary asset's (QQQ/SPY) own
SMA-trend-following long signal when the primary asset's trailing
momentum_window-day return ranks in the top rank_threshold of the
FACTOR-STYLE basket {MTUM, QUAL, IWD, IWM} -- a materially different,
smaller, style-based basket vs. the existing sector-based 9-ETF basket.
For crypto, reuses the existing 5-major-coin basket (no style-factor
analogue exists in crypto).

## Grid test summary (manual replication of run_strategy_grid's regime-slicing logic, since this strategy needs a per-symbol `primary_symbol` kwarg the grid harness doesn't pass automatically)

symbols QQQ/SPY x trend_sma_window in {50,100,150} x momentum_window in
{126,252} x rank_threshold in {1,2,3}, vol_regime_splits=3, 2019-2026
(108 cells)

- pass_fraction: 0.444 (48/108)
- by_vol_regime: low 30/36, mid 18/36, high 0/36

## Single-config validators (full 2019-2026 sample, trend_sma_window=50, momentum_window=252, rank_threshold=3)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.182 PASS | 0.189 PASS | 1.095 PASS (61 trades @10bps) | 0.75 PASS (3/4 splits) | 0.073 PASS |
| SPY | 1.071 PASS | 0.195 PASS | 0.962 PASS (61 trades @10bps) | 0.75 PASS (3/4 splits) | 0.163 PASS |

Both symbols pass all 5 validators at the identical shared config.

## Cross-asset scope check

| Symbol | Sharpe | MDD | TC-survival |
|---|---|---|---|
| QQQ | 1.182 PASS | 0.189 PASS | 1.095 PASS |
| SPY | 1.071 PASS | 0.195 PASS | 0.962 PASS |
| BTC/USDT | 1.380 PASS | 0.497 FAIL | 1.314 PASS |
| ETH/USDT | 1.014 PASS | 0.492 FAIL | 0.980 PASS |

## Decision: ACCEPTED (equity: QQQ + SPY, shared config)

Strategy file and this report kept as a live accepted strategy, scoped
to equity (QQQ, SPY) at trend_sma_window=50/momentum_window=252/
rank_threshold=3. Crypto (BTC/USDT, ETH/USDT) both pass Sharpe and
TC-survival comfortably but decisively fail max drawdown (49.7%/49.2%
vs 25% cap) -- despite the 5-major-coin basket existing (reused from
the sector-rank-gate strategy), the factor-momentum-rank mechanism does
not control crypto's much larger drawdowns; do not apply to crypto.

## Notes for future loops
- Both QQQ and SPY pass at the IDENTICAL shared parameter config --
  unlike most cross-symbol scope splits in this repo, no per-symbol
  retuning was needed here, suggesting the factor-sleeve rank
  mechanism is reasonably robust across the two major equity index
  ETFs.
- Distinct from the existing sector-rank-gate strategy (2026-09-11-118,
  9-SPDR-sector basket) via using a smaller, STYLE-factor-based basket
  (MTUM/QUAL/IWD/IWM) instead -- both are valid, separately-accepted
  adaptations of the same QuantPedia/academic rotational-momentum
  concept to this repo's single-asset interface.
- Grid pass_fraction (44.4%) is solid but, as with nearly every
  strategy in this repo, completely fails in the high-vol tercile
  (0/36) -- do not trust this signal during high-volatility regimes.
- Walk-forward is 3/4 (0.75, meets threshold exactly) for both symbols
  -- the same split index is negative for both QQQ and SPY, suggesting
  a shared macro period (likely the 2022 rate-hiking regime, a
  recurring weak period across many strategies in this repo) rather
  than symbol-specific noise.
