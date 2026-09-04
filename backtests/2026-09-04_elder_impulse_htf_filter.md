# Backtest Report: Elder Impulse System + Higher-Timeframe Filter (2026-09-04)

**Strategy file:** `strategies/2026-09-04_elder_impulse_htf_filter.py`
**Knowledge base id:** 2026-09-04-125
**Outcome:** REJECTED (near-miss)

## Hypothesis

Alexander Elder's Impulse System colors bars green when both a 13-EMA and
MACD(12,26,9) histogram are rising (bulls control trend+momentum). Elder
himself recommends only trading impulse signals aligned with a
higher-timeframe (~5x) trend; here approximated as a 65-period (13x5) EMA
slope filter computed directly on daily bars. This directly extends the
already-rejected bare Impulse System (2026-09-04-064) by adding the HTF
filter Elder considered essential.

Source: https://www.quantifiedstrategies.com/elder-impulse-system/

## Grid test summary (htf_window in {50,65,90} x max_hold_days in {10,15}, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 72, passed_cells: 18, pass_fraction: 0.25
- by_asset_class: equity 18/36, crypto 0/36
- by_vol_regime: low 12/24, mid 6/24, high 0/24
- best_cell: SPY, htf_window=50, max_hold_days=10, low-vol, Sharpe=2.358

## Single-config validation (htf_window=65 [Elder's recommended 13x5], max_hold_days=15)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.794 (FAIL, near-miss) | 0.878 (FAIL, near-miss) | >= 1.0 |
| Max drawdown | 0.219 (PASS) | 0.143 (PASS) | <= 0.25 |
| TC survival (net Sharpe) | 0.338 (FAIL) | 0.236 (FAIL) | >= 0.5 |
| Walk-forward (4 splits) | 0.75 (PASS) | 1.00 (PASS) | >= 0.75 |
| Parameter sensitivity (rel std) | 0.066 (PASS) | 0.034 (PASS) | <= 0.5 |

## Verdict

Rejected as a near-miss. The HTF filter clearly improves robustness
(MDD comfortably under threshold, clean walk-forward and parameter
sensitivity on both symbols) versus the bare version, but full-sample
Sharpe falls short on both QQQ and SPY, and ~227-228 trades over 7.7yr
means transaction costs erode the edge below the 0.5 net-Sharpe survival
bar. Crypto rejected outright (0/36 grid cells).
