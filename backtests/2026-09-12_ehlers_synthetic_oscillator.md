# Backtest Report: Ehlers Synthetic Oscillator Zero-Line Crossover (TASC 2026.04)

**Strategy file:** `strategies/2026-09-12_ehlers_synthetic_oscillator.py`
**Source:** John F. Ehlers, "Avoiding Whipsaw Trades", TASC April 2026.
TradingView implementation: https://www.tradingview.com/script/we9AMcvE-TASC-2026-04-A-Synthetic-Oscillator/

## Hypothesis

A nonlinear phase-based oscillator, built from an instantaneous dominant-cycle
estimate (Hann-smoothed price -> bandpass I/Q components -> cumulative phase
-> sin(phase)), can time trend turns with less whipsaw than fixed-lag linear
filters. Long-only adaptation: enter on oscillator crossing from negative to
positive, exit on the reverse cross.

## Single-config validator results

### QQQ (hann_len=12, upper_bound=48) — best QQQ grid cell

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.218 | >= 1.0 |
| Max drawdown | **FAIL** | 0.263 | <= 0.25 |
| Transaction cost survival (10bps/trade, 82 trades) | PASS | net Sharpe 1.123 | >= 0.5 |
| Walk-forward (4 manual contiguous splits — vectorbt splitting API broken, see prior reports) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity (9-cell hann_len x upper_bound grid) | PASS | rel. std 0.392 | <= 0.5 |

### SPY (hann_len=12, upper_bound=60) — best SPY grid cell

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.155 | >= 1.0 |
| Max drawdown | PASS | 0.203 | <= 0.25 |
| Transaction cost survival (10bps/trade, 80 trades) | PASS | net Sharpe 1.023 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity | **FAIL** | rel. std 0.581 | <= 0.5 |

Neither asset's best config passes ALL validators — QQQ fails max drawdown
narrowly, SPY fails parameter sensitivity narrowly.

## Grid test summary (hann_len x {8,12,16}, upper_bound x {36,48,60}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3)

- **Total cells:** 108, **passed:** 25, **pass_fraction: 0.231**
- **By asset class:** equity 25/54 (0.463), crypto 0/54 (0.0)
- **By vol regime:** low 18/36 (0.5), mid 4/36 (0.111), high 3/36 (0.083)
- **Best cell:** QQQ low-vol, hann_len=12/upper_bound=36, Sharpe 3.10
- **Worst cell:** SPY mid-vol, hann_len=16/upper_bound=36, Sharpe -1.15

The strategy only works in low-vol equity regimes; crypto is a decisive
fail across the board (0/54), and mid/high-vol equity regimes are weak too.

## Decision: REJECT

Both best per-symbol configs each fail exactly one standard validator
(QQQ: max drawdown 0.263 > 0.25 threshold; SPY: parameter sensitivity
relative std 0.581 > 0.5 threshold), and the edge is concentrated almost
entirely in low-vol equity regimes with a decisive crypto failure. This is
a near-miss, not a clean accept — logged as rejected per Step 8.

Strategy code and this report are kept as a record of a rejected attempt
(not a live strategy).
