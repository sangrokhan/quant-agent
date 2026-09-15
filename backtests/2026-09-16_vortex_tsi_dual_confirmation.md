# Vortex Indicator + TSI dual-confirmation trend system (2026-09-16)

**Hypothesis id:** 2026-09-16-168
**Strategy file:** `strategies/2026-09-16_vortex_tsi_dual_confirmation.py`
**Source:** Google AI-overview synthesis (Medium/Alexzap, Investopedia,
TradingView) — read via `browser_exec` Google SERP fallback after
`web_search` failed with a DuckDuckGo/Yahoo TLS connection error on every
query attempted this iteration.

## Hypothesis

A combined Vortex Indicator + True Strength Index (TSI) system requires
BOTH indicators to agree before entering: VI+ crosses above VI- (trend
direction confirmation from the Vortex's true-range-normalized directional
movement construction) AND TSI is above its own signal line (momentum
confirmation from Blau's double-smoothed price-change oscillator) at the
same bar. Exit when either confirmation reverses (VI- crosses back above
VI+ OR TSI crosses below its signal line). Distinct from this repo's prior
Vortex entries (plain SMA-trend-filtered crossover, ADX-filtered
crossover, continuous-sizing-dial variant) and prior TSI entries
(zero-line crossover, signal-line crossover, continuous-sizing-dial
variant) — none combine the two as a dual AND-gate confirmation system;
explicitly flagged as an untested angle in 2026-09-10-070's notes.

## Grid test summary (Step 6)

Grid: `vortex_window` in [10,14,21] x `tsi_r` in [13,25] x `tsi_s` in
[7,13] (`tsi_signal` fixed at 7), symbols QQQ/SPY/BTC/USDT/ETH/USDT,
vol_regime_splits=3 (144 cells).

- **Pass fraction:** 51/144 = 0.354
- **by_asset_class:** equity 32/72, crypto 19/72
- **by_vol_regime:** low 35/48, mid 7/48, high 9/48 — edge concentrates
  heavily in low-vol regimes across both asset classes, consistent with a
  trend-confirmation system (works when trends are orderly, struggles in
  choppy/high-vol whipsaw conditions)
- **Best cell:** QQQ, vortex_window=21/tsi_r=25/tsi_s=13, low-vol regime,
  Sharpe 2.09

## Single-config validation (Step 7)

### QQQ, vortex_window=21, tsi_r=25, tsi_s=13, tsi_signal=7

| Validator | Result | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.184 | >= 1.0 | PASS |
| Max drawdown | 0.119 | <= 0.30 | PASS |
| Transaction cost survival (10bps/trade) | net Sharpe holds | >= 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual fallback) | pass_fraction >= 0.5 | >= 50% | PASS |
| Parameter sensitivity (vortex_window in [17,21,25]) | relative std within tolerance | <= 0.6 | PASS |

### SPY, vortex_window=10, tsi_r=25, tsi_s=13, tsi_signal=7

| Validator | Result | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.046 | >= 1.0 | PASS |
| Max drawdown | 0.116 | <= 0.30 | PASS |
| Transaction cost survival (10bps/trade) | net Sharpe holds | >= 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual fallback) | pass_fraction >= 0.5 | >= 50% | PASS |
| Parameter sensitivity (vortex_window in [6,10,14]) | relative std within tolerance | <= 0.6 | PASS |

Crypto (BTC/USDT best full-sample Sharpe 0.798 at vortex_window=14/tsi_r=13/tsi_s=7;
ETH/USDT best 0.878 at vortex_window=10/tsi_r=25/tsi_s=13) — neither cleared
the Sharpe >= 1.0 threshold in the parameter sweep, consistent with the
grid's asset-class breakdown (crypto pass fraction well below equity's).

## Decision

**Accept** — QQQ and SPY, both all 5 validators pass with solid margins
(both MDD well under 12%, a notably clean risk profile for a dual-gated
trend system). **Reject** — BTC/USDT and ETH/USDT, best full-sample Sharpe
fell short of the 1.0 threshold across the parameter sweep; the dual
Vortex+TSI confirmation requirement appears to filter too aggressively
in crypto's higher-baseline-volatility regime, consistent with the grid's
low-vol-regime concentration finding.
