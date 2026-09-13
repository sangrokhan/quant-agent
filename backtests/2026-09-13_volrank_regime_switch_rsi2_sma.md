# Backtest report: 2026-09-13 volrank regime switch (RSI2 / SMA50-200)

## Hypothesis
Per "Trading using Garch Volatility Forecast" (R-bloggers 2012, citing
Quantum Financier's "Regime Switching System Using Volatility Forecast"):
https://www.r-bloggers.com/2012/01/trading-using-garch-volatility-forecast/

Classify regime via a smoothed double percentile-rank of realized
volatility: `vol_rank = percent_rank(SMA(percent_rank(hist_vol(21), 252), 21), 250)`.
When `vol_rank > threshold` (high-vol/choppy regime) trade RSI(2) mean
reversion (long when RSI(2) < rsi_threshold); when `vol_rank <= threshold`
(calmer/trending regime) trade SMA(50) vs SMA(200) crossover trend-following
(long when SMA50 > SMA200). Long-only per SAFETY.md.

Strategy file: `strategies/2026-09-13_volrank_regime_switch_rsi2_sma.py`

## Step 6 — Grid test summary

Grid: `vol_rank_threshold in [0.4, 0.5, 0.6] x rsi_threshold in [40, 50, 60]`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`,
window 2019-01-01 to 2026-09-01.

- total_cells=108, passed_cells=21, pass_fraction=0.194
- by_asset_class: equity 21/54, crypto 0/54
- by_vol_regime: low 18/36, mid 1/36, high 2/36
- best_cell: QQQ vol_rank_threshold=0.5, rsi_threshold=40, low-vol slice, Sharpe=1.70
- worst_cell: SPY vol_rank_threshold=0.6, rsi_threshold=40, mid-vol slice, Sharpe=-0.16
- Passes are concentrated almost entirely in the low-realized-vol tercile;
  the strategy essentially only "works" when the market is already calm --
  the opposite of a genuine regime-switch edge (which should show up
  precisely when regimes actually change/are turbulent).
- Crypto: 0/54 passed across the board (BTC/USDT, ETH/USDT) -- construction
  does not transfer to crypto at all.
- Full-equity per-param-combo mean Sharpe (across QQQ+SPY, all vol slices):
  {0.4,40}:1.138, {0.4,50}:0.911, {0.4,60}:1.004, {0.5,40}:0.899,
  {0.5,50}:0.786, {0.5,60}:0.930, {0.6,40}:0.803, {0.6,50}:0.733, {0.6,60}:0.855.

## Step 7 — Full-sample single-config validation (best cell config: vol_rank_threshold=0.5, rsi_threshold=40)

| Symbol | Sharpe | MDD | Net Sharpe (5bps/trade) | Trades |
|---|---|---|---|---|
| QQQ | 0.931 (FAIL, thr 1.0) | 0.170 (PASS, thr 0.25) | 0.749 (PASS, thr 0.5) | 241 |
| SPY | 0.622 (FAIL, thr 1.0) | 0.162 (PASS, thr 0.25) | 0.425 (FAIL, thr 0.5) | 217 |

Parameter sensitivity: full-equity mean-Sharpe across the 9-cell param grid
ranges 0.733-1.138 (relative std ~14%, well under the 0.5 threshold) --
i.e. the strategy is *stable* across small parameter changes, but stably
mediocre rather than stably good. It never clears the primary Sharpe
threshold on the full sample for either symbol.

Walk-forward: skipped (pre-existing tooling gap, `vbt.utils.splitting.RangeSplitter`
unavailable in installed vectorbt version -- consistent with prior entries
since 2026-09-13-007).

## Step 8 — Decision: REJECTED

Full-sample Sharpe fails the 1.0 threshold on both QQQ (0.931) and SPY
(0.622); SPY also fails transaction-cost survival. The grid's apparent
"passes" are an artifact of slicing into the low-vol tercile only -- the
double-percent-rank volatility regime gate does not produce a genuine,
full-sample-robust edge over either sub-strategy alone with this repo's
long-only adaptation. Strategy file kept in `strategies/` as a rejected
record (not live).
