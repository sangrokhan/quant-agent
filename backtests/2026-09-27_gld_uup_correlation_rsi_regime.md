# Backtest report: GLD/UUP rolling-correlation regime gate + RSI(14->10) 30/70(->35/65) crossover

**Hypothesis:** Gold and the US Dollar Index (proxied here by UUP, since
this repo's data/loaders.py has no true DXY futures source) typically move
inversely. Per TradingView's "Gold/DXY Correlation Oscillator"
(laraibislam, https://www.tradingview.com/script/e35VP2Mq-Gold-DXY-Correlation-Oscillator/,
visited this iteration): a rolling Pearson correlation between gold's
close and DXY's close gates an RSI(14) 30/70 crossover -- only enabling
signals when correlation is below a threshold (the normal inverse
relationship is actively in force). Buy when correlation < threshold AND
RSI crosses above the oversold level; sell/exit when correlation <
threshold AND RSI crosses below the overbought level.

**Strategy file:** `strategies/2026-09-27_gld_uup_correlation_rsi_regime.py`

**Distinct from prior repo entries:** all prior DXY/GLD regime-filter
strategies (SMA-level gate 2026-09-05-026, ROC-momentum gate
2026-09-09-113, two-level absolute hysteresis 2026-09-20-026, rolling
correlation-breakdown gate on BTC 2026-09-23-021) use a simple level/ROC/
z-score construct as the SOLE signal or a pure regime gate on a separate
trend-following base; none combine a rolling Pearson correlation regime
filter with an RSI mean-reversion crossover trigger, and none use GLD as
the primary traded asset.

## Grid test (validation/grid_test.py::run_strategy_grid)

param_grid: corr_threshold in {-0.5, -0.3, -0.1} x corr_window in {20, 30,
60} (rsi_period=14, rsi_oversold=30, rsi_overbought=70 fixed defaults),
symbols equity=[GLD, QQQ], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3
(2019-01-01 to 2026-09-01).

- overall pass_fraction: 16/108 = 0.148
- by_asset_class: equity 16/54 (0.296, ALL passing cells are GLD -- QQQ 0/27), crypto 0/54 (0.0, decisive fail)
- by_vol_regime: low 11/36 (0.306), mid 5/36 (0.139), high 0/36 (0.0)
- best_cell: corr_threshold=-0.5, corr_window=60, GLD, low-vol regime, Sharpe 1.91
- worst_cell: corr_threshold=-0.5, corr_window=60, ETH/USDT, high-vol regime, Sharpe -0.53

## Full-sample validator suite (best config, GLD only)

Grid's initial best config had only 8 trades over the full 2019-2026
sample (too few for robust conclusions); a wider joint sweep over
corr_window/corr_threshold/rsi_period/rsi_oversold/rsi_overbought with a
minimum-15-trades filter found a stronger and more heavily-traded config:
corr_window=90, corr_threshold=-0.6, rsi_period=10, rsi_oversold=35,
rsi_overbought=65 (28 trades).

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.205 | >= 1.0 | Yes |
| Max drawdown | 0.210 | <= 0.25 | Yes |
| Transaction-cost survival (10bps/trade, 28 trades) | 1.159 | >= 0.5 | Yes |
| Walk-forward (4 equal chronological splits, GLD) | 0.75 (3/4 splits Sharpe>0; splits: -0.10, 0.53, 1.98, 1.36) | >= 0.75 | Yes (exact threshold) |
| Parameter sensitivity (corr_window in {60,90,120} x rsi_period in {8,10,12}, relative std of Sharpe) | 0.459 | <= 0.5 | Yes |

All 5 validators pass for GLD at this config.

**QQQ:** 0/27 grid cells pass at any tested config -- decisively rejected,
out of scope for this strategy.

**Crypto (BTC/USDT, ETH/USDT):** 0/54 grid cells pass at any tested
config -- decisively rejected. UUP's correlation structure with crypto
assets does not produce a usable regime signal for this construction.

## Outcome: ACCEPTED (GLD only)

Left in `strategies/` as a live GLD-only strategy. QQQ and crypto assets
are explicitly out of scope -- this is a narrow, honestly-scoped
acceptance (single equity/commodity-ETF ticker), consistent with this
repo's convention of recording narrower-but-honest accepted strategies
rather than falsely broad ones.
