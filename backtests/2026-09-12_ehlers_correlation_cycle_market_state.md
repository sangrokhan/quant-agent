# Ehlers Correlation Cycle / Market State — REJECTED (near-miss)

**Strategy file:** `strategies/2026-09-12_ehlers_correlation_cycle_market_state.py`
**Source:** https://www.mesasoftware.com/papers/CORRELATION%20AS%20A%20CYCLE%20INDICATOR.pdf
(John F. Ehlers, original MESA Software paper, full EasyLanguage code)

## Hypothesis

Pearson-correlate the last `period` closes against a Cosine wave (Real
component) and a negative Sine wave (Imag component), compute the phasor
angle = 90 + arctan(Real/Imag) (quadrant-corrected, angle regression
prohibited), then derive a market-state variable per the source's own exact
rule: cycle mode (state=0, trade long when angle<0) vs trend-up
(state=+1, long) vs trend-down (state=-1, flat) based on whether the
angle's bar-to-bar change is below a 9-degree "flatline" threshold. First
Correlation-Cycle/Phasor/Market-State strategy in this repo, architecturally
distinct from all other Ehlers-family entries (Instantaneous Trendline,
Cyber Cycle, Even Better Sinewave, Voss Predictive Filter,
Deviation-Scaled MA/Oscillator, Trendflex, Roofing Filter, MESA Adaptive
MA/Sine Wave/Stochastic).

## Grid test summary (Step 6)

- Grid: `period` in [14, 20, 30]; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT
  (crypto); vol_regime_splits=3. 36 total cells.
- **pass_fraction: 0.222 (8/36)**
- by_asset_class: equity 8/18 passed; **crypto 0/18 (decisive fail)**
- by_vol_regime: low 6/12, mid 2/12, **high 0/12 (decisive fail)** — edge
  concentrated in calmer regimes, breaks down in high-vol
- best_cell: period=20, QQQ, low-vol regime, Sharpe 2.33

## Single-config validation (Step 7) — period=20, full sample 2019-2026

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.969 ❌ (near-miss) | 0.926 ❌ (near-miss) | ≥ 1.0 |
| Max drawdown | 0.234 ✅ | 0.173 ✅ | ≤ 0.25 |
| TC survival (10bps/trade, 246/258 trades) | 0.652 ✅ | 0.494 ❌ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice) | 0.75 ✅ (3/4) | 1.00 ✅ (4/4) | ≥ 0.75 |
| Parameter sensitivity (period 14/20/30) | 0.370 ✅ | 0.656 ❌ | ≤ 0.5 relative std |

## Decision: REJECTED (near-miss both symbols)

Full-sample Sharpe misses the 1.0 threshold on both QQQ (0.969) and SPY
(0.926) — both close but decisive per this repo's validator contract. SPY
additionally fails TC-survival and parameter sensitivity. High-vol regime
decisively fails on the grid (0/12), and crypto is decisively rejected
(0/18). The high trade frequency (246-258 trades over ~7 years, roughly
weekly turnover) drags on transaction costs, consistent with the "cycle
mode fails during trends" caveat the source paper itself flags — frequent
whipsaw around the 9-degree flatline threshold during choppy/high-vol
periods likely explains both the elevated trade count and the high-vol
regime failure. A future iteration could try widening the flatline
threshold or adding a minimum-hold-period filter to reduce whipsaw, but
this iteration logs the direct source-faithful implementation as rejected.
