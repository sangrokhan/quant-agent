# Wyckoff Spring accumulation-shakeout long entry

## Hypothesis
Richard Wyckoff's "spring" pattern: within an accumulation range, price
makes a brief failed breakdown below support on light volume (a shakeout),
then reclaims support on expanding volume, signaling absorption by smart
money. Per TradingSim's explicit mechanical rule: "Setup: an accumulation
zone at least two weeks old, a break below support on light volume, then a
reclaim of support on expanding volume. Entry: the close back above
support... Stop: just below the spring low. Target: the top of the zone."

Source: https://www.tradingsim.com/blog/wyckoff-method-trading
("Entry and Exit Rules for Wyckoff Trades" section, read in-browser).

First Wyckoff-family strategy in this repo -- a genuinely new pattern
construction (volume-confirmed failed-breakdown-then-reclaim inside a
detected consolidation range).

## Grid test (Step 6)
`param_grid={"range_width_pct": [0.06,0.08,0.12], "reclaim_window": [3,5]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`. 2019-01-01 to 2026-09-01.

- total_cells: 72, passed: 0, **pass_fraction: 0.0**
- by_asset_class: equity 0/36, crypto 0/36
- by_vol_regime: low 0/24, mid 0/24, high 0/24
- best_cell: range_width_pct=0.08, reclaim_window=3, SPY, high-vol, Sharpe 0.90 (still below threshold)
- worst_cell: same params, SPY, mid-vol, Sharpe -1.10

## Decision: REJECT
Decisive 0/72 grid pass fraction across both asset classes and all
volatility regimes. Signal is also very sparse (16 trades on QQQ full
sample, default params) -- the accumulation-zone detection proxy
(rolling-range-width threshold) combined with the light/expanding-volume
condition rarely fires cleanly enough to produce a robust edge on daily
bars. No full validator suite run given the uniformly decisive 0-pass grid.

## Notes
- Strategy file kept in `strategies/` as a rejected-attempt record.
- The daily-bar accumulation-zone/volume-confirmation proxies used here are
  necessarily simplifications of Wyckoff's original discretionary,
  chart-pattern-based method; a future iteration could try intraday bars or
  a different range-detection heuristic (e.g. ADX-based instead of
  rolling-width-based) if revisiting this indicator family.
