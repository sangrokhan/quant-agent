# Backtest Report: SMI Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_smi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-098

## Hypothesis

Stochastic Momentum Index (William Blau, 1993): close's displacement from
the midpoint (not low) of the recent high-low range, numerator and
denominator each double-EMA-smoothed then divided, bounded roughly
[-100,+100]. Confirmed via DuckDuckGo HTML SERP (luxalgo.com, tradiecapital.com,
forexmt4indicators.com, ta-lib.org, all consistent).

Repo has one prior SMI entry (2026-09-04-140), a binary oversold-threshold
signal-line-crossover, decisively rejected. This iteration reframes SMI as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate, same
pattern that rescued VZO/ADX/DMI-diff/CHOP/Vortex/TSI earlier.

## Grid test summary (Step 6)

`param_grid={smi_sensitivity: [0.4,0.6,0.8], deadband: [0.05,0.10]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=72, passed=29, pass_fraction=0.403
- by_asset_class: equity 18/36 (0.50), crypto 11/36 (0.31)
- by_vol_regime: low 20/24 (0.83), mid 9/24 (0.38), high 0/24 (0.00)
- per-symbol: QQQ 12/18 (best sharpe 2.76 @ sens=0.4,db=0.1), SPY 6/18 (best
  sharpe 2.62 @ sens=0.8,db=0.1), BTC/USDT 9/18 (best sharpe 1.76 @
  sens=0.4,db=0.05), ETH/USDT 2/18 (best sharpe 2.44 @ sens=0.4,db=0.05)

## Single-config validator results (Step 7)

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.4, db=0.1 | 1.093 (pass) | 14.88% (pass) | 0.609 (pass) | 0.75 (pass) | 0.014 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.8, db=0.1 | 1.027 (pass) | 10.48% (pass) | 0.438 (**FAIL**, <0.5) | 0.75 (pass) | 0.015 rel-std (pass) | **REJECT** (TC-survival) |
| BTC/USDT | sens=0.4, db=0.05 | 1.454 (pass) | 30.95% (**FAIL**, >25%) | 1.156 (pass) | 1.00 (pass) | 0.007 rel-std (pass) | **REJECT** (MDD) |

## Decision

**Accept for QQQ only** — all 5 validators pass. **Reject SPY** (fails
transaction-cost survival: net Sharpe 0.438 misses the 0.5 threshold at
246 trades despite a passing gross Sharpe/MDD). **Reject crypto**
(BTC/USDT decisive MDD fail 30.95% vs 25% threshold, consistent with this
cron trigger's recurring crypto-drawdown pattern for sizing-dial overlays).
Same QQQ-only-among-equity outcome as RMI (2026-09-14-097) -- both this
iteration's oscillator-family sizing dials clear QQQ but not SPY, unlike
the volume/trend-strength family (VZO/ADX/DMI-diff/CHOP/Vortex/TSI) which
cleared both. Worth flagging as a pattern for a future iteration: oscillator
(bounded-momentum) sizing dials may generate more SPY trades / higher cost
drag than trend-strength dials at comparable deadband settings.
