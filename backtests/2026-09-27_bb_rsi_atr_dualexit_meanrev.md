# Backtest Report: BB+RSI+ATR Dual-Exit Mean Reversion (2026-09-27)

## Hypothesis

Per https://medium.com/@redsword_23261/mean-reversion-strategy-with-bollinger-bands-rsi-and-atr-based-dynamic-stop-loss-system-02adb3dca2e1
(Sword Red, Dec 2024, FMZ Quant Pine Script source, read via `browser_exec`
fallback -- `web_extract`'s ddgs backend cannot fetch page content):
20-period Bollinger Bands (2.0 std) + 14-period RSI (30/70) identify extreme
mean-reversion setups. Source's own exit is a RACE between a soft
band/RSI-reversal exit and a hard 2x/3x ATR(14) stop/take-profit bracket,
whichever fires first. Adapted long-only (this repo's `generate_signals`
{0,1} convention).

Distinct from repo's 74+ prior BB+RSI hits (per 2026-09-22-084) via the
dual-race hard-ATR-bracket + soft-exit exit construction (not a plain
band/RSI-only exit, and not ATR-stop-alone as tested for other signal
families e.g. 2026-09-09-004).

## Grid test summary (Step 6)

param_grid: bb_std=[1.5,2.0,2.5], rsi_oversold=[25,30], atr_stop_mult=[1.5,2.0],
atr_target_mult=[3.0]; symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT];
vol_regime_splits=3 (2018-01-01 to 2026-09-01).

- total_cells: 144, passed_cells: 6, **pass_fraction: 0.0417**
- by_asset_class: equity 6/72 passed, crypto 0/72 passed (crypto: 0%)
- by_vol_regime: low 0/48, mid 6/48, high 0/48 -- ONLY passes in mid-vol
  regime cells, and only on equities
- best_cell: QQQ, mid-vol, bb_std=2.5/rsi_oversold=30/atr_stop_mult=1.5/atr_target_mult=3.0, Sharpe=1.34
- worst_cell: ETH/USDT, low-vol, Sharpe=-1.04

## Single-config validators (Step 7) -- best_cell config, full sample

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.319 FAIL | 0.285 FAIL | >= 1.0 |
| Max Drawdown | 0.113 PASS | 0.067 PASS | <= 0.25 |
| TC survival (10bps) | 0.306 FAIL | 0.269 FAIL | >= 0.5 |
| Walk-forward (4-split manual) | 1.0 PASS | 0.75 PASS | >= 0.75 |
| Parameter sensitivity | 0.442 PASS | 0.909 FAIL | <= 0.5 |
| num_trades | 6 | 5 | -- |

Full-sample Sharpe and TC-survival fail decisively on BOTH symbols; the
grid's "best cell" Sharpe of 1.34 only holds in the narrow mid-vol tercile
slice -- once evaluated across the whole 2018-2026 sample the edge collapses
(0.32/0.29), consistent with only 6/144 grid cells passing (4.2%). Trade
count is very low (5-6 trades over ~8.5 years per symbol) since the entry
requires both a 2.5-std band touch AND RSI<30 simultaneously -- an
infrequent joint condition -- so results are also statistically thin.

## Verdict: REJECTED

Fails full-sample Sharpe and transaction-cost survival on both equity
symbols tested; SPY additionally fails parameter sensitivity. Grid
pass_fraction of 4.2% confirms this is not a broadly robust edge -- it only
worked in a narrow mid-vol/equity/tight-parameter slice that does not
survive full-sample or cost-adjusted evaluation. Strategy file kept in
`strategies/` as a rejected-attempt record.
