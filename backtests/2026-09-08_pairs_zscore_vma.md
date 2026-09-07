# Pairs Trading: V/MA (Visa/Mastercard) Cointegration Z-Score

**Strategy file:** reuses `strategies/2026-09-08_pairs_zscore_cointegration.py` (same code as 2026-09-08-071, different pair)
**Source:** https://github.com/ardabaranbaytar/pairs-trading-backtest (candidate-pair cointegration comparison; explicitly found V-MA has much stronger cointegration (p=0.0000, correlation 0.8939) than JPM-BAC or KO-PEP (p=0.2849, rejected by that source))

## Hypothesis

Per `2026-09-08-071/072/073`'s notes: JPM/BAC's pairs-trading edge appears
capped near Sharpe 1.0 regardless of regime-gate tuning, possibly because
money-center banks are "too correlated" structurally. Test a different,
more strongly-cointegrated equity pair — Visa/Mastercard (V/MA), which an
external source's own systematic cointegration screen across 10 candidate
pairs found to have the strongest statistical relationship (vs. JPM-BAC,
KO-PEP, XOM-CVX, etc.).

## Grid test summary (Step 6)

`param_grid`: `hedge_window in {60,90,120}`, `z_window in {15,20,30}`,
`entry_z in {1.5,2.0}`; `vol_regime_splits=3`; symbols: equity V (partner
MA), crypto ETH/USDT (partner BTC/USDT, carried over as the crypto control).

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (V/MA) | 8/54 (0.148) | 2/18 | 0/18 | 6/18 |
| crypto (ETH/BTC) | 0/54 (0.0) | 0/18 | 0/18 | 0/18 |

**Finding: V/MA performs WORSE than JPM/BAC (071: 21/54=0.389) despite the
source's claim of stronger cointegration.** Notably the regime pattern is
inverted from JPM/BAC — V/MA passes MORE in high-vol (6/18) than low-vol
(2/18), the opposite of the mean-reversion-favors-low-vol pattern found for
JPM/BAC and assumed by the ER-regime-gate research (2026-09-08-072). This
suggests V/MA's price divergences don't behave as classic
range-bound-mean-reversion the way JPM/BAC's did — cointegration strength
(a long-run statistical property) doesn't necessarily translate into a
better short-term z-score mean-reversion trading edge.

Best cell: hedge_window=90, z_window=30, entry_z=1.5, high-vol regime,
Sharpe 1.69. Full-period (all regimes) Sharpe for this config: **0.912**
(below 1.0 threshold) — didn't even bother running the full validator
suite given the grid's low overall pass_fraction (0.148) already indicates
this pair is decisively weaker and less consistent than JPM/BAC.

## Decision: **REJECTED** (decisive — weaker and less consistent than JPM/BAC)

## Notes for future iterations

Cointegration strength alone (as commonly tested via Engle-Granger p-value)
is not a reliable predictor of z-score mean-reversion trading edge quality
— V/MA's stronger cointegration p-value did not translate into a better
grid pass_fraction or more consistent regime behavior than JPM/BAC. Do not
assume "more cointegrated pair = better strategy" for future pairs-trading
iterations; the regime-consistency pattern (low-vol-favors-reversion) seen
in JPM/BAC may be pair-specific rather than a pairs-trading universal.
JPM/BAC (with the ER regime gate, 2026-09-08-072/073) remains the strongest
pairs-trading candidate found this cron trigger, still just below the
acceptance bar. Given three JPM/BAC iterations plus this V/MA test all
plateau near/below the Sharpe threshold, the pairs-trading family may be
exhausted for this cron trigger — a future iteration should consider a
completely different technique rather than more pair substitutions.
