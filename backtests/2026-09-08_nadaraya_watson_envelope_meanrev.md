# Backtest Report: Nadaraya-Watson Envelope Mean Reversion

**Strategy file:** `strategies/2026-09-08_nadaraya_watson_envelope_meanrev.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

A causal ("endpoint", non-repainting) Nadaraya-Watson kernel-regression fit
of recent closes, banded by `mult * mean_absolute_deviation` of the fit
residual, identifies short-term price "stretch". Per LuxAlgo's official docs
(https://www.luxalgo.com/library/indicator/nadaraya-watson-envelope/):
"Price crosses the lower extremity: ... flagging stretched declines for
mean-reversion longs." Long-only, gated by a 200-day SMA uptrend filter to
avoid fading a genuine downtrend (source's own stated caveat). Novel
indicator family for this repo (Gaussian-kernel-weighted regression + MAD
envelope, distinct from Bollinger/Keltner/STARC/MA-Envelope SMA/ATR-based
bands already tested).

## Sources

- https://www.luxalgo.com/library/indicator/nadaraya-watson-envelope/ (primary, exact construction)
- https://www.google.com/search?q=Nadaraya-Watson+envelope+indicator+trading+strategy+entry+exit+rules (SERP, browser_exec fallback after web_search backend failure)
- (web_extract failed on 2 candidate URLs with backend errors -- fell back to browser_exec to read the LuxAlgo page directly)

## Grid test summary (window x mult, equity+crypto, 3 vol terciles)

- `pass_fraction`: 16/108 = 0.148
- `by_asset_class`: equity 16/54 passed, crypto 0/54 (decisive fail)
- `by_vol_regime`: low 10/36, mid 6/36, high 0/36 -- edge concentrated
  entirely in low-vol tercile slices, degrades through mid, vanishes in
  high-vol
- `best_cell`: window=15, mult=2.5, QQQ, low-vol, Sharpe=2.41
- `worst_cell`: window=30, mult=2.5, SPY, high-vol, Sharpe=-1.09

## Single-config validation (window=15, mult=2.5 -- best grid cell params)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.215 (FAIL) | 0.954 (FAIL, near-miss) | ≥ 1.0 |
| Max drawdown | 0.112 (PASS) | 0.078 (PASS) | ≤ 0.25 |
| TC survival (10bps, actual trade count) | 0.176 (FAIL) | 0.861 (PASS) | ≥ 0.5 |
| Walk-forward (manual 4-split) | 1.0 (PASS, 4/4) | 0.75 (PASS, 3/4) | ≥ 0.75 |
| Parameter sensitivity (9-cell grid rel-std) | 0.507 (FAIL) | 0.891 (FAIL) | ≤ 0.5 |

`check_walk_forward` used the manual 4-split workaround (pre-existing
`vbt.utils.splitting` missing-attribute bug documented since
2026-09-03-002/backtests/2026-09-03_btc_absolute_momentum.md).

## Decision: REJECT

The grid's best_cell Sharpe (2.41) is a low-vol-tercile SLICE, not
representative of full-sample performance -- full-sample Sharpe collapses to
0.215 (QQQ, decisive fail) / 0.954 (SPY, near-miss) at the same params.
Parameter sensitivity fails decisively on both symbols (rel-std 0.51/0.89,
both above the 0.5 threshold) -- performance is fragile to window/mult
choice, consistent with the grid's own by_vol_regime finding that the edge
only exists in a narrow low-vol slice and evaporates elsewhere. Crypto fails
decisively (0/54). Consistent with LuxAlgo's own stated caveat: "nothing
suggests this envelope outperforms traditional band tools."

## Notes for future loops

If revisited: consider restricting entries to the low-vol regime explicitly
(same pattern as the accepted `2026-09-03_bb_meanrev_qqq_volregime.py` and
`2026-09-06-181`/`2026-09-06-183` KAMA+vol-gate rescue) rather than trading
unconditionally across all vol regimes -- the grid's by_vol_regime split
already shows the edge is real but narrow (10/36 low-vol passes vs 0/36
high-vol). A vol-regime-gated variant is a plausible follow-up hypothesis,
not yet tested.
