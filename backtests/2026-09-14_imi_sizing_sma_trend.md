# Backtest Report: IMI Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_imi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-100

## Hypothesis

Intraday Momentum Index (Tushar Chande): RSI-like 0-100 oscillator built
from each bar's open-to-close body move (cumulative up-body vs total
up+down body over a rolling window) rather than close-to-close changes.
Confirmed via DuckDuckGo HTML SERP (ta-lib.org, blinkx.in, alphasquawk.com,
figurebetter.com).

Repo has one prior IMI entry (2026-09-05-071), a binary oversold-recovery
mean-reversion trigger, accepted SPY-only (QQQ near-miss 0.859 Sharpe,
crypto decisively rejected). This iteration reframes IMI as a CONTINUOUS
SIZING dial within an SMA(trend_window) uptrend gate, testing whether the
sizing-dial construction extends the edge to QQQ.

## Grid test summary (Step 6)

`param_grid={imi_sensitivity: [0.4,0.6,0.8], deadband: [0.05,0.10,0.15]}`
(deadband range widened upfront given this cron trigger's recurring
transaction-cost lesson from the BOP iteration), `symbols={equity:
[QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01.

- total_cells=108, passed=44, pass_fraction=0.407
- by_asset_class: equity 27/54 (0.50), crypto 17/54 (0.31)
- by_vol_regime: low 32/36 (0.89), mid 12/36 (0.33), high 0/36 (0.00)
- best_cell: QQQ, sens=0.6/db=0.15, low-vol, Sharpe 3.047

## Single-config validator results (Step 7)

Grid best-cell config (sens=0.6, db=0.15) still failed TC-survival on both
equity symbols (QQQ net Sharpe 0.326 at 315 trades; SPY net Sharpe 0.129 at
293 trades). Widened deadband further (0.2-0.3): QQQ clears all 5
validators at db=0.2; SPY's gross Sharpe stays below 1.0 (0.84-0.93) at
every deadband tried in that range, so SPY does not clear even after cost
control improves.

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.6, db=0.2 | 1.106 (pass) | 12.64% (pass) | 0.504 (pass) | 0.75 (pass) | 0.034 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.6, db=0.15 (best tried) | 0.922 (**FAIL**) | 8.74% (pass) | 0.129 (**FAIL**) | 1.00 (pass) | 0.052 rel-std (pass) | **REJECT** (Sharpe, TC-survival across all deadbands tried) |
| BTC/USDT | sens=0.6, db=0.15 | 1.516 (pass) | 36.57% (**FAIL**, >25%) | 1.265 (pass) | 1.00 (pass) | 0.010 rel-std (pass) | **REJECT** (MDD) |

## Decision

**Accept for QQQ only** — all 5 validators pass at deadband=0.2. **Reject
SPY** (Sharpe stays below 1.0 across every deadband tested 0.05-0.3; unlike
BOP where widening the deadband alone rescued SPY, here SPY's IMI-sizing
gross return profile itself is too weak, not just cost-drag-limited).
**Reject crypto** (BTC/USDT decisive MDD fail 36.57%, this cron trigger's
worst crypto MDD miss yet for a sizing-dial strategy). Interesting
asymmetry vs the prior binary-IMI entry (2026-09-05-071, accepted SPY-only,
QQQ near-miss): the sizing-dial reframing flips which symbol clears --
supports this cron trigger's broader finding that binary-vs-continuous
framing changes not just whether a strategy passes but *which* symbol it
passes on, reinforcing the value of testing both framings per indicator
rather than assuming one dominates.
