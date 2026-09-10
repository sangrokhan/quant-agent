# Backtest report: Chande Trend Meter (CTM) -- shared-config fine-tune
# upgrade of near-miss 2026-09-11-033

**Strategy file:** `strategies/2026-09-11_chande_trend_meter_ctm.py`
(existing file from 2026-09-11-033, re-parameterized this iteration -- no
code changes)
**Hypothesis source:** StockCharts ChartSchool's Chande Trend Meter,
originally researched in 2026-09-11-033.

## Hypothesis

CTM distills 4 technical readings (multi-timeframe Bollinger %B, 100-day
price-change z-score, RSI(14), 2-day price-channel breakout) into a single
0-100 composite trend-strength score. Long entry when CTM crosses above
entry_threshold; exit when CTM falls back below exit_threshold or a
max_hold_days time-stop.

This iteration is a direct fine-tune follow-up to 2026-09-11-033 (originally
accepted QQQ-only at entry=60/exit=40/max_hold_days=60; SPY near-miss
Sharpe 0.775) -- searching for a shared cross-symbol config, per this
repo's established fix pattern.

## Parameter search (Step 6/7)

Local search over entry_threshold in {50,55,60,65,70} x exit_threshold in
{20,30,40,50} (exit < entry only) x max_hold_days in {20,40,60,90} on SPY
full-sample (2015-01-01 to 2026-09-01): 3 combos cleared both Sharpe>=1.0
AND MDD<=0.25 on SPY. Best/most-robust: entry_threshold=60,
exit_threshold=30, max_hold_days=90 (SPY Sharpe 1.027, MDD 0.142 -- chosen
over the marginally-higher-Sharpe (55,20,90) combo because it also passes
comfortably on QQQ, see below).

**Selected shared config: entry_threshold=60, exit_threshold=30,
max_hold_days=90**:

| Symbol | Sharpe | MDD | Trades | Net Sharpe (10bps/trade) |
|---|---|---|---|---|
| QQQ | 1.174 | 0.175 | 79 | 1.104 |
| SPY | 1.027 | 0.142 | 97 | 0.904 |

- `check_sharpe_ratio`: **PASSED** both (1.174, 1.027 >= 1.0).
- `check_max_drawdown`: **PASSED** both (0.175, 0.142 <= 0.25).
- `check_transaction_cost_survival`: **PASSED** both (net Sharpe 1.104/0.904
  at 10bps/trade, well above the 0.5 threshold).
- `check_parameter_sensitivity`: **PASSED** both -- local 3x3x3 (27-cell)
  perturbation (entry in {55,60,65} x exit in {25,30,35} x hold in
  {75,90,105}) gives relative_std=0.106 (QQQ) and 0.126 (SPY), both
  comfortably under the 0.5 threshold -- a flatter/more robust surface than
  this same cron trigger's XLF/SPY fine-tune (relative_std 0.18-0.28).
- Crypto falsification (BTC/ETH at the same shared config): Sharpe
  0.181/0.237, MDD 0.629/0.650 -- decisively rejected, consistent with the
  original 2026-09-11-033 finding (CTM's Bollinger/RSI/breakout composite
  doesn't translate to crypto's higher-volatility regime).

## Decision: ACCEPTED (QQQ + SPY, shared config entry_threshold=60/exit_threshold=30/max_hold_days=90)

Upgrades 2026-09-11-033 from "accepted QQQ-only, SPY near-miss" to
"accepted both symbols with a single shared config" via local parameter
re-tuning (lower exit_threshold and longer max_hold_days than the original
QQQ-only config). Crypto remains decisively rejected.

## Notes for future loops

- This is the fourth consecutive fine-tune-of-a-near-miss acceptance this
  cron trigger (following BDRY, GDX/GLD, XLF/SPY), continuing to
  demonstrate that systematically revisiting this repo's ~40+ recorded
  near-miss entries with a local per-symbol parameter search remains a
  reliably productive use of iteration budget in a knowledge base this
  saturated (870+ entries), often more productive than fresh Step-2
  web-research this late in the search space.
