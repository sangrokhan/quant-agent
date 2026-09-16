# 2026-09-17 — Ehlers Adaptive SuperSmoother crossover + vol-regime gate

**Hypothesis:** Direct fix attempt for prior near-miss rejection
(2026-09-12-146, Ehlers Adaptive SuperSmoother vs fixed-period SuperSmoother
crossover). That entry's own `notes` explicitly suggested: "explicit
vol-regime gate to flatten during high realized-vol, consistent with several
prior accepted strategies." This strategy is identical crossover logic
(TASC September 2026 Traders' Tips, John F. Ehlers "Adaptive SuperSmoother",
re-confirmed via https://traders.com/documentation/feedbk_docs/2026/09/traderstips.html),
plus a realized-vol regime gate (flatten when trailing 20d realized vol >
252d trailing median) copied from the pattern in
strategies/2026-09-03_bb_meanrev_qqq_volregime.py.

## Grid summary (base_period={20,30} x min_hold_days={5,10} x vol_regime_ratio={0.9,1.0}, symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3, 2019-01-01 to 2026-09-01, 96 cells)

- Overall pass_fraction: 0.167 (16/96)
- By asset class: equity 16/48 passed, crypto 0/48 passed (decisive reject)
- By vol regime: low 16/32, mid 0/32, high 0/32
- Best cell: crypto ETH/USDT mid-vol Sharpe 2.26 (single lucky cell, not representative -- crypto overall 0/48)
- Worst cell: crypto ETH/USDT high-vol Sharpe -0.91

## Single-best-config validators (base_period=30, min_hold_days=5, vol_regime_ratio=1.0, 2018-01-01 to 2026-09-01)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe | 0.820 | 0.831 | >=1.0 | **FAIL both** |
| Max Drawdown | 0.123 | 0.115 | <=0.25 | PASS both (fixed the prior MDD failure) |
| TC-adjusted Sharpe | 0.632 | 0.544 | >=0.5 | PASS both |
| Walk-forward (manual 4-slice) | 0.75 | 1.0 | >=0.75 | PASS both |
| Parameter sensitivity (rel std) | 0.107 | 0.180 | <=0.5 | PASS both |

## Verdict: REJECTED (both QQQ and SPY)

The vol-regime gate successfully fixed the prior MDD failure (26.9%/28.7% ->
12.3%/11.5%) exactly as the prior entry's notes predicted, but overcorrected:
by flattening during mid/high-vol regimes entirely, both symbols' full-sample
annualized Sharpe dropped below the 1.0 threshold (0.82/0.83), because too
much of the historically-profitable trend exposure was cut. Crypto remains
decisively rejected (0/48 grid cells).

**Lesson for a future loop:** a partial de-risking (e.g. halve exposure in
mid-vol rather than fully flatten, only flatten in high-vol) might recover
the Sharpe while keeping MDD under control -- worth a follow-up sub-iteration
tuning `vol_regime_ratio` higher (less aggressive gating) or using continuous
inverse-vol sizing instead of a binary flatten, consistent with this repo's
successful EWMA/Parkinson/Garman-Klass/Rogers-Satchell vol-targeting overlay
pattern (accepted this same cron trigger, ids 2026-09-17-050/051/052/053/058).
