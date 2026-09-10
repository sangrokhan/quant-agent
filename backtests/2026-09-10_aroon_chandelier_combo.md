# Aroon Oscillator Entry + Chandelier Exit Trailing Stop Combo (QQQ accepted, SPY near-miss)

**Hypothesis source:** Google AI-overview synthesis (StockCharts.com/LuxAlgo/
FxDailyReport et al), via browser_exec Google SERP fallback of "Aroon
Oscillator Chandelier exit combo strategy rules trend following".

**Hypothesis:** Aroon Oscillator (AroonUp-AroonDown, 25-period default) acts
as the entry engine -- it filters out sideways noise, firing only on
directional breakouts (crosses above 0, ideally past +50). The Chandelier
Exit (Highest High over N bars minus atr_mult x ATR) both confirms the
breakout (close must close firmly above the Chandelier line, which flips
green) and supplies the trailing stop for the whole trade. Long entry: Aroon
Oscillator > entry threshold (50) AND close > Chandelier Exit line. Exit:
close crosses back below the (ratcheting) Chandelier Exit line, or a
max_hold_days time-stop.

Distinct from prior Chandelier-family entries (2026-09-04-035: Chandelier
regime + StochRSI dip TIMING, not an Aroon breakout entry; 2026-09-09-064/065:
standalone Chandelier trend-flip, no Aroon; 2026-09-09-090/091: Chandelier +
Supertrend dual-confirm, different second indicator) and prior Aroon-family
entries (none paired with Chandelier Exit; 2026-09-06-098 paired Aroon with
ADX instead).

Strategy file: `strategies/2026-09-10_aroon_chandelier_combo.py`

## Step 6 grid summary (144 cells: aroon_window x chandelier_atr_mult x
max_hold_days x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol terciles)

- `pass_fraction`: 35/144 = 0.243 (best result of this cron trigger's 3
  strategies tested so far)
- `by_asset_class`: equity 35/72 passed; **crypto 0/72 passed** (decisive
  fail)
- `by_vol_regime`: low 24/48; mid 10/48; high 1/48 -- concentrated in
  low-vol regimes but with meaningful mid-vol representation too (broader
  than most near-misses in this repo)
- best cell (QQQ): aroon_window=25, chandelier_atr_mult=3.0,
  max_hold_days=20, low-vol, Sharpe 2.624
- best cell (SPY): aroon_window=25, chandelier_atr_mult=3.5,
  max_hold_days=20, low-vol, Sharpe 2.652

## Step 7 single-config validation (aroon_window=25, chandelier_atr_mult=3.0,
max_hold_days=20 -- grid's best QQQ cell, full 2019-01-01..2026-09-01 sample)

### QQQ

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **pass** | 1.332 | 1.0 |
| Max drawdown | pass | 0.126 | 0.25 |
| Transaction cost survival (10bps/trade, 133 trades) | pass | 1.075 | 0.5 |
| Walk-forward (4 manual splits) | pass | 1.00 (4/4 splits positive) | 0.75 |
| Parameter sensitivity (12-cell full-sample sweep) | pass | 0.155 relative std | 0.5 |

### SPY

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL (near-miss)** | 0.844 | 1.0 |
| Max drawdown | pass | 0.127 | 0.25 |
| Transaction cost survival (10bps/trade, 142 trades) | pass | 0.550 | 0.5 |
| Walk-forward (4 manual splits) | pass | 1.00 (4/4 splits positive) | 0.75 |
| Parameter sensitivity (12-cell full-sample sweep) | pass | 0.144 relative std | 0.5 |

## Outcome: **ACCEPTED (QQQ only)**; SPY near-miss (all other validators
comfortably pass, only Sharpe misses); crypto rejected decisively (0/72
grid cells). This is a genuinely robust QQQ trend-following strategy: strong
Sharpe (1.33), tight walk-forward consistency, and low parameter
sensitivity (0.155 relative std -- the least parameter-sensitive
accepted/near-accepted strategy tested this trigger).
