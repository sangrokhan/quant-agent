# Backtest Report: PVO-Confirmed N-Day-High Breakout

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_pvo_confirmed_breakout.py`
**KB id:** 2026-09-27-107

## Hypothesis

Source: [StockCharts ChartSchool — Percentage Volume Oscillator (PVO)](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-volume-oscillator-pvo)
(visited this iteration; first PVO-family entry in this repo, 0 prior KB
hits). PVO=((12d EMA vol - 26d EMA vol)/26d EMA vol)*100. Source: "A
resistance break on expanding volume shows more buying interest, increasing
the chances of success." Entry: close breaks above the highest close of the
prior `breakout_window` days AND PVO(12,26,9) is positive and rising
(volume already above its own recent average, and still increasing).
Exit: close falls below SMA(exit_window), or a max_hold_days time-stop.

## Step 6 — Grid summary

Grid: `breakout_window` in [15, 20, 30] x `exit_window` in [10, 20],
symbols equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), 3 vol-regime terciles,
72 cells.

- **pass_fraction: 0.375 (27/72)**
- by_asset_class: equity 10/36, crypto 17/36
- by_vol_regime: low 16/24, mid 11/24, **high 0/24** — the strategy works
  exclusively in low/mid volatility regimes and decisively fails to hold up
  in high-vol regimes across all symbols (Sharpe negative in nearly every
  high-vol cell).
- best_cell: breakout_window=15, exit_window=10, crypto ETH/USDT, mid-vol,
  Sharpe 2.32
- worst_cell: breakout_window=20, exit_window=20, equity QQQ, high-vol,
  Sharpe -1.26

## Step 7 — Full-period validators (config: breakout_window=20, exit_window=20)

| Symbol | Trades | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 16 | -0.038 (FAIL) | 0.216 (PASS) | -0.076 (FAIL) | 0.25 (FAIL) | 2.80 (FAIL) |
| SPY | 16 | 0.408 (FAIL) | 0.095 (PASS) | 0.353 (FAIL) | 0.75 (PASS) | 0.10 (PASS) |
| BTC/USDT | 1082 | 0.252 (FAIL) | 0.285 (FAIL) | 0.096 (FAIL) | 1.00 (PASS) | 0.09 (PASS) |
| ETH/USDT | 1062 | 0.295 (FAIL) | 0.329 (FAIL) | 0.152 (FAIL) | 1.00 (PASS) | 0.05 (PASS) |

All 4 symbols fail Sharpe (threshold 1.0) over the full 7.5-year period, even
though the grid's low/mid-vol terciles looked promising. Crypto additionally
fails max drawdown (mixing in high-vol regime losses drags MDD past 25%) and
has an enormous trade count (~1000+ trades) making transaction-cost drag
severe. The grid's regime-sliced good performance does not survive when the
regimes are combined into one continuous full-period backtest.

## Step 8 — Decision: REJECTED (all symbols)

Rejected on full-period Sharpe failing decisively across all 4 tested
symbols, plus MDD failure on both crypto symbols and TC-survival failure on
all 4. The PVO volume-confirmation gate does not prevent the strategy from
trading heavily (and losing) during high-vol regimes when run continuously
rather than vol-regime-isolated — high-vol cells in the grid were uniformly
losing (0/24 pass), and those periods dominate full-sample drawdown/Sharpe.

**Notes for future loops:** the vol-regime breakdown (low/mid strong, high
uniformly failing) suggests a genuine ADX/realized-vol regime gate added on
top of the PVO-confirmed breakout (explicitly excluding high-vol trading,
not just implicitly hoping PVO handles it) could be worth testing as a
direct fix, similar to the fix pattern used for other near-miss trend
strategies in this repo.
