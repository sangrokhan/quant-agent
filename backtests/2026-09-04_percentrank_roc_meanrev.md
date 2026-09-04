# PercentRank(ROC) Mean Reversion (Cesar Alvarez) — Backtest Report (2026-09-04)

## Hypothesis
Cesar Alvarez (alvarezquanttrading.com): instead of a raw Rate-of-Change
(ROC) threshold to flag a sell-off (which doesn't normalize across
low/high-volatility names), rank today's short-term ROC against its own
trailing-year history via PercentRank. Source's full rule set: setup =
close > SMA(100) AND 252-day PercentRank of ROC(2) below a low threshold
(~5); exit when RSI(2) > 40. We implement the same logic with a same-day
market entry (source uses a limit order 1/2*ATR below the previous close,
not simulated here) and add a max_hold_days safety time-stop.

Source: https://alvarezquanttrading.com/blog/using-recent-returns-for-mean-reversion/
(web_search failed for both original queries this iteration -- DDGS
RequestError -- fell back to browser_exec Google search, whose SERP
surfaced this article on the second query attempt).

## Grid summary (Step 6)
`param_grid={entry_pct_rank:[5.0,10.0,15.0], max_hold_days:[7,10]}`
(roc_period=2, lookback=252, trend_window=100, exit_rsi_threshold=40
fixed), symbols `{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01..2026-09-01.

- total_cells=72, passed_cells=16, **pass_fraction=0.222**
- by_asset_class: equity 16/36, crypto **0/36**
- by_vol_regime: low 10/24, mid 2/24, high 4/24
- best_cell: entry_pct_rank=15.0, max_hold_days=7, QQQ, low-vol, Sharpe=2.09
- worst_cell: entry_pct_rank=5.0, max_hold_days=7, SPY, high-vol, Sharpe=-0.13

## Single-config validation (Step 7)
Config: entry_pct_rank=15.0, max_hold_days=7 (grid-best cell config).
Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.305 (pass) | 0.787 (**fail**) |
| Max drawdown (<=0.25) | 0.107 (pass) | 0.112 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 1.044 (pass) | 0.508 (pass, near-miss) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 1.0, 4/4 splits positive (pass) | 0.5, 2/4 splits positive (**fail**) |
| Parameter sensitivity (entry_pct_rank in {5,10,15}, rel std <=0.5) | 0.442 (pass) | 0.205 (pass) |
| num_trades | 82 | 80 |

Same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Accept for QQQ** — all 5 standard validators pass (Sharpe 1.305, MDD
0.107, TC-survival 1.044, walk-forward perfect 4/4, parameter sensitivity
0.442 near but under the 0.5 threshold).
**Reject for SPY** — full-sample Sharpe fails (0.787) and walk-forward
fails decisively (only 2/4 splits positive, both early splits negative);
TC-survival is a near-miss pass (0.508) but the other two failures rule
it out.
**Reject for crypto** — 0/36 grid cells pass.

Consistent with the pattern of many mean-reversion strategies in this log
(Connors RSI, RSI(2), etc.) landing as QQQ-accepted / SPY-near-miss or
rejected -- QQQ's higher baseline volatility appears to generate cleaner
oversold setups for the PercentRank(ROC) trigger than SPY's comparatively
calmer index behavior.
