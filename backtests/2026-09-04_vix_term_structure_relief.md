# VIX Term-Structure "Buy the Relief" (SPY) — REJECTED (near-miss)

**Hypothesis:** VIX/VIX3M ratio > 1.0 = backwardation (panic, near-term
fear exceeds longer-term fear); ratio <= 1.0 = contango (calm). Per
Options Cafe's VIX term-structure article, buying the initial panic spike
is a coin flip, but buying the "relief" — the moment the ratio crosses
back down from backwardation into contango — substantially improves
short-horizon SPY win rate (source claims 88% over 5 trading days on 17yr
of data). Long entry on that down-cross, exit after relief_hold_days or a
renewed backwardation spike.

**Source:** https://options.cafe/blog/vix-term-structure-contango-backwardation
(concrete numeric rule: VIX/VIX3M ratio, threshold 1.0, worked historical
examples). Distinct from the previously-rejected VIX-Bollinger-Band
mean-reversion strategy (2026-09-04-103, single-series own-range spike
trigger) — here the signal compares TWO points on the vol curve.

**Novelty:** First VIX term-structure (multi-tenor implied-vol comparison)
strategy in this repo.

## Best config: relief_hold_days=3, backwardation_threshold=1.0 (SPY, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.962 | >= 1.0 | **FAIL (near-miss)** |
| Max drawdown | 10.03% | <= 25% | PASS |
| Transaction cost survival (5bps/trade, 84 trades) | net Sharpe 0.799 | >= 0.5 | PASS |
| Walk-forward | SKIPPED | n/a | Repo-wide `vectorbt.utils.splitting` API issue, see 2026-09-04-154 |
| Parameter sensitivity | not formally computed | n/a | Grid itself shows high dispersion across params (see below) — inferred fail |

## Step 6 grid summary (relief_hold_days in [3,5,8] x backwardation_threshold in [0.98,1.0,1.02], symbols QQQ/SPY equity ONLY — crypto has no analogous VIX/VIX3M term-structure data via this repo's loaders, so no crypto cells attempted)

- **Overall pass_fraction: 14.8%** (8/54 cells)
- **By vol regime: low 0/18, mid 0/18, high 8/18 (44.4%)** — this strategy's edge, such as it is, concentrates ENTIRELY in high-vol regimes, which makes intuitive sense (the VIX-backwardation signal only fires during genuine stress episodes) but means it contributes nothing in calm/normal markets, most of the sample.
- No single (symbol, param) combination passed more than 1 of 3 vol-regime cells — the "best cell" (SPY, hold=3, threshold=1.0, high-vol, Sharpe 1.44) is a single favorable slice, not a robust pattern across regimes/params.
- **Worst cell:** SPY, hold=5, threshold=0.98, low-vol, Sharpe -1.24.

## Decision: REJECT (near-miss, worth revisiting)

Full-sample SPY Sharpe (0.96) is a genuine near-miss just under the 1.0
threshold, and both max drawdown and transaction-cost survival pass
cleanly. However the grid shows the edge is concentrated exclusively in
high-vol regimes (0% pass in low/mid-vol) and no param combo is robust
across regimes — consistent with a real but narrow/regime-specific signal
rather than a broadly reliable one. Given the Sharpe near-miss and the
economically sensible high-vol-only concentration (this is fundamentally
a crisis-relief signal, not an all-weather strategy), a future loop should
consider: (1) restricting entries to ONLY fire when already in a
detected high-vol regime (removing the low/mid-vol noise trades that drag
down full-sample Sharpe), or (2) sizing/leveraging positions higher during
these rarer but higher-conviction relief signals. Recording as rejected
per the strict >=1.0 Sharpe threshold, but flagging as the strongest
near-miss of this cron trigger's 4 iterations.
