# Backtest Report: SPY-style Opening Gap-Down Partial-Fill Mean Reversion

**Strategy file:** `strategies/2026-09-08_spy_gap_down_partial_fill.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per QuantifiedStrategies.com's own disclosed, freely-available numeric rule
(https://www.quantifiedstrategies.com/gap-fill-trading-strategies/, author's
own SPY 2010-2012 backtest, 110 fills/98 winners/avg 0.19% per fill): a
moderate overnight gap DOWN (open between -0.15% and -0.6% below the prior
close, deliberately excluding both tiny noise gaps and large gaps) is a
same-day mean-reversion long entry at the open, gated by prior-day IBS <
0.25 (source's own filter). Target = 0.75 of the gap size; exit at target if
touched intraday, otherwise flat at the close (no overnight hold, single-
day trade). Distinct from already-rejected 2026-09-03-010 (simple academic-
literature gap-down fade with no gap-size band, no partial-fill target
mechanic, no IBS filter).

## Sources

- https://www.quantifiedstrategies.com/gap-fill-trading-strategies/ (primary, exact disclosed rule + author's own backtest stats)
- https://www.google.com/search?q=%22gap+fill%22+overnight+gap+trading+strategy+quantifiedstrategies+rules+SPY (SERP, browser_exec used throughout this iteration -- web_search backend failed with repeated TLS/rustls errors on 2 prior queries this iteration)

## Grid test summary (gap_down_min/max x ibs_threshold, equity+crypto, 3 vol terciles)

- `pass_fraction`: 26/96 = 0.271
- `by_asset_class`: equity 26/48, crypto 0/48 (decisive fail -- no genuine
  overnight session gap in 24/7 crypto, expected falsification per source's
  own SPY-specific framing)
- `by_vol_regime`: low 2/32, mid 8/32, high 16/32 -- edge concentrated in
  high-vol tercile (larger gaps during volatile periods, more room to
  mean-revert toward the 0.75-of-gap target)
- `best_cell`: gap_down_min=-0.001/gap_down_max=-0.005/ibs=0.3, SPY,
  high-vol, Sharpe=3.62
- `worst_cell`: gap_down_min=-0.001/gap_down_max=-0.008/ibs=0.2, QQQ,
  low-vol, Sharpe=-1.14

## Single-config validation (gap_down_min=-0.001/gap_down_max=-0.005/ibs=0.3 -- best grid cell)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.600 (FAIL) | 0.743 (FAIL) | ≥ 1.0 |
| Max drawdown | 0.057 (PASS) | 0.024 (PASS) | ≤ 0.25 |
| TC survival (10bps, actual trade count) | -0.105 (FAIL, decisive) | -0.186 (FAIL, decisive) | ≥ 0.5 |
| Walk-forward (manual 4-split) | 0.75 (PASS, 3/4) | 0.75 (PASS, 3/4) | ≥ 0.75 |
| Parameter sensitivity (8-cell grid rel-std) | 0.316 (PASS) | 0.504 (FAIL, marginal) | ≤ 0.5 |

## Decision: REJECT

The best grid cell's Sharpe=3.62 was a high-vol-tercile slice, not full-
sample-representative -- full-sample Sharpe collapses to 0.60 (QQQ) / 0.74
(SPY), both failing the 1.0 threshold. Transaction-cost survival fails
decisively on both symbols: with 78-93 trades over ~7.7 years (roughly
weekly), a flat 10bps round-trip cost drag turns both net Sharpes NEGATIVE,
meaning the strategy's small average edge per trade (per source's own 0.19%
per fill) does not survive even modest realistic costs at this trade
frequency. This mirrors several other near-misses in this repo (Klinger,
ZLEMA, Accelerator Oscillator) where high trade frequency was the decisive
failure mode, but here the underlying Sharpe was already sub-threshold too.

## Notes for future loops

The high-vol-tercile concentration (16/32 vs 2/32 in low-vol) is a genuine,
repeatable pattern (consistent with the mechanism: bigger vol -> bigger
gaps -> more room to hit the 0.75-of-gap target before the close). A future
loop could explicitly gate entries to high-vol regimes only (same rescue
pattern as accepted 2026-09-03_bb_meanrev_qqq_volregime.py) AND/OR widen the
gap-size band toward the source's full -0.15%/-0.6% range (this grid tested
narrower/wider variants around it, not the source's exact stated band) to
see if either change clears both the Sharpe and TC-survival bars
simultaneously -- not yet tested as a combined fix.
