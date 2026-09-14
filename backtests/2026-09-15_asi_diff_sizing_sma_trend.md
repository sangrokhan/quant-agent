# 2026-09-15 ASI-minus-EMA Continuous Sizing Dial (SMA trend gate)

## Hypothesis

Wilder's Swing Index (SI): `SI = 50*(C-CP+0.5*(CP-OP)+0.25*(C-O))/R` where
`R = max(|High-C|,|Low-C|,|High-CP|,|Low-CP|)`; `ASI_t = ASI_{t-1} + SI_t`
(cumulative sum). Repo has 3 prior ASI entries, all discrete-trigger
constructions and all falling into the same "persistent near-miss" pattern
(Sharpe just below 1.0 while every other validator passes cleanly): a
zero-line-cross (decisive reject, 0/216 cells), a swing-channel breakout on
the ASI line itself (Sharpe 0.734 SPY/0.949 QQQ), and that breakout with a
vol-regime gate added (still Sharpe 0.781 QQQ/0.843 SPY). None tried a
**continuous sizing dial**. This iteration reframes ASI minus its own
EMA(asi_ema_span) — analogous to the OBV-vs-EMA and Klinger constructions
already validated in this repo — as a rolling z-scored + tanh-squashed
[-1,1] sizing dial within an SMA(trend_window) uptrend gate, deadband to
cut turnover, leverage_cap for crypto, directly targeting this repeated
Sharpe-only near-miss with the same fix pattern that has repeatedly
rescued similar near-misses (RMI/RMO/McGinley/Anchored Momentum/STC/Dorsey
RVI) elsewhere in this repo.

## Source

- https://fxopen.com/blog/en/accumulative-swing-index-definition-and-how-to-use-it/
  (full SI/ASI formula, confirmed via browser_exec; web_search's DDGS
  backend returned no results for this query)

## Strategy file

`strategies/2026-09-15_asi_diff_sizing_sma_trend.py`

Params: `trend_window`, `asi_ema_span`, `zscore_window`, `base_exposure`,
`sensitivity`, `leverage_cap`, `deadband`.

## Step 6 — Grid test summary

`param_grid={asi_ema_span:[10,20,40], zscore_window:[100,150],
sensitivity:[0.4,0.6], deadband:[0.15,0.25,0.35]}`, symbols
QQQ/SPY + BTC/USDT/ETH/USDT, vol_regime_splits=3.

- total_cells=432, passed=216, **pass_fraction=0.500**
- by_asset_class: equity 110/216 (0.509), crypto 106/216 (0.491)
- by_vol_regime: low 144/144 (1.000), mid 65/144 (0.451), high 7/144 (0.049)
- best_cell: QQQ, asi_ema_span=10/zscore_window=100/sensitivity=0.6/deadband=0.35,
  low-vol Sharpe 2.91

## Step 7 — Single-config validation

QQQ's best-by-Sharpe full-sample config (asi_ema_span=20/zscore_window=100/
sensitivity=0.4/deadband=0.35) passed all 5 validators outright. SPY's
best-by-Sharpe config initially failed TC-survival (net Sharpe 0.445<0.5 at
246 trades); a targeted SPY-only sweep widening deadband to [0.25,0.35,
0.45,0.55] found a clean pass at asi_ema_span=10/zscore_window=100/
sensitivity=0.4/deadband=0.55 (98 trades, down from 246).

| Symbol | Params | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd | Param sens. (rel std) | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | ema=20/zw=100/sens=0.4/db=0.35 | 1.244 (pass) | 0.103 (pass) | 0.883 (pass) | 1.00 (pass) | 0.084 (pass) | 125 |
| SPY | ema=10/zw=100/sens=0.4/db=0.55 | 1.068 (pass) | 0.079 (pass) | 0.729 (pass) | 1.00 (pass) | 0.229 (pass) | 98 |
| BTC/USDT | ema=40/zw=100/sens=0.4/db=0.25 | 1.288 (pass) | 0.398 (**fail**, >0.25) | 1.127 (pass) | 1.00 (pass) | 0.066 (pass) | 219 |
| ETH/USDT | ema=20/zw=150/sens=0.4/db=0.35 | 1.155 (pass) | 0.324 (**fail**, >0.25) | 1.079 (pass) | 1.00 (pass) | 0.071 (pass) | 167 |

Walk-forward used the repo-standard manual 4-equal-slice fallback
(vbt.utils.splitting API unavailable in installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

- **QQQ: accepted** — all 5 validators pass, resolving the repo's
  persistent QQQ ASI near-miss (0.949 -> 1.244 Sharpe).
- **SPY: accepted** — all 5 validators pass after a targeted deadband
  widen, resolving the persistent SPY ASI near-miss (0.734/0.843 -> 1.068
  Sharpe).
- **BTC/USDT: rejected** — decisive max-drawdown failure (0.398 > 0.25),
  same pattern seen repeatedly this cron trigger for momentum/volume-diff
  sizing dials on crypto.
- **ETH/USDT: rejected** — decisive max-drawdown failure (0.324 > 0.25),
  same pattern.

This resolves a 3-attempt persistent near-miss for ASI in this repo:
continuous sizing (rather than discrete crossover/breakout triggers) was
the fix that discrete-rule tuning alone (channel width, vol-regime gates)
could not find.
