# 2026-09-23 — SMA Trend-Following Gated to High-Vol Tercile Only

## Hypothesis

Per Prashant Malan's SSRN paper "One Ticker Deep: The Trend Strategy That
Passed Every Test and Still Shouldn't Be Believed" (SSRN abstract_id=7073258,
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7073258, read via
browser_exec this iteration — web_search DDGS/Yahoo backend TLS-errored on
every query attempted), a plain long-only trend rule ("hold names trading
above their own moving average, else cash") passed walk-forward with
out-of-sample Sharpe 1.36–1.53 in the source's own cross-sectional equity
universe. The source's own attribution analysis found the edge is monotone
in volatility and concentrated ENTIRELY in the top volatility tercile of
the universe — in the bottom two terciles the strategy underperformed
buy-and-hold. This iteration tests the mirror-image gate of this repo's
usual "low-vol-only" filters: gate a plain SMA(trend_window) trend-following
rule to trade ONLY when the asset's own trailing realized-vol percentile
rank is in the top tercile (>= vol_percentile_floor of its own trailing
252-day history).

Source URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7073258

## Grid summary (Step 6)

- Grid: trend_window ∈ {50,100,150} × vol_percentile_floor ∈ {0.6,0.667,0.75}
  × {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol terciles = 108 cells.
- pass_fraction: 8/108 = 0.074
- by_asset_class: equity 8/54 passed; crypto 0/54 passed
- by_vol_regime: low 3/36, mid 3/36, high 2/36
- best_cell: crypto BTC/USDT high-vol, trend_window=100, floor=0.75, Sharpe 1.27
  (but crypto asset class as a whole 0/54 — this cell is an outlier, not
  representative, and worst_cell same params on ETH/USDT is Sharpe -0.29)
- Notable equity passes: SPY high-vol-tercile cells at trend_window=50,
  floor=0.667/0.75 (Sharpe 1.16/1.22, MDD 0.06-0.10) — the config closest to
  the source's own thesis.

## Single-config validation (Step 7) — SPY, trend_window=50, vol_percentile_floor=0.75

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full sample) | FAIL | 0.738 | 1.0 |
| max_drawdown | pass | 0.080 | 0.25 |
| transaction_cost_survival | pass | 0.628 (net Sharpe) | 0.5 |
| walk_forward (4-split, manual fallback) | FAIL | 0.5 pass_fraction | 0.75 |
| parameter_sensitivity | pass | 0.20 relative std | 0.5 |

## Decision: REJECTED

Full-sample Sharpe (0.738) and walk-forward pass-fraction (0.5, splits 1-2
failed) both miss threshold, despite an attractive Sharpe when the same
config's returns are masked down to only the grid's independently-computed
high-vol-tercile days (1.22). The gap between the grid's regime-masked
Sharpe and the strategy's own actual full-sample Sharpe is the key
diagnostic: because the strategy's OWN entry condition (trailing vol
percentile rank >= floor) does not perfectly align with the grid's
after-the-fact tercile labeling of the full sample, a large fraction of the
strategy's actual trading days fall outside what the grid calls "high vol"
— so restricting entries this way does not cleanly reproduce the source's
own attribution finding. Net: the source's own paper is explicitly a
methodological cautionary tale (title: "...Still Shouldn't Be Believed"),
warning that even a clean walk-forward pass can be an artifact of
concentration (one stock, one vol tercile) rather than a real
generalizable edge — this repo's own test corroborates that skepticism:
the mirror-image gate does not survive full-sample walk-forward here either.
