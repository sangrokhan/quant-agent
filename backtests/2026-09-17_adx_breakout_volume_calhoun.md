# ADX Breakout with Volume Confirmation (Calhoun, TASC Mar 2016) — Rejected

**Source:** https://traders.com/Documentation/FEEDbk_docs/2016/03/TradersTips.html
(Ken Calhoun, "ADX Breakouts", TASC March 2016; TradeStation EasyLanguage code disclosed)

**Hypothesis:** Wilder ADX(14) crossing above a high trigger level (35-45)
combined with above-average volume (>=1.1-1.3x 20-day avg) signals a strong
momentum breakout getting underway. Exit rule (our addition, since the
source only specifies entry + an unreplicable floating trailing stop):
ADX falling back below an exit_level, or a max_hold_days time-stop.

## Grid summary (144 cells: 3 trigger_level x 2 exit_level x 2 volume_multiplier
x 4 symbols x 3 vol regimes)

- pass_fraction: 0.1667 (24/144)
- by_asset_class: equity 6/72, crypto 18/72
- by_vol_regime: low 10/48, mid 14/48, **high 0/48** (fails in every high-vol
  cell across both asset classes — ADX-crossover entries whipsaw badly in
  choppy/high-vol conditions)
- best_cell: BTC/USDT, mid-vol, trigger_level=35/exit_level=20/volume_multiplier=1.1,
  Sharpe=2.058

## Single-config validation (best avg-Sharpe config: BTC/USDT,
trigger_level=40, exit_level=25, volume_multiplier=1.3)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | -0.005 | >= 1.0 | FAIL |
| Max drawdown | 45.3% | <= 25% | FAIL |
| TC survival (net Sharpe, 200 trades) | -0.031 | >= 0.5 | FAIL |
| Walk-forward (4 splits) | 0.75 (3/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.593 | <= 0.5 | FAIL |

## Verdict: REJECTED

The grid's headline BTC/USDT mid-vol-only cell (Sharpe 2.06) was a narrow
single-tercile artifact — full-sample validation on that config decisively
fails Sharpe, MDD, TC-survival, and parameter sensitivity. Only walk-forward
passed. Equity (QQQ/SPY) results were also weak (6/72 grid cells passed,
best average Sharpe only 0.89, itself just one regime). The high-vol regime
failed 0/48 across every asset class and parameter combination, indicating
ADX-level-crossing is not a robust entry trigger under choppy/volatile
conditions regardless of asset class.
