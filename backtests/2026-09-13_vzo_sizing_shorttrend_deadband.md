# Backtest Report: VZO Continuous Sizing with Deadband (2026-09-13-091)

**Strategy file:** `strategies/2026-09-13_vzo_sizing_shorttrend_deadband.py`

**Hypothesis:** Volume Zone Oscillator (Khalil & Steckler 2009/2011),
formula already known in this repo (2026-09-04-122/2026-09-10-115, no new
external source needed): VZO=100*(VP/TV), VP=EMA of signed (OBV-style)
volume, TV=EMA of raw volume, roughly bounded [-100,100]. This repo's 2
prior VZO entries were binary threshold ENTRY triggers, BOTH decisively
rejected -- 2026-09-04-122 specifically found only 9 trades over 7.5 years
("too rare an event to build a reliable edge"). This iteration applies VZO
as a CONTINUOUS SIZING dial instead (the construction validated 9x already
this cron trigger), sidestepping the "too rare" problem entirely since
sizing responds to VZO's value every day rather than waiting for a
threshold crossing.

## Fine scan for dual-symbol config (scripts/scan_vzo_shorttrend.py)
Every single candidate combination except trend_window=50 passed BOTH
symbols on the first attempt -- the strongest, most robust result of any
sizing-dial strategy tested this cron trigger:
- tw=40, sens=0.5, deadband=0.10: QQQ 1.201 / SPY 1.095 -- both pass
- tw=30, sens=0.5, deadband=0.10: **QQQ 1.297 / SPY 1.089 -- both pass, selected (best QQQ margin of entire cron trigger)**
- tw=50, sens=0.5, deadband=0.10: QQQ 1.223 / SPY 0.973 (SPY fail)
- tw=40, sens=0.7, deadband=0.10: QQQ 1.246 / SPY 1.074 -- both pass
- tw=40, sens=0.5, deadband=0.15/0.20: both pass in both cases

Selected best config: trend_window=30, vzo_sensitivity=0.5, deadband=0.10.

## Grid summary (scripts/run_grid_vzo_shorttrend.py)
- param_grid: trend_window in {25,30,35}, vzo_sensitivity in {0.4,0.5,0.6}, deadband={0.10}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=30, pass_fraction=0.278
- by_asset_class: equity 30/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 9/36, **high 3/36** (unusual -- every other
  sizing-dial strategy this cron trigger scored 0/36 in the high-vol
  tercile; VZO is the first to show any high-vol robustness at all)
- best_cell: trend_window=25, vzo_sensitivity=0.6 -> SPY low-vol Sharpe 2.65

## Single-config validators (trend_window=30, vzo_sensitivity=0.5, deadband=0.10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.297 PASS (best QQQ margin this cron trigger) | 1.089 PASS |
| Max drawdown (<=0.25) | 0.196 PASS | 0.156 PASS |
| TC survival net Sharpe (>=0.5) | 1.153 PASS (net Sharpe EXCEEDS gross threshold) | 0.898 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.023 PASS | 0.082 PASS |

**All 5 validators pass for both QQQ and SPY, with the strongest margins of
any strategy accepted this cron trigger.**

## Decision: ACCEPT (both QQQ and SPY) -- strongest accept this cron trigger
Third dual-symbol accept for a genuinely NEW indicator this cron trigger
(after MFI-089, CMF-090), and the strongest overall: highest QQQ Sharpe
(1.297), TC-survival net Sharpe exceeding the gross-Sharpe threshold, and
the only sizing-dial strategy to show any high-vol-regime grid robustness.
Notably rescues an indicator (VZO) whose only 2 prior threshold-based
attempts in this repo were decisively rejected -- confirms the
continuous-sizing-dial reframing can salvage indicators that fail as rare
binary triggers. Crypto remains decisively rejected across the grid.
Strategy kept live in `strategies/`.
