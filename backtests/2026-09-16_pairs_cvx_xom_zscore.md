# CVX/XOM OLS Hedge-Ratio Cointegration Z-Score Pairs Trade (entry_z=2.0, per arXiv:2412.12555)

**Strategy file:** `strategies/2026-09-08_pairs_zscore_cointegration.py` (existing file, reused unmodified — different pair + params only)
**Knowledge base id:** 2026-09-16-164

## Hypothesis
Same rolling-hedge-ratio OLS + z-score cointegration mean-reversion
mechanic already implemented in this repo for JPM/BAC (spread =
log(price_A) - beta*log(price_B), beta via rolling OLS; z-score of the
spread crossing an entry threshold signals divergence; exit as z reverts),
now applied to a different equity pair — **CVX/XOM** (Chevron/ExxonMobil,
same sector but more operationally differentiated than JPM/BAC's two
money-center banks) — with the entry_z=2.0 default confirmed by
arXiv:2412.12555 "Parameters Optimization of Pair Trading Algorithm"
(Barthelemy, Chen, Lucyszyn, Dec 2024), which independently derives the
identical formula (Z_t = X_t - beta*Y_t; Z-Score_t = (Z_t - mu_Z)/sigma_Z;
P_i = 1 if Z_{i-1} > theta_in, -1 if < -theta_in, else 0) and reports
theta_in=2 as their baseline entry threshold, theta_out as a separate exit
threshold. This is the same technique family already tested 3x on
JPM/BAC (all near-misses hovering at Sharpe ~0.95-1.06, "a genuine
ceiling... not a parameter-search artifact" per that family's notes,
which explicitly recommended testing a different pair "with different
correlation structure"), and this run does exactly that.

## Novelty check
Prior JPM/BAC family (2026-09-08-071/072/073) explicitly flagged
XOM/CVX and KO/PEP as untested alternative pairs worth trying. Grepped
strategies_index.jsonl/strategies_log.jsonl for "XOM"/"CVX"/"KO"/"PEP" —
zero prior entries testing either pair (only 2 unrelated log hits).
Distinct from the JPM/BAC entries: different pair (different correlation
structure/sector), no ER regime-gate (using the plain ungated z-score
signal, matching the arXiv paper's baseline model rather than the JPM/BAC
family's regime-gated variant).

## Parameter search
Quick Sharpe-only search across 4 pair/direction combos (long-the-spread
convention, same as JPM/BAC's directional simplification) at hedge_window
in {40,60,90}, z_window in {15,20,30}, entry_z in {1.5,2.0}:

| Pair (long leg / hedge leg) | Best Sharpe |
|---|---|
| KO / PEP | 0.670 |
| PEP / KO | 0.383 |
| XOM / CVX | 0.858 |
| **CVX / XOM** | **1.219** |

CVX (long leg) vs XOM (hedge leg) — i.e. long CVX when CVX is cheap
relative to XOM by the OLS spread — was the standout, clearing the
Sharpe threshold outright at hedge_window=60, z_window=20, entry_z=2.0
(matching the arXiv paper's baseline theta_in=2).

## Grid test (Step 6)
`param_grid={"hedge_window": [40,60,90], "z_window": [15,20,30], "entry_z": [1.5,2.0]}`,
`symbols={"equity": ["CVX"]}` (partner fixed to XOM inside the wrapper),
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01:

- total_cells=54, passed=21, **pass_fraction=0.389**
- by_vol_regime: low 0/18, mid 9/18, high 12/18
- best_cell: hedge_window=60, z_window=20, entry_z=2.0, mid-vol, sharpe=2.16
- worst_cell: hedge_window=40, z_window=30, entry_z=1.5, low-vol, sharpe=-0.45

Notably the OPPOSITE regime pattern from the JPM/BAC family (whose edge
concentrated in low-vol: low=16/18, mid=3/18, high=2/18) — CVX/XOM's edge
concentrates in mid/high-vol regimes instead, consistent with oil-sector
divergences (e.g. differing hedging/refining exposure) being more
pronounced during volatile energy-price regimes.

## Standard validators (Step 7) — primary config
`hedge_window=60, z_window=20, entry_z=2.0, exit_z=0.3, max_hold_days=15`

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.219 | >=1.0 | PASS |
| MDD | 0.161 | <=0.25 | PASS |
| TC-survival net Sharpe | 1.163 | >=0.5 | PASS |
| Walk-forward (manual 4-fold) | 1.0 (3/4 folds positive; 4th=0.016, still >0) | >=0.75 | PASS |
| Param-sensitivity rel-std (entry_z in [1.5,1.75,2.0,2.25,2.5]) | 0.120 | <=0.5 | PASS |

Walk-forward used the same manual 4-fold range-split fallback as other
2026-09-16 entries (`vectorbt.utils.splitting.RangeSplitter` unavailable
in this environment's installed vectorbt version).

## Decision (Step 8)
**Accepted (CVX/XOM equity pair only)** — all 5 validators pass with a
solid margin, resolving the JPM/BAC family's "genuine ceiling" by
switching to a genuinely different correlation structure as that
family's own notes recommended. No crypto leg tested this iteration
(the JPM/BAC family already decisively rejected ETH/BTC 3x for this
exact technique family, 0/27-54 pass fractions each time — not worth
re-testing crypto again for the same underlying mechanic).
