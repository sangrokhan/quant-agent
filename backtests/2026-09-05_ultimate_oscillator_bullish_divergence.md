# Ultimate Oscillator (UO) Bullish Divergence — Backtest Report

**Hypothesis:** Ultimate Oscillator (UO, Larry Williams, 7/14/28-period
buying-pressure/true-range blend weighted 4:2:1) bullish divergence — price
makes a new N-bar low while UO makes a higher low (divergence low below 30)
— followed by UO breaking back above the UO level recorded at the
divergence, signals a long entry per the source's own confirmation trigger.

**Source:** https://www.tradingview.com/support/solutions/43000502328-ultimate-oscillator-uo/
("Bullish Divergence forms meaning price forms a lower low while UO makes a
higher low. The low of the Divergence should be below 30. UO breaks above
the high of the Divergence.") + https://arrowalgo.com/ultimate-oscillator-complete-guide-algorithmic-trading/
(corroborating: "Watch for bullish divergence with the Ultimate Oscillator
below 30 to enter long positions").

**Strategy file:** `strategies/2026-09-05_ultimate_oscillator_bullish_divergence.py`

## Step 6 — Grid test summary (param_grid: swing_lookback in [10,15,20] x
max_hold_days in [10,15]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 0, **pass_fraction: 0.0** (decisive fail)
- by_asset_class: equity 0/36 (100% of equity cells errored with
  `empty/no-trade slice` — the divergence + confirm-break conjunction never
  fires a single trade on QQQ or SPY across any parameter combination or
  vol regime in this 2019-2026 window); crypto 0/36 (weak positive Sharpe
  in most cells but never clears the 1.0 threshold)
- by_vol_regime: low 0/24, mid 0/24, high 0/24
- best_cell: swing_lookback=10, max_hold_days=10, ETH/USDT, mid-vol,
  Sharpe=0.166 (far below 1.0 threshold)
- worst_cell: swing_lookback=20, max_hold_days=10, BTC/USDT, high-vol,
  Sharpe=-0.137

## Step 7 — Single-config validators

Skipped: the grid is decisively 0/72 with equity generating literally zero
trades across every cell (entry condition — recent divergence AND UO
breaking back above its own divergence-flag value — is too rare/strict
given the `oversold_level < 30` divergence-low precondition combined with
the `ffill().shift(1)` confirm-break reference, which in practice only
resets rarely and QQQ/SPY's UO rarely dips that low with a confirming
divergence pattern in this dataset), and crypto's best Sharpe (0.166) is an
order of magnitude below the 1.0 pass threshold. Running the full
single-config validator suite would add no information beyond what the grid
already shows definitively.

## Outcome: **REJECTED**

Zero trades in equity across all 36 cells (entry condition never fires);
crypto technically trades but with weak positive Sharpe far below threshold
in the best cell (0.166) and negative in several cells. The UO divergence +
"break above divergence high" confirmation trigger, as operationalized here
via the UO value at the divergence flag bar, is either too rare to be
useful on QQQ/SPY daily bars or the confirm_break approximation needs
refinement (e.g. tracking an explicit rolling max of UO since the
divergence bar rather than the single flag-bar value) — worth revisiting in
a future loop with a looser confirmation rule (e.g. simple oversold-level
cross like the MFI divergence variant, 2026-09-05-061, used) rather than
the literal "breaks above the divergence high" reading.
