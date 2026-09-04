# Backtest Report: McGinley Dynamic Fast/Slow Crossover (2026-09-04)

**Strategy file:** `strategies/2026-09-04_mcginley_dynamic_crossover.py`
**Knowledge base id:** 2026-09-04-127
**Outcome:** REJECTED (near-miss)

## Hypothesis

The McGinley Dynamic (John R. McGinley, 1990) is an adaptive moving average:
`MD_t = MD_{t-1} + (Price_t - MD_{t-1}) / (N * (Price_t/MD_{t-1})^4)`, which
speeds up in fast/volatile markets and slows in calm ones. Standard trading
rule (fxopen.com): fast-period McGinley Dynamic crossing above slow-period
McGinley Dynamic = bullish long entry; crossing back below = exit. First
McGinley Dynamic strategy in this repo.

Source: https://fxopen.com/blog/en/how-to-trade-with-the-mcginley-dynamic-indicator/

## Grid test summary (fast_n in {8,10,14} x slow_n in {30,40}, max_hold_days=20, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 72, passed_cells: 17, pass_fraction: 0.236
- by_asset_class: equity 17/36, crypto 0/36
- by_vol_regime: low 10/24, mid 7/24, high 0/24
- best_cell: QQQ, fast_n=10, slow_n=30, low-vol, Sharpe=1.946

## Single-config validation (fast_n=10, slow_n=30, max_hold_days=20)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.511 (FAIL) | 0.721 (FAIL) | >= 1.0 |
| Max drawdown | 0.147 (PASS) | 0.083 (PASS) | <= 0.25 |
| TC survival (net Sharpe) | 0.486 (FAIL, near-miss) | 0.681 (PASS) | >= 0.5 |
| Walk-forward (4 splits) | 1.00 (PASS) | 0.75 (PASS) | >= 0.75 |
| Parameter sensitivity (rel std) | 0.436 (PASS) | 0.256 (PASS) | <= 0.5 |

Additional configs checked for full-sample Sharpe (all fail 1.0 threshold on
both symbols): (fast10,slow40): QQQ 0.32/SPY 0.47; (fast14,slow40): QQQ
0.33/SPY 0.55; (fast8,slow40): QQQ 0.56/SPY 0.34; (fast8,slow30): QQQ
0.69/SPY 0.75.

## Verdict

Rejected as a near-miss. Grid pass_fraction is respectable (0.236) and MDD/
walk-forward/parameter-sensitivity pass cleanly, but full-sample Sharpe
fails on every one of 5 parameter combos checked on both symbols -- the
strong regime-conditional performance (Sharpe 1.95 in QQQ low-vol) doesn't
survive dilution by the high-vol regime (worst_cell Sharpe -0.62). Crypto
rejected outright (0/36 grid cells).
