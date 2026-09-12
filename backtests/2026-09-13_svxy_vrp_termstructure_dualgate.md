# 2026-09-13 SVXY VRP + Term-Structure Dual-Gate — Backtest Report

**Hypothesis:** Long SVXY (short-vol ETF) only when BOTH the VIX/VIX3M
term-structure ratio is in contango (<= contango_thresh) AND the Volatility
Risk Premium (VRP = VIX - realized_vol(SVXY, rv_window)) is positive
(> vrp_threshold). Per Zarattini/Aziz/Mele "The Volatility Edge: A Dual
Approach For VIX ETNs Trading" (SSRN 5316487, referenced in Quantpedia's
April 2026 monthly digest — https://quantpedia.com/quantpedia-in-april-2026/,
paper summary read via https://concretumgroup.com/the-volatility-edge-a-dual-approach-for-vix-etns-trading/,
both visited this iteration via browser_exec since web_extract's ddgs
backend cannot fetch page content). Source's own final strategy combines
"the option-market volatility premium" and "the slope of the VIX term
structure" as a dual signal, reporting 16.3% CAGR / Sharpe ~1 / 42% MDD
(2008-2025, with realistic transaction costs, at unspecified allocation
sizing not directly reproducible here).

## Prior related entries
- 2026-09-05-044 (VRP-only regime filter on QQQ): accepted.
- 2026-09-11-071 (term-structure-only gate on SVXY): rejected — Sharpe
  0.639, MDD 0.402 full-sample; edge confined entirely to low-vol regime
  (9/9 low pass, 0/9 mid, 0/9 high) because the ratio-only signal lags
  actual realized-vol spikes.

This iteration combines both signals (AND-gate) on the same SVXY instrument
to test whether VRP's faster reaction to realized-vol spikes rescues the
term-structure gate's mid/high-vol failure.

## Single-config validators (best full-sample config: contango_thresh=1.02, vrp_threshold=3.0, min_hold_days=3, SVXY, 2018-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.278 | >= 1.0 | **FAIL** |
| Max drawdown | 0.208 | <= 0.25 | PASS |
| Transaction-cost survival (10bps/trade, 16 trades) | 0.236 | >= 0.5 | **FAIL** |

Walk-forward/parameter-sensitivity skipped — already decisively rejected on
Sharpe and TC-survival (walk_forward's vectorbt API also errored in this
environment: `vbt.utils.splitting` not available in the installed
vectorbt version, a pre-existing tooling gap noted for a future loop to fix
in validators.py, not specific to this strategy).

## Step 6 grid summary (contango_thresh in [0.98,1.0,1.02] x vrp_threshold in [1.0,2.0,3.0] x min_hold_days in [1,3], SVXY only — no crypto analog for VIX, vol_regime_splits=3)

- 54 total cells, 17 passed (pass_fraction 0.315)
- **by_asset_class**: equity 17/54 (32%) — crypto N/A (no VIX-equivalent instrument)
- **by_vol_regime**: low 17/18 (94% pass), mid 0/18, high 0/18
- Best cell: contango_thresh=1.02, vrp_threshold=3.0, min_hold_days=3, low-vol regime, Sharpe 1.898
- Worst cell: contango_thresh=0.98, vrp_threshold=2.0, min_hold_days=1, mid-vol regime, Sharpe -1.392

## Decision: REJECTED

The dual-gate materially **improved max drawdown** vs the term-structure-only
predecessor (0.208 vs 0.402 full-sample at the best config — confirming the
VRP component does add a faster-reacting stress detector that trims tail
risk), but full-sample Sharpe (0.278) and net-of-cost Sharpe (0.236) remain
decisively below threshold, and the grid's regime breakdown is nearly
identical to the single-signal predecessor: the edge is still confined
almost entirely to the low-vol tercile (17/18 pass) with zero cells passing
in mid or high vol. Adding the VRP AND-gate reduced total trade count
(fewer false contango entries) but did not convert enough of the low-vol
edge into full-sample profitability once the strategy sits flat through
most of the mid/high-vol sample (which is most of the drawdown-prone period
by construction, but also removes most of the compounding opportunity).

## Notes for future iterations

- MDD improvement (0.402 -> 0.208) from adding VRP as a second gate is a
  genuine, reproducible finding — future SVXY/VXX dual-signal attempts
  should keep the VRP component even if further tuning the term-structure
  side.
- The source paper's own headline Sharpe ~1/CAGR 16.3% likely relies on
  DYNAMIC position sizing ("adapts position sizing based on two key
  signals") rather than a binary long/flat AND-gate — this repo's
  long/flat-only convention cannot faithfully reproduce that; a genuinely
  faithful replication would need continuous position-sizing support in
  generate_signals, which is out of scope for this repo's current
  strategy-file/grid-test contract (binary 0/1 positions only).
- `validators.check_walk_forward`'s `vbt.utils.splitting.RangeSplitter`
  reference errors with the installed vectorbt version in this
  environment — worth a maintenance fix in a future iteration (not
  blocking, since this strategy was already decisively rejected on other
  validators).
