# Backtest Report: Weak-Prior-Month Downside-Tail-Risk Gate

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_weak_month_tailrisk_gate.py`
**Source:** Valeriy Zakamulin, "Industry Rotation Using Market-State
Similarity" (2026), summarized in Quantitativo Weekly #4,
https://www.quantitativo.com/p/quantitativo-weekly-4 (read via
browser_exec after direct navigation from the Quantitativo archive page).

## Hypothesis

The source finds a weak market month predicts a worse LEFT TAIL (downside
risk) for the following month — a signal nearly invisible to OLS (which
looks at conditional means) but visible via quantile regression. The
source's own strategy classifies the current market state (standardized
excess return) and rotates away from what performed badly after similar
historical states; its payoff is specifically a risk-reduction story
(Sharpe 0.56->0.71, MDD roughly halved 54%->26%). Adapted to a
single-asset TS gate: classify the trailing month's return by its own
historical percentile; when in the WEAK (bottom `weak_percentile`) tail,
go flat regardless of trend status (an asymmetric downside-only gate);
otherwise follow a standard SMA trend filter.

## Grid test summary (Step 6)

`param_grid={"weak_percentile":[0.1,0.2,0.3], "trend_window":[50,100]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **total_cells:** 72, **passed:** 18, **pass_fraction: 0.25**
- **by_asset_class:** equity 18/36; crypto 0/36 (decisive reject)
- **by_vol_regime:** low 12/24, mid 6/24, high 0/24
- **best_cell:** QQQ, weak_percentile=0.1, trend_window=50, low-vol regime,
  Sharpe 2.78; worst_cell: same symbol/weak_percentile with
  trend_window=100, high-vol regime, Sharpe -0.54

## Single-config validation (Step 7): weak_percentile=0.1, trend_window=50

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.072 (PASS) | 0.99999838 (**FAIL**, essentially at the bar) | >= 1.0 |
| Max drawdown | 0.184 (PASS) | 0.215 (PASS) | <= 0.25 |
| TC survival (5bps/trade) | 0.995 (PASS, 121 trades) | 0.899 (PASS, 117 trades) | >= 0.5 |
| Walk-forward (4 manual chunks) | 0.75 (PASS, borderline) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity (relative_std, 6-combo grid) | 0.104 (PASS) | 0.124 (PASS) | <= 0.5 |

(Manual 4-chunk walk-forward workaround used per pre-existing
`vbt.utils.splitting` AttributeError bug.)

## Decision: **ACCEPT (QQQ only)**

QQQ passes every validator at this config (Sharpe 1.072, MDD 18.4%, TC-net
Sharpe 0.995, walk-forward 3/4 chunks positive, parameter sensitivity
relative_std 0.104 — quite stable across the grid). SPY is a hair below the
Sharpe threshold (0.999998... vs 1.0 — a razor-thin miss) despite passing
every other validator comfortably; a slight parameter tweak or longer
sample would very plausibly flip it, but per the strict "all validators
must pass" acceptance rule, SPY at this exact config does not qualify.
Crypto rejected decisively (0/36) — the "weak-month tail-risk" concept
built on trailing-percentile classification of monthly returns doesn't
transfer meaningfully to crypto's return distribution over this window.

Scope: **equity, QQQ only**, not a broad multi-asset strategy. The
mechanism (an asymmetric downside-only gate triggered specifically by a
historically weak PRIOR month, layered on a standard trend filter) is
distinct from every other regime-filter entry in this repo (MAX-effect
2026-09-06-162 and ATR-percentile 2026-09-06-163 gate on volatility/return
extremity of EITHER sign; valuation-boundary 2026-09-08-145 gates on a
long-term price-level deviation) — a genuinely new accepted angle.
