# Ulcer Index Inverse-Volatility Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-170 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_ulcer_index_invvol_sizing_sma_trend.py`

## Hypothesis

Ulcer Index (Peter Martin & Byron McCann, 1987/1989): percent-drawdown from
the rolling N-period max close, squared, averaged, then square-rooted --
UI = sqrt(mean((100*(Close - RollingMaxClose)/RollingMaxClose)^2)). This
repo has 3 prior Ulcer Index entries (2026-09-04-144 low-UI-level long entry
gate, plus 2 UI-slope trend-following filters), ALL using UI as a BINARY
threshold/slope GATE for a separate entry trigger. None used UI's own
continuous magnitude as an INVERSE-VOLATILITY sizing dial. This iteration
follows the BBW/GAPO inverse-vol-conditioning pattern already validated
twice this cron trigger: rolling min-max normalize UI, INVERT it (low UI =
shallow/brief drawdowns = calm uptrend -> scale exposure UP; high UI = deep/
prolonged drawdown pain -> scale exposure DOWN), applied within an
SMA(trend_window) uptrend gate. First Ulcer Index continuous-sizing /
inverse-volatility-conditioning variant in this repo.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index
(fetched via browser_exec after web_extract's DuckDuckGo-only backend
returned a "search-only, cannot extract" error).

## Grid test summary (Step 6)

`param_grid={ui_window: [10,14,20], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 108, **passed:** 43, **pass_fraction:** 0.398.
- **by_asset_class:** equity 27/54 (0.500), crypto 16/54 (0.296).
- **by_vol_regime:** low 30/36 (0.833), mid 9/36 (0.250), high 4/36 (0.111).
- **best_cell:** QQQ, ui_window=10/sensitivity=0.6, low-vol, Sharpe 2.762.
- **worst_cell:** QQQ, ui_window=20/sensitivity=0.8, high-vol, Sharpe -0.375.

## Single-config validator results (Step 7)

Best grid config (ui_window=10, sensitivity=0.6) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.345 (pass) | 0.142 (pass) | 0.857 (pass) | 1.000 (pass) | 0.092 (pass) | **accepted** |
| SPY | 0.881 (**fail**, near-miss) | 0.100 (pass) | 0.351 (**fail**) | 0.750 (pass) | 0.058 (pass) | **rejected** |
| BTC/USDT | 0.123 (**fail**, decisive) | 0.253 (**fail**) | -0.064 (**fail**) | 1.000 (pass) | 0.117 (pass) | **rejected** |
| ETH/USDT | 0.146 (**fail**, decisive) | 0.302 (**fail**) | -0.060 (**fail**) | 0.750 (pass) | 0.105 (pass) | **rejected** |

## Decision

**Accepted (QQQ only):** clears all 5 validators comfortably at
leverage_cap=1.0 -- Ulcer Index's percentage-drawdown-severity construction,
reframed as a continuous inverse-volatility sizing dial rather than a binary
level/slope gate, rescues an indicator family whose 3 prior binary-gate
entries were mixed (1 accepted QQQ-only, 2 not accepted per index notes).
**Rejected (SPY):** near-miss -- Sharpe 0.881 just misses the 1.0 threshold
and TC-survival fails outright (0.351 vs 0.5), consistent with several
other equity sizing-dial variants this cron trigger where QQQ clears but
SPY's lower realized vol under the same config compresses net Sharpe below
threshold after cost drag.
**Rejected (crypto):** BTC/USDT, ETH/USDT -- decisive Sharpe/TC-survival
failures with MDD failures on both symbols even at leverage_cap=0.4 and very
high trade counts (5600+), consistent with this cron trigger's recurring
finding that daily-bar-calibrated drawdown/volatility-normalized sizing
dials transfer poorly to crypto's higher-frequency whipsaw regime.
