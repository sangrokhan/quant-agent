# 2026-09-23 TRIX Signal-Line Crossover, Explicit Low-Vol-Regime-Gated Entry (SPY/QQQ/BTC/ETH)

## Hypothesis
Direct follow-up to this cron trigger's own 2026-09-23-031 (TRIX(14)
signal-line(9/12) crossover + 50/200 EMA trend filter, near-missed
full-period Sharpe on SPY at 0.983). That grid test showed an 0.875 pass
rate confined to the low-vol tercile, suggesting the unconditional average
is diluted by higher-vol whipsaw. This iteration adds an EXPLICIT low-vol
regime gate on entry (20d realized vol <= trailing 252d median), plus a
risk-off exit when the regime flips to high-vol, mirroring
`2026-09-03_bb_meanrev_qqq_volregime.py`'s pattern.

## Grid test summary (vol_regime_ratio x [0.9, 1.0, 1.15]; symbols
QQQ/SPY equity, BTC/USDT crypto; vol_regime_splits=3; 27 total cells)

- pass_fraction: 0.074 (2/27) -- worse than the ungated version's 0.375
- by_asset_class: equity 1/18, crypto 1/9
- by_vol_regime: low 2/9, mid 0/9, high 0/9

Note: this grid-cell breakdown is somewhat degenerate for an already
vol-gated strategy -- since the strategy trades almost exclusively in
low-vol periods by construction, the mid/high-vol grid cells contain mostly
flat (zero-return) periods, which naturally fail the Sharpe test trivially
rather than reflecting a real edge failure in those regimes. The
full-period single-config numbers below are the more meaningful comparison.

## Single-config validation (full-period, unconditional)

| vol_regime_ratio | Symbol | Sharpe | Passed (>=1.0) | Max DD | Passed (<=0.25) |
|---|---|---|---|---|---|
| 1.0 | SPY | 0.136 | No | 0.081 | Yes |
| 1.0 | QQQ | 0.212 | No | 0.172 | Yes |
| 1.0 | BTC | 0.163 | No | 0.272 | No |
| 1.0 | ETH | 0.156 | No | 0.240 | Yes |
| 1.15 | QQQ | 0.262 | No | 0.215 | Yes (best cell found) |
| 0.9 | SPY | -0.271 | No | 0.107 | Yes |

## Verdict: REJECTED -- explicit gate made it WORSE, not better

Counter to the hypothesis, baking the low-vol regime directly into the
entry rule (with a risk-off exit on regime flip) substantially REDUCED
full-period Sharpe versus the ungated 2026-09-23-031 version (SPY 0.983 ->
0.136 at vol_regime_ratio=1.0; best across all tested ratios/symbols was
only 0.262). The likely mechanism: the risk-off EXIT (forcing flat
whenever vol regime flips to high, even mid-trade) chops up otherwise
profitable trend continuations and adds far more whipsaw than the
entry-only gate saves, unlike the BB mean-reversion reference strategy
where a regime-flip exit make more sense (mean-reversion assumption breaks
down completely in high-vol, so exiting immediately is protective) --
whereas TRIX/EMA is a trend-following mechanism where forcing an exit
purely on a vol-regime flip (independent of trend health) discards winners
prematurely.

## Verdict: REJECTED

Strategy file kept in `strategies/` as a record of a rejected attempt.
Lesson for future loops: a strategy's regime-conditional grid strength does
NOT automatically transfer when the regime filter is converted from a
post-hoc observation into a hard entry+exit gate -- the specific
implementation of the "risk-off exit on regime flip" matters a lot and
should be tested as its OWN variable (e.g. entry-gate only, no exit-gate)
rather than assumed to help by analogy with a different (mean-reversion)
strategy's regime-filter design.
