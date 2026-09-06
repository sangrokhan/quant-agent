"""Backtest report: Classic Floor-Trader Pivot Point S1 Bounce mean reversion.

Hypothesis id: 2026-09-07-025
Strategy file: strategies/2026-09-07_classic_pivot_s1_bounce.py
Outcome: **REJECTED**

## Hypothesis

Per ArrowAlgo's "Pivot Point Trading Strategy" guide's "S1 Bounce (Mean
Reversion)" rule: classic floor-trader daily pivot (P=(prior H+L+C)/3,
S1=2P-prior_H), long entry when today's low touches/dips to S1 but
today's close recovers back above S1 (same-bar bounce filter); exit at
the pivot P itself or a max_hold_days time-stop. First CLASSIC S1-bounce
mean-reversion strategy in this repo, distinct from the already-tested
pivot BREAKOUT variant (2026-09-04-073) and Camarilla pivots
(2026-09-04-119, different formula/levels entirely).

## Step 6 grid summary (max_hold_days in [3,5,10], symbols
QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- total_cells: 36, passed_cells: 4, pass_fraction: **0.111**
- by_asset_class: equity 4/18 (0.222), crypto 0/18 (0.0, decisive)
- by_vol_regime: low 1/12, mid 0/12, high 3/12 -- no consistent regime,
  scattered passes
- best_cell: SPY, max_hold_days=10, high-vol regime, Sharpe 1.261

## Step 7 single-config validation (max_hold_days=10, full 2019-2026
sample, QQQ & SPY)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.546 (FAIL) | 0.918 (FAIL, near-miss) | >= 1.0 |
| Max drawdown | 0.304 (FAIL) | 0.187 (PASS) | <= 0.25 |
| Tx-cost survival (5bps, 283/291 trades) | 0.359 (FAIL) | 0.627 (PASS) | >= 0.5 net Sharpe |
| Walk-forward | not run -- decisive/near-miss full-sample results plus pre-existing `vbt.utils.splitting` bug | | |
| Parameter sensitivity | not run -- scattered low grid pass_fraction already conclusive of instability | | |

## Decision

**Rejected.** QQQ fails decisively on Sharpe, MDD, and TC-survival. SPY
is a near-miss on Sharpe (0.918) but passes MDD and TC-survival --
promising enough to flag for a future revisit (e.g. tightening the S1
touch condition or adding a trend filter), but not accept-worthy on its
own this iteration since the strategy's grid pass_fraction is low and
scattered (0.111, no consistent vol-regime concentration) and crypto
rejects categorically (0/18 grid cells). The very high trade count
(283-291 over 7.7yr) suggests S1 gets touched-and-recovered frequently
in normal price noise, diluting the strategy's edge similarly to the
4-indicator confluence strategy tested earlier this cron trigger
(2026-09-07-024).

Source: https://arrowalgo.com/ Pivot Point Trading Strategy guide (page
itself 404'd on direct fetch via browser_exec, read via Google
search-result snippet only), corroborated by a UNIVPM academic thesis
PDF's own pseudo-code reference to a "BreakP_Long"/S1-bounce pivot
strategy variant (PDF not directly extracted -- web_extract failed on
the DuckDuckGo backend, browser_exec Google search snippet used instead
per RESEARCH_LOOP.md's fallback guidance).
"""
