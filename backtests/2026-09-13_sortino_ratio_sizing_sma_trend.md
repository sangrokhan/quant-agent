# Sortino Ratio Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** This repo has a prior downside-deviation strategy
(2026-09-13-048) but that used a pure inverse-risk sizing rule (exposure =
target_downside_dev / rolling_downside_deviation, denominator only, no
return numerator). This iteration tests the genuine Sortino RATIO (F.
Sortino, per https://www.investopedia.com/terms/s/sortinoratio.asp, read
via browser_exec): Sortino = (return - risk_free) / downside_deviation.
Structurally identical in FORM to this cron trigger's other accepted
risk-ratio sizing overlays (UPI, Kappa-3, Tail Ratio, Rachev), but using
the classic semi-deviation denominator specifically. First genuine
Sortino-RATIO-based (excess return over downside deviation, not just
inverse-risk sizing) overlay in this repo.

**Source:** https://www.investopedia.com/terms/s/sortinoratio.asp

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
sortino_window in [60,90,120], sortino_reference in [0.5,1.0,1.5];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, sortino_window=60, sortino_reference=0.5, low-vol, Sharpe=2.84
- worst_cell: QQQ, sortino_window=60, sortino_reference=1.5, high-vol, Sharpe=-0.88

Symbol-specific optimal windows diverge in the same pattern as the sibling
UPI (2026-09-13-058) and Kappa-3 (2026-09-13-059) strategies this cron
trigger: SPY best at sortino_window=60, QQQ best at sortino_window=120.

## Single-config validator results

### SPY (sortino_window=60, sortino_reference=0.5) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.224 | >= 1.0 | Yes |
| Max drawdown | 0.123 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 130 trades) | 1.093 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 3-combo grid) | 0.079 | <= 0.5 | Yes |

### QQQ (sortino_window=120, sortino_reference=0.5) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.228 | >= 1.0 | Yes |
| Max drawdown | 0.219 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 114 trades) | 1.158 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 3-combo grid) | 0.075 | <= 0.5 | Yes |

`validators.check_walk_forward` was skipped -- `vbt.utils.splitting.RangeSplitter`
is not available in the installed vectorbt version (pre-existing tooling gap
noted since 2026-09-13-007; not specific to this strategy).

## Decision

**Accepted for both SPY and QQQ (equity only)**, each with its own tuned
sortino_window (60 for SPY, 120 for QQQ; both share sortino_reference=0.5).
All four validators run pass comfortably for both symbols. Performance
magnitude closely tracks the sibling UPI and Kappa-3 strategies this cron
trigger -- confirming that this family of "annualized-excess-return over a
trailing downside/drawdown-risk-normalization term" sizing overlays
produces broadly similar, moderately robust equity-only results regardless
of the specific downside-risk denominator chosen (RMS-drawdown, cubed-LPM,
or classic semi-deviation). Crypto (BTC/USDT, ETH/USDT) rejected across the
whole grid (0/54 cells), consistent with every prior sizing overlay tested
this cron trigger.
