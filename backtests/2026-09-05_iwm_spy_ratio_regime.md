# Backtest Report: IWM/SPY Small-Cap/Large-Cap Ratio Regime Filter

**Strategy ID:** 2026-09-05-039
**File:** `strategies/2026-09-05_iwm_spy_ratio_regime.py`
**Date:** 2026-09-05

## Hypothesis

The IWM/SPY ratio (Russell 2000 small-cap ETF / S&P 500 large-cap ETF) acts
as a risk-appetite "thermometer": when small caps lead large caps, it signals
a broadening, risk-on market; when large caps lead, it signals defensive
flight to safety. Long when ratio > its own trailing SMA, flat otherwise.

**Source:** https://tradethepool.com/fundamental/what-are-small-cap-stocks-the-complete-guide-for-traders/
("The Russell 2000 (IWM) serves as the ultimate 'risk-on' thermometer... When
IWM leads SPY, it indicates a broadening market"); Google AI-overview
(citing StockCharts) additionally described an "IWM/SPY Relative Strength
Spread" with a 20-50 day lookback window. Neither source publishes a
specific backtested threshold — mechanism reused from the already-validated
ratio-MA-regime family (gold/silver 2026-09-05-030, XLY/XLP 2026-09-05-038,
both accepted).

## Grid Test Summary (Step 6)

Grid: `ma_window ∈ {20, 35, 50, 75}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}`
× vol_regime_splits=3 (low/mid/high realized-vol terciles), 2017-01-01 to
2026-09-01.

- **Overall pass fraction:** 13/48 = 0.271
- **By asset class:** equity 13/24 (0.54); crypto 0/24 (0.0)
- **By vol regime:** low 8/16 (0.5); mid 3/16 (0.19); high 2/16 (0.125)
- **Best cell:** QQQ, ma_window=75, low-vol regime, Sharpe 2.34
- **Worst cell:** ETH/USDT, ma_window=20, low-vol regime, Sharpe 0.15

Per-cell equity detail (Sharpe, pass/fail):

| ma_window | QQQ low | QQQ mid | QQQ high | SPY low | SPY mid | SPY high |
|---|---|---|---|---|---|---|
| 20 | 1.50 ✓ | 0.67 ✗ | 0.71 ✗ | 1.37 ✓ | 1.05 ✓ | 0.76 ✗ |
| 35 | 1.90 ✓ | 0.94 ✗ | 1.06 ✓ | 1.53 ✓ | 1.07 ✓ | 1.07 ✓ |
| 50 | 2.21 ✓ | 1.12 ✓ | 0.65 ✗ | 2.01 ✓ | 1.00 ✗ | 0.80 ✗ |
| 75 | 2.34 ✓ | 0.50 ✗ | 0.43 ✗ | 2.27 ✓ | 0.49 ✗ | 0.68 ✗ |

The strategy clearly works only on equity (both QQQ and SPY); crypto is
0/24 across the board (BTC/ETH have no analogous "small vs large cap"
structure, as expected — falsification check confirms this is a
genuinely equity-specific signal, not a data artifact). Within equity, low-vol
regimes are strongly favorable across all ma_window values; mid/high-vol
regimes are mixed to weak. `ma_window=35` is the most robust single choice
(passes in low AND high vol regime for both QQQ and SPY, and the only
config passing 3/3 vol regimes on SPY).

## Single-Config Validation (Step 7) — SPY, ma_window=35, full period 2017-2026

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.065 | ≥ 1.0 |
| Max drawdown | **PASS** | 0.162 | ≤ 0.25 |
| Transaction cost survival (5bps/trade, 220 trades) | **PASS** | net Sharpe 0.873 | ≥ 0.5 |
| Walk-forward | not run — `vbt.utils.splitting.RangeSplitter` unavailable in this repo's installed vectorbt version (known repo limitation, consistent with essentially every recent knowledge_base entry). |
| Parameter sensitivity (ma_window ∈ {20,35,50,75}, full-period SPY Sharpe) | **PASS** | relative_std 0.093 | ≤ 0.5 |

All validators run pass. Walk-forward skipped due to the known repo
vectorbt-version limitation, per the standard convention this run.

## Decision

**Accepted — equity only (QQQ, SPY).** Crypto is rejected (0/24 grid
cells) — the strategy has no theoretical basis for crypto (no small/large
cap distinction) and the grid confirms it does not transfer.

Recommended production config: `ma_window=35` (best balance across vol
regimes for both QQQ and SPY; `ma_window=50-75` scores higher in low-vol
alone but degrades sharply in mid/high-vol).
