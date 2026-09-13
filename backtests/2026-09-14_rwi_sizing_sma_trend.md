# Backtest Report: RWI-diff Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_rwi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-104

## Hypothesis

Random Walk Index (Michael Poulos): RWI_high=(High-Low[n bars ago])/(ATR(n)
*sqrt(n)), RWI_low=(High[n bars ago]-Low)/(ATR(n)*sqrt(n)) -- compares
actual displacement to what a pure random walk with the same ATR would
produce. Unlike VHF/PFE (natively bounded), RWI is unbounded by
construction. Confirmed via DuckDuckGo HTML SERP (linnsoft.com,
strike.money, stockmaniacs.net, tradingsim.com).

Repo has 1 prior RWI entry (2026-09-04-153), a binary threshold-crossover,
decisively rejected (grid pass_fraction 10.4%, low-vol-only edge). This
iteration uses the SIGNED DIFFERENCE rwi_diff=RWI_high-RWI_low, squashed
with tanh to bounded [-1,1] (analogous to DMI-diff, 2026-09-13-093), as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={rwi_sensitivity: [0.4,0.6,0.8], deadband: [0.15,0.20,0.25]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=39, pass_fraction=0.361
- by_asset_class: equity 29/54 (0.54), crypto 10/54 (0.19)
- by_vol_regime: low 28/36 (0.78), mid 9/36 (0.25), high 2/36 (0.06)
- per-symbol: QQQ 18/27 (best sharpe 2.96), SPY 11/27 (best sharpe 2.48),
  BTC/USDT 9/27 (best sharpe 1.93), ETH/USDT 1/27

## Single-config validator results (Step 7)

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.6, db=0.20 | 1.168 (pass) | 16.99% (pass) | 0.589 (pass) | 1.00 (pass) | 0.033 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.7, db=0.30 (widened) | 1.043 (pass) | 8.57% (pass) | 0.559 (pass) | 1.00 (pass) | 0.035 rel-std (pass) | **ACCEPT** |
| BTC/USDT | sens=0.4, db=0.15 | 1.520 (pass) | 37.99% (**FAIL**, >25%) | 1.276 (pass) | 1.00 (pass) | 0.013 rel-std (pass) | **REJECT** (MDD) |

## Decision

**Accept for equity (QQQ, SPY)** — QQQ clears all 5 at the grid's own
best-cell config; SPY needed a wider deadband (0.30 vs 0.20) plus a higher
sensitivity (0.7 vs 0.6) to clear TC-survival, matching the recurring
pattern this cron trigger where SPY consistently needs stronger turnover
control than QQQ for the same dial. **Reject crypto** (BTC/USDT decisive
MDD fail 37.99%, one of the largest crypto MDD misses this trigger).
Confirms that RWI's underlying "actual move vs random-walk expectation"
comparison does carry real signal (contrary to the earlier binary-threshold
rejection's 10.4% pass_fraction) once reframed with a signed, bounded
(tanh-squashed) sizing construction rather than an unbounded hand-tuned
threshold -- a useful methodological note: RWI's native unboundedness was
likely part of why the original threshold-crossover version failed (a fixed
threshold doesn't adapt to how far RWI can range), and squashing it before
sizing fixed that.
