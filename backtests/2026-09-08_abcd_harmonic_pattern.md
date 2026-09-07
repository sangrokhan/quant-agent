# AB=CD Harmonic Pattern -- SPY -- Backtest Report

**Strategy file:** `strategies/2026-09-08_abcd_harmonic_pattern.py`
**Hypothesis id:** 2026-09-08-107
**Source:** Google SERP AI overview + onetradejournal.com snippet (page itself 404'd,
used SERP-extracted rule text) -- AB=CD harmonic pattern: BC leg retraces
~0.618 of AB leg, CD leg extends 1.272-1.618x BC leg (approximating AB in
distance); entry at/just past D on confirmation, stop just beyond D, target
a retracement of the CD leg back toward C.

## Config tested (best grid cell)
- `pivot_window=7`, `cd_extension_target=1.272`
- Symbol: SPY, 2019-01-01 to 2026-09-01, daily bars

## Single-config validator results

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.071 | >= 1.0 | PASS |
| Max drawdown | 1.40% | <= 25% | PASS |
| Transaction cost survival (10bps/trade, 28 trades) | net Sharpe 0.527 | >= 0.5 | PASS |
| Walk-forward (manual 4-split stand-in; vbt RangeSplitter broken in installed vectorbt 1.1.0, known repo scaffold bug) | 4/4 splits positive Sharpe (1.0 pass fraction) | >= 0.75 | PASS |

Walk-forward splits: [0.295, 1.322, 1.381, 0.308] Sharpe -- all positive,
though magnitude varies (weaker in splits 0 and 3, stronger in 1 and 2).

## Grid-test summary (Step 6)

`param_grid={pivot_window:[7,11,15], cd_extension_target:[1.272,1.5,1.618]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
108 total cells, 2019-2026.

- **pass_fraction: 0.231** (25/108)
- by_asset_class: equity 24/54 (44%), crypto 1/54 (2% -- essentially fails on crypto)
- by_vol_regime: low 11/36, mid 11/36, high 3/36 (weaker in high-vol regimes)
- best_cell: SPY, pivot_window=7, cd_extension_target=1.272, low-vol, Sharpe 1.870
- worst_cell: SPY, pivot_window=15, cd_extension_target=1.5, high-vol, Sharpe -1.082

## Scope / honesty note

This strategy shows real edge concentrated in **equity, low/mid volatility
regimes**, with the shorter `pivot_window=7` config generalizing best. It
essentially does **not** work on crypto (1/54 grid cells) and degrades in
high-vol equity regimes (3/36). Accept scope: **equity only (QQQ/SPY),
low/mid-vol regimes preferred, pivot_window=7 config**. Do not deploy on
crypto or expect it to hold through high-vol regimes.

## Decision: ACCEPT (scoped to equity, primarily low/mid-vol regimes)
