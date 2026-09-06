# IBS + 5-Day-Low Breakdown, Fixed Time-Exit — Backtest Report

**Date:** 2026-09-07
**Strategy file:** `strategies/2026-09-07_ibs_5day_low_timeexit.py`
**Source:** https://www.quantifiedstrategies.com/5-day-low-of-the-range-strategy/
("The 5-Day Low of The Range Strategy" — own disclosed rule, SPY 1993-2026
backtest reports 309/517 (~60%) winners, 10.76% annualized over the
3-7-day holding sweet spot vs buy-and-hold)

## Hypothesis
Single-day IBS < `ibs_threshold` (close near the day's low) combined with
close breaking below the prior `lookback_days`-day low signals a short-term
panic/exhaustion worth a mean-reversion long. Exit on a **fixed time-stop**
(`hold_days`, source's own 3-7-day sweet spot) rather than a signal-based
exit — distinct from every other IBS-family strategy already in this repo
(2026-09-04-089/158/159 signal-based exits, 2026-09-05-019 failed-bounce
pattern), and tested with **no trend filter** (source's own backtest is
unconditional across the full 1993-2026 sample).

## Grid test (Step 6)
`param_grid={"ibs_threshold": [0.15, 0.25, 0.35], "hold_days": [3, 5, 7]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total: 19/108 pass (17.6%)**
- By asset class: equity 19/54 (35.2%), crypto 0/54 (0%)
- By vol regime: low 18/36 (50%), mid 1/36 (2.8%), high 0/36 (0%)
- Best cell: `ibs_threshold=0.35, hold_days=5`, SPY, low-vol, Sharpe 2.86
- Worst cell: `ibs_threshold=0.15, hold_days=7`, QQQ, mid-vol, Sharpe -0.52

Grid cells only pass narrowly and almost exclusively in the low-vol
tercile — full-sample validation below shows this does not survive once
all volatility regimes are pooled together.

## Single-config validation (Step 7), best grid config `ibs_threshold=0.35, hold_days=5`

| Symbol | Sharpe | Threshold | Pass | MDD | Threshold | Pass | TC net Sharpe | Threshold | Pass |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 0.346 | 1.0 | No | 0.299 | 0.25 | No | 0.239 | 0.5 | No |
| SPY | 0.441 | 1.0 | No | 0.248 | 0.25 | Yes | 0.311 | 0.5 | No |

Walk-forward: skipped — known scaffold bug, `vectorbt.utils.splitting`
module does not exist in the installed vectorbt version (documented in
prior entries, e.g. 2026-09-03-002/004).

Parameter sensitivity (relative std of Sharpe across `ibs_threshold` in
{0.15, 0.25, 0.35} at `hold_days=5`): QQQ 0.350 (pass, <0.5), SPY 0.133
(pass, <0.5) — the strategy IS parameter-stable, it's just decisively
unprofitable on a full-sample, all-regime basis.

## Decision: REJECTED

Full-sample Sharpe (0.35 QQQ, 0.44 SPY) is far below the 1.0 threshold on
both equity symbols — not a near-miss. The grid's apparent 35% equity pass
rate is an artifact of cherry-picking the low-vol tercile only; pooled
across all volatility regimes the edge evaporates, consistent with the
source's own admission that "lately the strategy has not performed well."
Crypto fails decisively (0/54 grid cells). No further validators needed
per Step 7 minimum-subset guidance (decisive Sharpe fail).
