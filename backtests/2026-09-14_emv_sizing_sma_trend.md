# Backtest Report: Ease of Movement (EMV) Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_emv_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-106

## Hypothesis

Ease of Movement (Richard W. Arms Jr.): Distance Moved = midpoint(t) -
midpoint(t-1) where midpoint = (High+Low)/2; Box Ratio = (Volume/1e8) /
(High-Low); EMV = Distance Moved / Box Ratio, conventionally smoothed with a
14-period SMA. Formula confirmed via chartschool.stockcharts.com
(browser_exec navigation -- web_extract blocked, "DuckDuckGo (ddgs) is a
search-only backend and cannot extract URL content").

Repo has one prior EMV entry (2026-09-04-115): binary threshold-crossover
ENTRY signal, accepted QQQ+SPY only (10-day EMV, 200-day trend filter,
max_hold_days=10), crypto decisively rejected. This iteration reframes EMV
as a CONTINUOUS SIZING dial (rolling z-score + tanh squash, the same fix
pattern applied to RWI-diff/EFI/VZO earlier this cron trigger, since raw
EMV's scale drifts with volume level and high-low range just like EFI)
within an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], emv_sensitivity:[0.5,0.6,0.7], deadband:[0.2,0.28]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=144, passed=41, pass_fraction=0.285
- by_asset_class: equity 41/72 (0.57), crypto 0/72 (0.00) -- crypto fails
  every single cell in the grid
- by_vol_regime: low 24/48 (0.50), mid 12/48 (0.25), high 5/48 (0.10)
- best_cell: QQQ, trend_window=60/sens=0.6/db=0.2, low-vol regime, Sharpe
  2.83
- worst_cell: QQQ, trend_window=60/sens=0.5/db=0.2, high-vol regime, Sharpe
  -0.69

## Single-config validator results (Step 7)

Best grid config (trend_window=60, emv_sensitivity=0.6, deadband=0.2)
applied full-sample per symbol:

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel-std over sens 0.4-0.8) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.029 (pass) | 13.00% (pass) | 0.670 (pass) | 1.00 (pass) | 0.044 (pass) | **ACCEPT** |
| SPY | 0.808 (**FAIL**) | 10.79% (pass) | 0.333 (**FAIL**) | 1.00 (pass) | 0.052 (pass) | **REJECT** |
| BTC/USDT | 0.207 (**FAIL**) | 42.36% (**FAIL**) | -0.031 (**FAIL**) | 1.00 (pass) | 0.020 (pass) | **REJECT** |

SPY deadband/sensitivity sweep (db in {0.25,0.3,0.35} x sens in
{0.5,0.6,0.7}, 9 combos): best found was db=0.35/sens=0.5, Sharpe=0.913 --
still under the 1.0 threshold in every combination tried. Unlike VHF/PFE/RWI
where widening the deadband rescued SPY, EMV's SPY signal appears
structurally weak rather than merely over-traded.

## Decision

**Accept for QQQ (equity) only.** All 5 validators pass at
trend_window=60/emv_sensitivity=0.6/deadband=0.2. **Reject SPY** — Sharpe
stays below 1.0 (max 0.913) across a 9-point deadband/sensitivity sweep,
unlike sibling sizing-dial strategies this cron trigger where widening the
deadband rescued SPY. **Reject BTC/USDT** — fails Sharpe, MDD (42.4% > 25%
threshold, worst crypto MDD among the recent sizing-dial batch), and
TC-survival simultaneously; crypto fails 0/72 grid cells, the weakest
crypto grid performance of the sizing-dial campaign this trigger. Volume-
based indicators (EMV, EFI, VZO/CMF/MFI family) appear to generalize to
crypto worse than pure-price trend-efficiency measures (VHF/CHOP/ADX),
plausibly because crypto exchange volume reporting is noisier/less
standardized than equity consolidated tape volume.
