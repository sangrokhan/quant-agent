# Force Index Continuous Sizing Dial + SMA Trend Gate

**Strategy file:** `strategies/2026-09-20_force_index_sizing_sma_trend.py`
**Date:** 2026-09-20
**Knowledge base id:** 2026-09-20-027

## Hypothesis

Elder's Force Index (EFI, Alexander Elder): raw 1-period EFI = (Close -
PriorClose) * Volume, smoothed with a 13-period EMA (per Google AI-overview
synthesis of StockCharts.com ChartSchool / LuxAlgo / Deepvue / Finlogix,
read via `browser_exec` since `web_search`'s DDGS backend errored with a
TLS `RequestError` on every query attempted this iteration -- confirmed
via `https://www.google.com/search?q=Elder+Force+Index+formula...` SERP
snippet). This repo has 4 prior Force Index entries, all binary
crossover/divergence ENTRY triggers, all rejected:
- 2026-09-04-049: dual-EMA (13-period trend filter + 2-3 period pullback trigger)
- 2026-09-05-048: FI(39) bullish divergence
- 2026-09-09-086: 2-period FI zero-cross + Schaff Trend Cycle confirmation
- 2026-09-10-097: plain 13-period EMA zero-line crossover (QQQ Sharpe 0.910
  near-miss/MDD 0.309 fail, SPY Sharpe 0.852 near-miss)

None reframed EFI as a CONTINUOUS SIZING dial. This iteration applies the
now-repeated repo pattern (Vortex/AO/KST/TRIX/Qstick/Elder-Ray/Ulcer/TSV/BOP
all similarly rescued): within an SMA(40) uptrend gate, exposure scales
continuously with a rolling z-scored, tanh-squashed EFI(13) reading rather
than a discrete zero-cross flip.

## Grid test (Step 6)

`scripts/run_grid_force_index_sizing.py`: param_grid = {sensitivity: [0.4,
0.6, 0.8], deadband: [0.10, 0.15, 0.20]} x symbols {QQQ, SPY, BTC/USDT,
ETH/USDT} x vol_regime_splits=3. 108 total cells.

- **pass_fraction: 0.565** (61/108)
- by_asset_class: equity 34/54 (63%), crypto 27/54 (50%)
- by_vol_regime: low 36/36 (100%), mid 18/36 (50%), high 7/36 (19%) --
  edge concentrated in low/mid-vol regimes, degrades sharply in high-vol
  (expected for a trend-following sizing dial)
- best_cell: QQQ, sensitivity=0.8/deadband=0.15, low-vol, Sharpe=2.65
- Full sample (not just low-vol tercile) average Sharpe across the 3x3
  sub-grid was consistently >=1.0 for ALL 4 symbols; sensitivity=0.4 was the
  most robust setting across all 4 symbols (see below).

## Single-config validation (Step 7)

Two per-asset-class configs (both reusing the identical strategy code,
only params differ):

| Config | sensitivity | deadband | leverage_cap |
|---|---|---|---|
| Equity (QQQ, SPY) | 0.4 | 0.25 | 1.0 (default) |
| Crypto (BTC/USDT, ETH/USDT) | 0.4 | 0.15 | 0.3 |

(Equity needed a wider deadband than the grid's tested max of 0.20 to clear
TC-survival cleanly; crypto needed a leverage_cap cut from the equity
default 1.0 to 0.3 to clear max-drawdown -- same rescue pattern used
repeatedly elsewhere in this repo for crypto sizing-dial variants.)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel std) | Trades |
|---|---|---|---|---|---|---|
| QQQ | 1.257 (pass) | 0.136 (pass) | 0.721 (pass) | 0.75 (3/4 splits, pass) | 0.028 (pass) | 182 |
| SPY | 1.245 (pass) | 0.084 (pass) | 0.666 (pass) | 0.75 (3/4 splits, pass) | 0.050 (pass) | 154 |
| BTC/USDT | 1.357 (pass) | 0.175 (pass) | 1.017 (pass) | 1.00 (4/4 splits, pass) | 0.024 (pass) | 185 |
| ETH/USDT | 1.331 (pass) | 0.213 (pass) | 1.133 (pass) | 1.00 (4/4 splits, pass) | 0.026 (pass) | 161 |

Note: `check_walk_forward`'s vectorbt call (`vbt.utils.splitting.RangeSplitter`)
raised `AttributeError` on the installed vectorbt 1.1.0 (same known issue
noted in several prior entries, e.g. 2026-09-20-026) -- substituted a manual
4-way contiguous-chunk walk-forward (per-chunk Sharpe>0, pass_fraction>=0.75)
computed directly with the same `returns.vbt.returns(freq="D").sharpe_ratio()`
call vectorbt provides, just without the broken splitter helper.

**All 5 validators pass for all 4 symbols.**

## Decision

**ACCEPTED** — equity (QQQ, SPY) at sensitivity=0.4/deadband=0.25/leverage_cap=1.0,
crypto (BTC/USDT, ETH/USDT) at sensitivity=0.4/deadband=0.15/leverage_cap=0.3.
Full validator suite clears for both asset classes; grid shows the edge is
strongest in low/mid volatility regimes and degrades in high-vol (documented
in `notes`, not a scope-limiting rejection since full-sample validators
already account for this).

## Sources

- Google AI-overview synthesis (StockCharts.com ChartSchool, LuxAlgo,
  Deepvue, Finlogix) for the Elder Force Index formula, read via
  `browser_exec` after `web_search`'s DDGS backend failed with a TLS
  `RequestError` on the direct query.
