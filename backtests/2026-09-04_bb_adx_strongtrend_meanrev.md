# 2026-09-04 Bollinger Band + ADX Strong-Trend Mean Reversion — Backtest Report

**Hypothesis** (id `2026-09-04-162`): A close falling below the lower
Bollinger Band (20,2std) while ADX(14) is ABOVE a strength threshold (25)
marks a higher-quality mean-reversion long entry than an ungated BB
lower-touch. Per StockSharp's worked "Bollinger Adx Strategy" example
(Entry: Close < LowerBand && ADX > AdxThreshold; Exit: Bollinger mean
reversion to middle band; reports ~46% avg annual backtested return on
stocks, unverified/likely intraday timeframe in source).

**Source**: https://doc.stocksharp.com/api-examples/0153_Bollinger_ADX.html

**Strategy**: `strategies/2026-09-04_bb_adx_strongtrend_meanrev.py`

## Grid test (adx_threshold∈{20,25,30}, bb_std∈{1.5,2.0,2.5}, max_hold_days∈{10,15}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 216, passed_cells: 3, **pass_fraction: 1.4%**
- by_asset_class: equity 3/108; crypto 0/108
- by_vol_regime: low 0/72, mid 3/72, high 0/72
- best_cell: SPY, adx_threshold=20/bb_std=2.0/max_hold_days=10, mid-vol only, Sharpe 1.60
- worst_cell: QQQ adx_threshold=25/bb_std=2.5/max_hold_days=15, mid-vol, Sharpe -0.90

## Single-config validation (adx_threshold=20, bb_std=2.0, max_hold_days=10) — full sample 2019-2026

| Symbol | Sharpe | Passed (>=1.0) | MDD | Passed (<=0.25) | ~Trades |
|---|---|---|---|---|---|
| QQQ | 0.317 | NO | 0.120 | YES | 185 |
| SPY | 0.414 | NO | 0.200 | YES | 176 |

Full-sample Sharpe fails decisively on both equity symbols. Grid pass_fraction
1.4%, only 3/216 cells pass, all mid-vol-regime-only on equity; crypto 0/108.
Gating the classic BB-lower-touch mean-reversion entry with an ADX
strong-trend filter does not rescue the edge -- if anything a strong ADX
trend at the moment of a lower-band touch more often signals a genuine
breakdown continuing (trend riding through the band) rather than a
mean-reversion bounce, the opposite of the source's claimed mechanism.
Under `suggested_workload=max`, walk-forward/param-sensitivity/tx-cost
validators were skipped since the primary Sharpe gate failed decisively.

## Decision: REJECTED

Economically, gating mean-reversion entries with a STRONG-trend filter is
arguably backwards: this repo's own accumulated evidence (2026-09-03-023
required LOW volatility + FLAT MA slope for BB mean-reversion, and that
also failed) suggests BB lower-band touches revert best in calm/ranging
conditions, not during confirmed strong trends where they're more likely
part of an ongoing breakdown. Distinct failure mode from prior ADX-gated
strategies (2026-09-03-017 pure DMI/ADX crossover, 2026-09-04-087
ADX-gated Renko) -- all ADX-as-filter attempts in this repo have failed so
far regardless of which base signal it gates.
