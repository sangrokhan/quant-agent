# Backtest report: Russell 2000 rebalancing seasonal (June 23–July 1)

**Strategy file:** `strategies/2026-09-24_russell_rebalancing_seasonal.py`
**Hypothesis source:** https://www.quantifiedstrategies.com/quantitative-trading-strategies/ (QuantifiedStrategies.com "8 Quantitative Trading Strategies" article, browser_exec)

## Hypothesis

Russell 2000 reconstitutes annually on the fourth Friday of June, and per
the source's own disclosed testing on the RUT cash index, price rallies
strongly around this event (small-cap effect). Source's own disclosed
exact rules: "Buy on the close of the first trading day after the 23rd
of June. Sell on the close on the first trading day of July." Source's
own disclosed RUT backtest stats: avg gain/trade 1.34%, win ratio 76%,
max drawdown 6%, profit factor 4.1. This strategy implements those exact
rules on IWM (small-cap ETF proxy) and SPY (broader-market spillover,
per the source's own note that "not only Russell 2000, but also the
broader market... performed very well").

## Grid test summary (Step 6)

`param_grid`: entry_day_of_month ∈ {20,23,26}, exit_day_of_month ∈
{1,3,5}; symbols: equity {IWM, SPY}, crypto {BTC/USDT, ETH/USDT} (no
seasonality rationale for crypto, included per RESEARCH_LOOP.md's
two-asset-class requirement); vol_regime_splits=3; period 2015-01-01 to
2026-09-01.

- **total_cells:** 108, **passed_cells:** 13, **pass_fraction:** 0.120
- **by_asset_class:** equity 12/54, crypto 1/54 (as expected — no economic rationale for crypto)
- **by_vol_regime:** low 10/36, mid 3/36, high 0/36
- **best_cell:** entry_day_of_month=26, exit_day_of_month=3, SPY low-vol, Sharpe=1.808

## Single-config validation (Step 7) — IWM & SPY, source's exact disclosed dates (entry_day_of_month=23, exit_day_of_month=1), full sample 2015-2026

| Validator | IWM | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** 0.269 | **FAIL** 0.602 | ≥ 1.0 |
| Max drawdown | PASS 0.064 | PASS 0.033 | ≤ 0.25 |
| Transaction cost survival | **FAIL** 0.177 (24 trades) | **FAIL** 0.457 (24 trades) | ≥ 0.5 |
| Walk-forward (4 splits) | PASS 0.75 | PASS 1.0 | ≥ 0.75 |
| Parameter sensitivity | PASS 0.479 | **FAIL** 0.522 (borderline) | ≤ 0.5 |

Total return over 11.7 years: IWM +7.2%, SPY +12.6% — a real but small
positive edge, consistent with the source's own modest per-trade stats
(1.34% avg gain), but the once-a-year trade frequency (24 trades = 12
years x 2 legs) produces too low a Sharpe to clear the 1.0 threshold
full-sample, and the tiny trade count means each 10bps round-trip cost
has an outsized proportional drag on net Sharpe.

## Decision (Step 8): REJECT

2 of 5 validators fail on IWM (Sharpe, transaction costs), 3 of 5 fail on
SPY (Sharpe, transaction costs, parameter sensitivity borderline) — reject
per Step 8's all-must-pass criterion on both symbols. This is a real,
positive, low-frequency seasonal effect (matches the source's own
disclosed direction and rough magnitude) but the annual trade frequency
is fundamentally too sparse to produce a full-sample Sharpe above 1.0 or
survive costs comfortably — a structural limitation of once-a-year
calendar strategies rather than a flawed hypothesis. Not flagged as a
near-miss worth revisiting (the low trade frequency is inherent to the
strategy's calendar structure and cannot be tuned away without
abandoning the pattern's defining feature).

Strategy/report/grid files are kept in the repo as a record of a rejected
attempt (not a live strategy).
