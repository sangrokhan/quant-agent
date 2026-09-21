# Gravestone Doji Short Reversal — Backtest Report (2026-09-21)

## Hypothesis
Source: https://pinescriptforge.com/strategy/gravestone-doji (read via
browser_exec fallback; web_extract's ddgs backend cannot extract page
content). Gravestone Doji (long upper shadow, open/close/low all near the
bar's low) at resistance/after an uptrend is a bearish reversal signal.
Source's disclosed rules: short entry on doji + next-candle confirmation;
exit at stop above the upper shadow (source: "risk 1x ATR"), target the
nearest support (operationalized here as `target_atr_mult` x ATR below
entry), max-hold time-stop fallback.

Strategy file: `strategies/2026-09-21_gravestone_doji_short_reversal.py`

## Step 6 — Grid test summary
`grid_summary_gravestone_doji_short_reversal.json` /
`grid_cells_gravestone_doji_short_reversal.json`

- Grid: `upper_shadow_min_pct` in {0.5, 0.6, 0.7}, `target_atr_mult` in
  {1.5, 2.0, 3.0}, `trend_window` in {30, 50}; symbols QQQ/SPY (equity) and
  BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3 (low/mid/high tercile of
  realized vol); 216 total cells.
- **pass_fraction: 0.083** (18/216 cells passed Sharpe>=1.0 and MDD<=0.25).
- **by_asset_class**: equity 0/108 passed; crypto 18/108 passed.
- **by_vol_regime**: low 18/72 passed; mid 0/72; high 0/72.
- All 18 passing cells are BTC/USDT, low-vol-regime only, Sharpe ~1.06-1.17,
  MDD ~0.006-0.012 (tiny drawdown because signal fires very rarely inside
  that narrow tercile slice).
- Best cell: BTC/USDT, low-vol, `upper_shadow_min_pct=0.5,
  target_atr_mult=1.5, trend_window=30`, Sharpe 1.173.

## Step 7 — Single-config validation (BTC/USDT, best-cell params, full
2018-2026 sample, no vol-regime gate)

Params: `upper_shadow_min_pct=0.5, target_atr_mult=1.5, trend_window=30`
(full sample, not restricted to the low-vol tercile the grid cherry-picked).

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | -0.082 | >= 1.0 |
| max_drawdown | **False** | 0.251 | <= 0.25 |
| transaction_cost_survival | **False** | -0.095 net Sharpe (10bps/trade, 8 trades) | >= 0.5 |
| walk_forward (4 splits) | **False** | 0.5 pass fraction ([F,F,T,T]) | >= 0.75 |
| parameter_sensitivity | True | rel_std 0.050 (across the 18 low-vol-tercile cells only) | <= 0.5 |

Only **8 position changes** (4 round-trip trades) occurred over the entire
2018-2026 BTC/USDT daily sample under these params — the Gravestone Doji +
uptrend + bearish-confirmation conjunction is extremely rare. The grid's
apparent 18-cell "pass" cluster is an artifact of restricting to the
low-vol-regime tercile subset, which shrinks the sample small enough that a
couple of lucky trades produce an inflated Sharpe with near-zero MDD — not
a robust edge. Full-period validation (Step 7) shows the strategy is flatly
unprofitable and fails every core validator except parameter_sensitivity
(which is trivially satisfied because there's so little variance across an
already-tiny, cherry-picked cell set).

## Step 8 — Decision: **REJECT**

Rejection reason: fails Sharpe, max drawdown, transaction-cost survival,
and walk-forward on the full-period single-config validation; the grid's
narrow "low-vol-regime, crypto-only" pass cluster is a small-sample
artifact (only a handful of trades), not evidence of a genuine edge. Unlike
prior successful vol-regime-gate rescues in this repo (e.g.
2026-09-21-225 Ascending Scallop), here the edge doesn't hold up even
within its own best-looking regime slice once tested standalone — trade
count is too low to draw any statistical conclusion, and a vol-regime gate
would only shrink the sample further.

Strategy file and this report are kept as a record of a rejected attempt.
