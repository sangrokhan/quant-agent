# 2026-09-23 CMO Mean-Reversion Snapback with Time Stop (SPY/QQQ/BTC/ETH)

## Hypothesis
Source: Google AI Overview (search: "Chande Momentum Oscillator CMO trading
strategy specific threshold rule backtest"), read via browser_exec Google
SERP fallback (web_search DDGS backend errored on this query).

Rule: CMO(9) mean-reversion snapback -- long entry when CMO drops below -50
then crosses back above -50 (oversold bounce); exit when CMO rises above
+50, or a forced time-based stop after 5 trading bars. First appearance of
the CMO indicator family in this knowledge base.

## Grid test summary (cmo_window x [9,14,20], max_hold_bars x [5,10],
oversold_threshold x [-50,-60]; symbols QQQ/SPY equity, BTC/USDT ETH/USDT
crypto; vol_regime_splits=3; 144 total cells)

- pass_fraction: 0.035 (5/144) -- extremely weak, close to noise
- by_asset_class: equity 2/72, crypto 3/72
- by_vol_regime: low 0/48, mid 3/48, high 2/48
- best_cell: cmo_window=20, max_hold_bars=10, oversold_threshold=-50,
  equity QQQ, mid-vol, Sharpe 1.51 (isolated cell, not representative)
- worst_cell: cmo_window=20, max_hold_bars=5, oversold_threshold=-50,
  crypto ETH/USDT, low-vol, Sharpe -1.19

Full parameter sweep for best full-period (unconditional) Sharpe across all
symbol/config combos: best was only 0.328 (cmo_window=9, max_hold_bars=5,
oversold_threshold=-60, SPY) -- far short of the 1.0 threshold, and the
extremely low overall pass_fraction (3.5%) indicates this is not a robust
edge, just noise in isolated grid cells.

## Verdict: REJECTED

Full-period Sharpe fails decisively (best 0.328) and the grid pass fraction
(0.035) is too low and too scattered across regimes/asset classes to
indicate a real, exploitable edge -- unlike the prior HMA iteration
(2026-09-23-028) which at least had a clear, concentrated low-vol-regime
signal (0.54 pass rate in low-vol), this CMO snapback rule shows no
coherent regime-conditional pattern either (0 in low-vol, only 3/48 in
mid, 2/48 in high). Walk-forward/tx-cost/param-sensitivity validators
skipped given the decisive full-grid Sharpe failure.

Strategy file kept in `strategies/` as a record of a rejected attempt (not
live). Not recommended for revisiting with parameter tweaks alone -- the
5-bar time-stop combined with a fixed +-50 CMO threshold does not appear to
capture a real edge on daily equity or crypto-default-interval bars; if
revisited, would need a fundamentally different confirmation filter (e.g.
volume or trend-regime gate) rather than more threshold tuning.
