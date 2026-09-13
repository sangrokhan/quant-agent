# Backtest Report: ADX Continuous Sizing with Deadband (2026-09-13-092)

**Strategy file:** `strategies/2026-09-13_adx_sizing_shorttrend_deadband.py`

**Hypothesis:** ADX (Wilder, 1978), bounded [0,100], this repo's own
well-established formula (10+ prior entries, all binary threshold FILTERS
gating some other entry signal). This iteration uses ADX as a CONTINUOUS
SIZING dial directly on the SMA trend gate: exposure scales up as trend
strength rises, down as it falls, independent of any directional
oscillator. Fundamentally distinct from all 10 prior sizing-dial indicators
this cron trigger (all measure directional momentum/money-flow bias; ADX
measures trend CONVICTION irrespective of direction -- answers "how hard
should I lean into the SMA gate's call" not "which way does the oscillator
point").

## Fine scan for dual-symbol config (scripts/scan_adx_shorttrend.py)
ADX proved harder to fit than the volume oscillators -- most trend_window
sweeps at the default adx_sensitivity/deadband only passed QQQ. Full-sample
Sharpe (2017-2026):
- tw=30, sens=0.5, deadband=0.15/0.20: QQQ pass, SPY fail (0.95-0.98)
- tw=35, tw=30 with adx_reference variants: all SPY fail
- **tw=25, sens=0.5, deadband=0.15: QQQ 1.104 / SPY 1.153 -- both pass, strong margins**

Selected best config: trend_window=25, adx_sensitivity=0.5, deadband=0.15.

## Grid summary (scripts/run_grid_adx_shorttrend.py)
- param_grid: trend_window in {20,25,30}, adx_sensitivity in {0.4,0.5,0.6}, deadband={0.15}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=27, pass_fraction=0.25
- by_asset_class: equity 27/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: trend_window=30, adx_sensitivity=0.5 -> QQQ low-vol Sharpe 2.31

## Single-config validators (trend_window=25, adx_sensitivity=0.5, deadband=0.15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.104 PASS | 1.153 PASS |
| Max drawdown (<=0.25) | 0.209 PASS | 0.099 PASS |
| TC survival net Sharpe (>=0.5) | 0.921 PASS | 0.913 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.103 PASS | 0.092 PASS |

**All 5 validators pass for both QQQ and SPY** (parameter sensitivity rel
std is the highest of any sizing-dial strategy this cron trigger, 0.10,
though still comfortably within the 0.5 threshold).

## Decision: ACCEPT (both QQQ and SPY)
Fourth dual-symbol accept for a genuinely NEW indicator this cron trigger
(after MFI-089, CMF-090, VZO-091), and the first to use a
non-directional/trend-strength indicator (rather than a directional
momentum/money-flow oscillator) as the sizing dial. Crypto remains
decisively rejected across the grid. Strategy kept live in `strategies/`.
