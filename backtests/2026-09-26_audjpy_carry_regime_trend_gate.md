# Backtest Report: Equity/Crypto Trend Gated by AUD/JPY Carry-Trade Regime

**Hypothesis source:** LITFX, "Carry Trade Strategy: Complete Practical Guide"
https://litfx.app/learn/carry-trade-strategy (read via browser_exec).

**Hypothesis:** AUD/JPY carry-pair trend status (source's own "50-day SMA above
200-day SMA" bullish-alignment rule) as a risk-on/risk-off gate on QQQ/SPY/BTC/ETH's
own 100/150-day SMA trend-following signal, since FX carry unwinds are a well-known
leading/coincident indicator of broader risk-asset stress.

## Grid Test (Step 6)

Params: `trend_window` in {50,100,150}, `carry_ma_window` in {150,200} (carry_fast_window
fixed 50). Symbols: equity {QQQ,SPY}, crypto {BTC/USDT,ETH/USDT}. vol_regime_splits=3.
2018-01-01 to 2026-09-01.

- pass_fraction: 0.208 (15/72)
- by_asset_class: equity 12/36; crypto 3/36
- by_vol_regime: low 15/24; mid 0/24; high 0/24 -- entirely a low-vol-regime artifact
- best_cell: trend_window=100/150, SPY, low-vol, Sharpe 1.94

## Full-Sample Validators (Step 7), config trend_window=150, carry_ma_window=150

| Symbol | Sharpe (>=1.0) | MDD (<=0.25) | TC survival (net Sharpe>=0.5) | Param sensitivity |
|---|---|---|---|---|
| QQQ | 0.729 FAIL | 0.160 PASS | 0.679 PASS | 0.257 PASS |
| SPY | 0.782 FAIL | 0.209 PASS | 0.699 PASS | 0.204 PASS |
| BTC/USDT | 0.962 FAIL (narrow) | 0.378 FAIL | 0.939 PASS | 0.064 PASS |
| ETH/USDT | 0.786 FAIL | 0.747 FAIL | 0.772 PASS | 0.099 PASS |

Full JSON: `validate_result_audjpy_carry_regime.json`, grid JSON:
`grid_result_audjpy_carry_regime.json`.

## Decision: REJECT

Sharpe fails decisively on all 4 symbols despite attractive isolated low-vol-regime
grid cells (best_cell Sharpe 1.94). Crypto additionally fails max drawdown badly
(0.38/0.75, far over the 0.25 cap) since the AUD/JPY gate does not meaningfully
restrict crypto's own violent drawdowns. The mid/high-vol regime pass_fraction of 0
(0/48 cells) confirms this gate adds essentially no value once regime-conditioning
is removed -- it is simply riding the same underlying trend-following signal with an
extra filter that happens to correlate with low-vol periods, not a genuine distinct
edge. Parameter sensitivity and TC-survival both pass, so this is a clean full-sample
Sharpe rejection rather than an overfitting or cost-fragility issue. Strategy file and
this report kept as a record of a rejected attempt -- first FX-carry-regime gate
tested in this repo, now closing off that specific angle.
