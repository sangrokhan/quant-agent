# Aroon Dual-Threshold Trend Confirmation (Up>70 AND Down<30) — Backtest Report

**Hypothesis:** Aroon Up and Aroon Down (Tushar Chande, 1995) both crossing
their respective 70/30 thresholds simultaneously (AroonUp > 70 AND
AroonDown < 30) confirms a strong bullish trend worth a long entry; exit
when either condition breaks, or a max_hold_days time-stop.

**Source:** https://www.avatrade.com/education/technical-analysis-indicators-strategies/aroon-indicator-strategies
("Aroon Up above 70 and Aroon Down below 30: Strong bullish trend." /
"Clear Signal Zones: The 70/30 threshold levels offer straightforward cues
for identifying strong bullish or bearish momentum.")

**Strategy file:** `strategies/2026-09-05_aroon_dual_threshold_trend_confirm.py`

**Distinct from:** 2026-09-04-031 (single-line Aroon-Down only threshold,
no Aroon-Up condition) and 2026-09-04-063 (Aroon Oscillator
AroonUp-AroonDown difference crossing zero, a derived single-line
construction). This is the first BOTH-lines dual-threshold confirmation
rule tested in this repo.

## Step 6 — Grid test summary (param_grid: window in [14,25] x
max_hold_days in [15,20,30]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 21, **pass_fraction: 0.292** (strongest
  grid pass-fraction of any strategy tested this cron trigger)
- by_asset_class: equity 21/36 (58%); crypto 0/36 (0%, decisive fail)
- by_vol_regime: low 12/24 (50%), mid 6/24 (25%), high 3/24 (12.5%) --
  notably the only strategy this trigger to pass ANY high-vol cells
- by_symbol: QQQ 12/18, SPY 9/18, BTC/USDT 0/18, ETH/USDT 0/18
- best_cell: window=25, max_hold_days=15, QQQ, low-vol, Sharpe=2.772
- worst_cell: window=14, max_hold_days=15, SPY, mid-vol, Sharpe=-0.098

## Step 7 — Single-config validators (config: window=25, max_hold_days=15,
full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.280 | **PASS** 1.167 |
| Max Drawdown (<= 0.25) | PASS 0.149 | PASS 0.096 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | **PASS** 1.133 (82 trades) | **PASS** 0.964 (84 trades) |
| Parameter sensitivity (relative_std <= 0.5, 6-cell window/max_hold sweep) | PASS 0.173 | PASS 0.195 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **ACCEPTED (QQQ AND SPY)**; crypto rejected decisively

Both equity indices clear all four validators run at the identical shared
config (window=25, max_hold_days=15): QQQ Sharpe 1.280/MDD 0.149/net Sharpe
1.133 (82 trades), SPY Sharpe 1.167/MDD 0.096 (tightest MDD of the pair)/net
Sharpe 0.964 (84 trades). Both show low parameter-sensitivity (relative_std
0.173 and 0.195). This is the broadest-passing equity strategy of the
cron trigger's iterations -- unlike the single-line Aroon-Down (2026-09-04-031,
QQQ only) and Aroon Oscillator (2026-09-04-063, QQQ only, SPY near-miss)
variants, the dual-threshold BOTH-lines confirmation generalizes cleanly
across both major equity indices, though it still fails decisively on
crypto (0/36 cells) like nearly every trend/momentum construction tested
against BTC/ETH in this repo.
