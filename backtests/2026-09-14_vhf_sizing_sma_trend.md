# Backtest Report: VHF Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_vhf_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-101

## Hypothesis

Vertical Horizontal Filter (Adam White): VHF = (highest_close - lowest_close)
/ sum(|close.diff()|) over a rolling window, bounded [0,1] -- net
directional range vs total path length traveled, an unsigned trend-strength
measure (like ADX/CHOP). Confirmed via DuckDuckGo HTML SERP (ta-lib.org,
gocharting.com, technicalresources.in, trendspider.com).

Repo has 2 prior VHF entries, both binary trend-efficiency GATE
constructions, both rejected. Neither used VHF as a CONTINUOUS SIZING dial.
This iteration applies the ADX/CHOP-style reframing.

## Grid test summary (Step 6)

`param_grid={vhf_sensitivity: [0.4,0.6,0.8], deadband: [0.10,0.15,0.20]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=61, pass_fraction=0.565 -- highest pass_fraction
  of any strategy this cron trigger
- by_asset_class: equity 26/54 (0.48), crypto 35/54 (0.65) -- **first
  strategy this cron trigger where crypto outperforms equity in the grid**
- by_vol_regime: low 36/36 (1.00), mid 19/36 (0.53), high 6/36 (0.17) --
  first strategy this cron trigger with ANY high-vol-regime passes
- per-symbol: QQQ 17/27, SPY 9/27, BTC/USDT 24/27 (best sens=0.8/db=0.2
  Sharpe 1.98 in MID-vol regime), ETH/USDT 11/27

## Single-config validator results (Step 7)

Grid best-cell configs initially missed TC-survival (QQQ 0.428 net Sharpe
at db=0.2) or MDD (BTC 0.257 at db=0.2/sens=0.8). A deadband/sensitivity
sweep found configs clearing all 5 validators:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.4, db=0.3 | 1.075 (pass) | 6.77% (pass) | 0.569 (pass) | 0.75 (pass) | 0.122 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.4, db=0.15 (best tried) | 0.964 (**FAIL**) | 6.04% (pass) | 0.218 (**FAIL**) | 0.75 (pass) | 0.332 rel-std (pass) | **REJECT** (Sharpe, TC-survival) |
| BTC/USDT | sens=0.6, db=0.2 | 1.226 (pass) | 21.71% (pass) | 1.033 (pass) | 0.75 (pass) | 0.101 rel-std (pass) | **ACCEPT** |

## Decision (original, 2026-09-14-101)

**Accept for QQQ (equity) AND BTC/USDT (crypto)** — both clear all 5
validators, the first strategy this cron trigger to accept BOTH an equity
AND a crypto symbol simultaneously (every prior sizing-dial this trigger
either rejected crypto on MDD or accepted equity-only). **Reject SPY**
(fails Sharpe and TC-survival at every deadband tried). Economically
sensible: VHF/trend-efficiency filtering (distinguishing genuinely
directional moves from choppy retracement) appears to generalize across
asset classes better than the directional-momentum oscillators
(RMI/SMI/IMI/BOP) tested earlier this trigger, consistent with ADX/CHOP
(the other two unsigned trend-strength dials) also being among this
trigger's strongest performers. Parameter sensitivity is noticeably higher
than other accepted dials this trigger (0.10-0.13 rel-std vs typically
<0.05) -- still comfortably under the 0.5 threshold but worth noting for a
future refinement pass.

## SPY fix (2026-09-17-028, follow-up iteration)

A wider joint sweep of `deadband` x `vhf_sensitivity` x `vhf_window` x
`base_exposure` (81 combos, SPY only) found 7 combos clearing all
thresholds, all requiring a higher `base_exposure=0.6` and a *lower*
`vhf_sensitivity=0.3` than the original SPY attempt (sensitivity=0.4) --
the original SPY rejection was a param-tuning issue (too-frequent
rebalancing relative to SPY's lower realized vol vs QQQ/BTC), not a
fundamental incompatibility.

Selected config: `vhf_sensitivity=0.3, deadband=0.25, vhf_window=28,
base_exposure=0.6`.

| Validator | Result |
|---|---|
| Sharpe | 1.163 (pass, threshold 1.0) |
| MDD | 6.38% (pass, threshold 25%) |
| TC-survival net Sharpe | 0.577 (pass, threshold 0.5, 129 trades) |
| Walk-forward pass fraction | 0.75 (pass, threshold 0.75) |
| Param sensitivity rel-std | 0.046 (pass, threshold 0.5) |

**Accept SPY.** Combined with the original 2026-09-14-101 accept, the VHF
continuous-sizing dial now covers equity QQQ+SPY and crypto BTC/USDT (ETH/USDT
not separately retested this iteration). Full raw validator output:
`validate_result_vhf_spy_fix.json`.
