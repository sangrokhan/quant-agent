# Coral (T3 Moving Average) slope-flip — backtest report

**Strategy file:** `strategies/2026-09-04_coral_t3_slopeflip.py`
**Hypothesis id:** 2026-09-04-131

## Hypothesis

The "Coral" indicator is a color-coded plot of Tim Tillson's T3 moving
average (sextuple cascaded EMA recombined via a fixed polynomial of one
volume-factor constant b=0.7), smoother/less-laggy than a plain EMA of the
same period. Per
[stonehillforex.com](https://stonehillforex.com/2022/09/coral-as-a-confirmation-indicator/):
"Long: The signal line goes from red, to yellow, to blue. The entry is the
open of the period after yellow"; i.e. color encodes local slope
direction, and the systematic rule is to trade the slope-flip. Tested
here: long entry when T3's slope flips from non-positive to positive
(first "blue" bar after a "yellow" transition), exit on the reverse flip
or a max_hold_days time-stop. Default period=34 (source's default),
b=0.7 (Tillson's standard).

Source: https://stonehillforex.com/2022/09/coral-as-a-confirmation-indicator/
(via browser_exec Google-search fallback after web_search's DDGS backend
returned "No results found").

## Grid summary (Step 6)

`period` in {20,34,50} x `b` in {0.5,0.7} x `max_hold_days` in {10,15},
symbols QQQ/SPY/BTC/USDT/ETH/USDT, vol_regime_splits=3:

- 144 cells total, 26 passed (pass_fraction=0.181)
- by_asset_class: equity 26/72, crypto 0/72
- by_vol_regime: low 21/48, mid 2/48, high 3/48
- best_cell: period=20, b=0.7, max_hold_days=10, QQQ, low-vol, Sharpe=2.29
- worst_cell: period=50, b=0.5, max_hold_days=15, SPY, high-vol, Sharpe=-0.98

## Primary config validators (period=20, b=0.7, max_hold_days=10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.935 **FAIL (near-miss)** | 0.588 **FAIL** |
| Max drawdown (<=0.25) | 0.078 PASS | 0.090 PASS |
| Net Sharpe after costs (>=0.5, 10bps/trade) | 0.866 PASS (27 trades) | 0.508 PASS (26 trades) |
| Walk-forward (4-split, >=0.75 pass_frac) | 1.00 PASS | 1.00 PASS |
| Parameter sensitivity (rel.std<=0.5, period in {20,34,50}) | 0.329 PASS | 0.568 **FAIL** |

## Decision

- **QQQ: reject (near-miss).** Sharpe (0.935) just misses the 1.0
  threshold; every other validator passes cleanly (MDD, TC-survival,
  walk-forward 100%, parameter sensitivity).
- **SPY: reject.** Sharpe fails more decisively (0.588) and
  parameter-sensitivity also fails (0.568 relative std).
- **Crypto: reject.** 0/72 grid cells passed.

Overall: rejected, but QQQ is a genuine near-miss worth revisiting -- a
future iteration could try a slightly faster period or a small trend
filter to push the Sharpe over 1.0 while keeping the strong MDD/TC/WF
profile.
