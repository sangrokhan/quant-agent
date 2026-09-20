# Volume-Weighted Bollinger Bands Mean-Reversion — Backtest Report (2026-09-21)

## Hypothesis

Per Google's AI-overview synthesis (corroborated by multiple TradingView
script listings, https://www.google.com/search?q=%22Volume+Weighted+Bollinger+Bands%22+strategy+formula+entry+exit+rule,
read via browser_exec — web_search backend intermittently TLS-erroring this
iteration): Volume-Weighted Bollinger Bands (VWBB) use a Volume-Weighted
Moving Average (VWMA) as the centerline instead of a plain SMA, and a
volume-weighted standard deviation for band width, making the bands "more
sensitive to volume" than standard Bollinger Bands. Tested here as a
mean-reversion signal: long when close drops below the lower VWBB band
while price remains above a longer-term SMA trend filter; exit at the VWMA
centerline or a time-stop.

Source URL: https://www.google.com/search?q=%22Volume+Weighted+Bollinger+Bands%22+strategy+formula+entry+exit+rule

## Strategy file

`strategies/2026-09-21_vwbb_meanrev_trend_gate.py`

## Grid test summary (Step 6)

- Grid: `window` ∈ {15, 20, 30}, `band_mult` ∈ {1.5, 2.0, 2.5}
- Symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- Vol regime splits: 3
- Total cells: 108, passed: 5, **pass_fraction = 0.046**
- By asset class: equity 4/54 passed (avg Sharpe 0.172), crypto 1/54 passed
  (avg Sharpe 0.337) — decisively weak on both
- By vol regime: low 0/36, mid 1/36, high 4/36 — inverted from the typical
  mean-reversion pattern (usually works best in low-vol/range-bound
  regimes); here it barely works anywhere and what little edge exists is in
  high-vol regimes, which is not a coherent/robust pattern to trust
- Best cell: window=30, band_mult=1.5, SPY, high-vol, Sharpe=1.29 (isolated,
  not supported by any neighboring cell)
- Worst cell: window=15, band_mult=2.0, SPY, low-vol, Sharpe=-0.86

## Decision: REJECTED (decisive, no full validator run needed)

Pass fraction of 4.6% across the full grid, near-zero average Sharpe on
both asset classes, and no coherent vol-regime pattern (the one pocket of
apparent edge is in high-vol regime, isolated and not corroborated by
neighboring parameter values) make this a clear reject without needing the
full single-config validator suite — consistent with RESEARCH_LOOP.md's
allowance to reject decisively-failing candidates efficiently. The
volume-weighting mechanism itself does not appear to add tradeable value
over the many already-tested plain-SMA Bollinger Band mean-reversion
variants in this repo.
