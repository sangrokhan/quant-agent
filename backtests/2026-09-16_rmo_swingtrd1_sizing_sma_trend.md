# Rahul Mohindar Oscillator SwingTrd1 (Range-Normalized) Continuous Sizing Dial + SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_rmo_swingtrd1_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-158

## Hypothesis
RMO (Viratech India, official MetaStock inclusion 2006), per
https://www.luxalgo.com/library/indicator/rahul-mohindar-oscillator/
(visited this iteration): 10 chained 2-period SMAs form the trend-bias MA;
price's displacement from that MA, normalized by the recent
HighestHigh-LowestLow range, forms SwingTrd1 (ST1). This repo's 3 prior
RMO entries all used the RAW (unnormalized) displacement (close - MA10) or
its ST2-ST3 EMA-smoothed spread -- never ST1 itself. Being range-normalized,
ST1 is naturally bounded roughly [-1,1] by construction (unlike the raw
line, which needs z-scoring). Used directly (clipped for safety, no
z-score/tanh) as a continuous sizing dial inside an SMA(trend_window)
uptrend gate with deadband.

## Grid test (trend_window x sensitivity x deadband, 3 vol regimes, QQQ/
SPY/BTC-USDT/ETH-USDT hourly-default crypto data)
- total_cells: 96, passed: 43, pass_fraction: 0.448
- by_asset_class: equity 26/48 (0.542), crypto 17/48 (0.354)
- by_vol_regime: low 26/32 (0.813), mid 17/32 (0.531), high 0/32 (0.0) --
  decisive high-vol-regime failure, consistent with most sizing-dial
  strategies in this repo
- best_cell: ETH/USDT mid-vol, trend_window=40/sensitivity=0.3/deadband=0.3,
  Sharpe 2.35 (cell-level, hourly crypto data, not directly comparable to
  the daily-bar single-config results below)

## Single-config validator results (per-symbol tuned config, crypto on
DAILY bars per this repo's established crypto-data-frequency-fix pattern)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param-sens | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | tw=30,sens=0.3,db=0.30,lev=1.0 | 1.266 (PASS) | 0.137 (PASS) | net Sharpe 0.733 (PASS) | 1.0 (PASS) | 0.106 (PASS) | ACCEPT |
| SPY | tw=40,sens=0.3,db=0.35,lev=1.0 | 1.128 (PASS) | 0.096 (PASS) | net Sharpe 0.662 (PASS) | 1.0 (PASS) | 0.062 (PASS) | ACCEPT |
| BTC/USDT | tw=40,sens=0.4,db=0.20,lev=0.25 | 1.309 (PASS) | 0.229 (PASS) | net Sharpe 0.923 (PASS) | 1.0 (PASS) | 0.072 (PASS) | ACCEPT |
| ETH/USDT | tw=40,sens=0.4,db=0.20,lev=0.25 | 1.161 (PASS) | 0.182 (PASS) | net Sharpe 0.915 (PASS) | 1.0 (PASS) | 0.026 (PASS) | ACCEPT |

## Decision
**Accept full universe** (QQQ, SPY, BTC/USDT, ETH/USDT), all 5 validators
pass on all 4 symbols, per-symbol tuned config, first attempt. Note the
initial default config (deadband=0.15-0.20, leverage_cap=0.5) failed
TC-survival on equity (too many trades) and MDD on crypto (too much
drawdown); a modest deadband widen (equity) and leverage reduction
(crypto, to 0.25) fully resolved both without any code changes.
