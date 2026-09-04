# Backtest Report: Chande Forecast Oscillator (CFO) zero-line + ADX filter (2026-09-05)

**Hypothesis:** Chande Forecast Oscillator (Tushar Chande): CFO =
100*(Close - OLS-regression-value)/Close, a percentage measure of price's
deviation from its own recent linear trend. Per arrowalgo.com's CFO guide,
the recommended mechanical strategy is a zero-line crossover (bullish when
CFO crosses above 0) combined with an ADX(14)>25 trend-strength filter to
suppress false signals in ranging markets. Exit when CFO crosses back
below zero, ADX drops below the threshold, or a max-hold time-stop.

**Source:** https://arrowalgo.com/chande-forecast-oscillator-complete-guide-algorithmic-trading/
(full CFO formula and ADX-filtered crossover rule disclosed free).

**Novelty:** first CFO strategy in this repo — distinct from the
already-tested linear-regression-slope mean-reversion strategy
(2026-09-04-058, trades the sign of the slope) and linear-regression-channel
breakout strategy (2026-09-04-141, trades residual-band breaks), since CFO
instead measures the pct deviation of price from the regression line's own
current value.

## Grid test (validation/grid_test.py)

- param_grid: `cfo_window` in {14, 20}, `adx_threshold` in {20, 25},
  `max_hold_days` in {15, 25}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3
- total_cells = 96, passed_cells = 18, **pass_fraction = 18.75%**
- by_asset_class: equity 18/48, crypto 0/48
- by_vol_regime: low 14/32, mid 4/32, high 0/32
- best_cell: QQQ, cfo_window=14, adx_threshold=25, max_hold_days=15,
  low-vol regime, Sharpe 2.01
- Best config (cfo_window=14, adx_threshold=20, max_hold_days=15/25)
  per-symbol: QQQ 2/3 passed (avg Sharpe 0.77), SPY 1/3 passed (avg Sharpe
  0.47), BTC/USDT 0/3 (avg Sharpe -0.01), ETH/USDT 0/3 (avg Sharpe 0.07).
  Note the vol-regime-tercile averages are all well below the 1.0 Sharpe
  threshold even for the "best" config — the grid pass count is driven by
  isolated low-vol-tercile passes, not broad strength.

## Single-config validators (config: cfo_window=14, adx_threshold=20,
max_hold_days=15, full 2019-01-01..2026-09-01 sample)

| Symbol | Sharpe | MDD | TC-survival (10bps, N trades) | Passed all? |
|---|---|---|---|---|
| QQQ | 0.146 (FAIL <1.0, decisive) | 0.381 (FAIL >0.25) | -0.022 net Sharpe, 157 trades (FAIL) | NO |
| SPY | -0.042 (FAIL, decisive) | 0.347 (FAIL >0.25) | -0.230 net Sharpe, 166 trades (FAIL) | NO |

Full-sample performance is far worse than the vol-regime-tercile averages
suggested — the strategy trades very frequently (157-166 entries over the
sample) and decisively fails Sharpe, MDD, and transaction-cost survival on
both equity symbols.

## Decision: REJECTED (decisive, both equity symbols and crypto)

The grid's isolated low-vol-tercile Sharpe passes did not survive
confirmation on the full out-of-sample period — full-sample Sharpe is
near zero or negative on both QQQ and SPY, MDD breaches the 25% threshold
on both, and net-of-cost Sharpe is negative. High trade frequency (roughly
one crossover every 2-3 weeks over 7.5 years) combined with per-trade
transaction costs erodes any edge the vol-regime-tercile splits appeared to
show. Crypto fails decisively across the whole grid as well (0/48).
