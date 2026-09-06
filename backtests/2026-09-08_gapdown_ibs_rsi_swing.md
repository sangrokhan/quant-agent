# Gap-Down + Low-IBS + Low-RSI Swing Mean-Reversion — Backtest Report

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_gapdown_ibs_rsi_swing.py`
**Source:** https://www.quantifiedstrategies.com/gap-trading-strategies/
("Gap trading in swing trading" section — fully disclosed, non-paywalled
rule; source's own S&P-500-futures 2011-2021 backtest reports avg gain
0.48%/trade, profit factor 1.8; SPY EOD version reports ~0.5% avg
gain/trade with a rising equity curve)

## Hypothesis
A gap-down opening (>= `gap_down_pct`) combined with a weak prior-day IBS
(<= `ibs_threshold`) and a low prior-day 5-day RSI (<= `rsi_threshold`)
marks oversold exhaustion worth a long entry at today's open; exit at
today's close if the close recovers above yesterday's close (gap filled),
else hold up to `max_hold_days` as a safety time-stop. Rationale (source's
own): captures "the extra risk premium of the gap down opening."

## Grid test (Step 6)
`param_grid={"gap_down_pct": [0.15, 0.3, 0.5], "rsi_threshold": [40, 45, 50],
"max_hold_days": [5, 7]}`, symbols `{"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total: 33/216 pass (15.3%)**
- By asset class: equity 33/108 (30.6%), crypto 0/108 (0%)
- By vol regime: low 33/72 (45.8%), mid 0/72 (0%), high 0/72 (0%)
- Best cell: `gap_down_pct=0.3, rsi_threshold=50, max_hold_days=5`, SPY,
  low-vol, Sharpe 2.40
- Worst cell: `gap_down_pct=0.5, rsi_threshold=45, max_hold_days=5`, QQQ,
  mid-vol, Sharpe -0.89

Same pattern as this repo's other single-regime "mean reversion" hits:
the grid pass rate is concentrated almost entirely in the low-vol tercile,
a red flag that the edge may not survive full-sample pooling.

## Single-config validation (Step 7), best grid config
`gap_down_pct=0.3, rsi_threshold=50.0, max_hold_days=5`

| Symbol | Sharpe | Threshold | Pass | MDD | Threshold | Pass | Net Sharpe (10bps) | Threshold | Pass |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 0.244 | 1.0 | No | 0.191 | 0.25 | Yes | 0.143 | 0.5 | No (74 trades) |
| SPY | 0.683 | 1.0 | No | 0.144 | 0.25 | Yes | 0.539 | 0.5 | Yes (59 trades) |

Walk-forward (manual 4-split fallback on SPY, `vectorbt.utils.splitting`
still broken): 3/4 splits Sharpe>0 = 0.75 pass fraction — **pass**.

Parameter sensitivity (relative std of Sharpe across `gap_down_pct` in
{0.15, 0.3, 0.5} at `rsi_threshold=50, max_hold_days=5`, SPY): relative std
0.247 (mean 0.653, std 0.161) — **pass** (<0.5).

## Decision: REJECTED

Full-sample pooled Sharpe (0.244 QQQ, 0.683 SPY) both miss the 1.0
threshold — QQQ decisively, SPY as a near-miss. QQQ additionally fails
transaction-cost survival (net Sharpe 0.143 after 74 trades @ 10bps).
As with the repo's prior IBS/gap-family entries, the grid's apparent
30.6% equity pass rate is concentrated in the low-vol tercile only and
does not survive pooling across the full sample/all regimes. MDD, walk-
forward, and parameter sensitivity all pass — the strategy is stable but
not profitable enough on a full-sample basis. Crypto fails decisively
(0/108 grid cells).

Future loop idea: SPY's near-miss Sharpe (0.68) plus its TC-survival PASS
suggests this could be worth revisiting with a tighter, low-vol-regime-only
gate (similar to how 2026-09-04-159 rescued 2026-09-04-158 by narrowing the
parameter neighborhood) — e.g. adding an explicit realized-vol percentile
filter so the strategy only trades in the regime where it actually works,
rather than trying to make the unconditional version pass full-sample.
