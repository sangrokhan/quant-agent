# Backtest Report: Internal Bar Strength (IBS) Mean Reversion + Trend Filter

**Strategy file:** `strategies/2026-09-04_ibs_meanrev_trend_filter.py`
**Hypothesis ID:** 2026-09-04-089

## Hypothesis

IBS = (Close - Low) / (High - Low). Buy on close when IBS < 0.2 (close near
the day's low, intraday panic/oversold), exit on close when IBS rises above
0.8 (close near the day's high, overbought/reversion complete). Add a
200-SMA proximity filter (only enter if price is not more than 5% above its
200-day SMA, per source's own finding that this improves quality) and a
max_hold_days=10 safety exit. Source: quantifiedstrategies.com published
SPY/QQQ backtests since 1993 showing CAGR outperformance, Sharpe ~1.7 for a
refined IBS-only-exit variant.

Source: https://www.quantifiedstrategies.com/internal-bar-strength-ibs-indicator-strategy/

## Single-config validator results (SPY, ibs_entry=0.2/ibs_exit=0.8/max_hold_days=10/trend_band_pct=0.05)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.400 | 1.0 |
| Max drawdown | ✅ | 0.110 | 0.25 |
| Transaction cost survival (10bps/trade, 101 trades) | ✅ | net Sharpe 1.194 | 0.5 |
| Walk-forward (4 manual date-slices) | ✅ | 4/4 positive (2.44, 0.93, 0.57, 0.54) | 0.75 |
| Parameter sensitivity (ibs_entry in [0.1,0.15,0.2,0.25,0.3]) | ✅ | rel-std 0.085 | 0.5 |

## Step 6 grid summary (ibs_entry ∈ {0.1,0.2}, ibs_exit ∈ {0.7,0.8}, max_hold_days ∈ {5,10}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 96, passed_cells: 16, pass_fraction: 0.167
- by_asset_class: equity 16/48, crypto 0/48
- by_vol_regime: low 0/32, mid 0/32, **high 16/32**
- best_cell: SPY, ibs_entry=0.2/ibs_exit=0.8/max_hold_days=10, high-vol regime, Sharpe 2.62
- worst_cell: QQQ, ibs_entry=0.1/ibs_exit=0.7/max_hold_days=10, mid-vol regime, Sharpe -0.59

**Interpretation:** the grid-cell pass criteria (Sharpe>=1.0 AND MDD<=0.25
computed per-vol-regime-slice) only pass in the high-vol tercile — this
matches the source's own claim that IBS mean-reversion "works best in bear
markets / volatile conditions" (short covering after panic spikes). The
full-sample single-config validator run above (spanning all vol regimes,
2019-2026) still clears Sharpe 1.0 comfortably (1.40) because volatile
periods contribute disproportionately to the edge even when averaged with
calmer stretches. Crypto rejected decisively (0/48 grid cells) — IBS panic-
reversal logic does not transfer to BTC/ETH at daily granularity in this
data.

## Decision

**ACCEPT (SPY only)**, full-sample config: `ibs_entry=0.2, ibs_exit=0.8,
max_hold_days=10, trend_band_pct=0.05`. All 5 standard validators pass
cleanly on SPY. QQQ was tested in the grid too (16/48 equity passes were a
mix of QQQ/SPY high-vol cells) but was not separately validated as a
primary config this iteration — flagged for a future loop to check QQQ full-
sample directly. Crypto and low/mid-vol equity regimes are explicitly out of
scope for this accepted config; edge appears concentrated in higher-vol
conditions, consistent with the source's own stated regime dependency.
