# Backtest Report: Pain Ratio Sizing — Crypto Leverage-Cap Recalibration Attempt (REJECTED)

**Strategy file:** `strategies/2026-09-16_pain_ratio_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16

## Hypothesis

2026-09-13-051's Pain Ratio dynamic exposure scaling on an SMA(200) trend
gate was accepted on SPY/QQQ and had BTC/USDT pass Sharpe (1.064),
TC-survival (1.046), and walk-forward (0.75) — only MDD failed decisively
at 37.57% > 25%, at leverage_cap=1.0. Unlike the sizing-dial-family
retunes this cron trigger (RWI, PFE, EFI, PPO, ER, Chaikin Osc, TMF,
Elder-Ray), which all rescued crypto cleanly by cutting leverage_cap
(their Sharpe was strong and MDD-only was the blocker), Pain Ratio's
exposure signal is NOT bounded the same way (`pain_ratio / reference`,
uncapped except by the leverage_cap clip) and crypto's Sharpe was already
marginal (1.064) rather than comfortably above 1.0.

## Attempted retunes

- `leverage_cap=0.25`: BTC/USDT Sharpe 0.949 (fail, <1.0), MDD 0.133
  (pass); ETH/USDT Sharpe 0.833 (fail), MDD 0.210 (pass). Cutting leverage
  fixed MDD but pulled Sharpe below the 1.0 threshold on both symbols.
- `leverage_cap=0.5`: BTC/USDT Sharpe 0.939 (fail), MDD 0.250 (borderline
  pass); ETH/USDT Sharpe 0.803 (fail), MDD 0.393 (fail). Raising leverage
  back up did not rescue Sharpe and reintroduced MDD failure on ETH/USDT.

Neither leverage setting produces a passing Sharpe on crypto — this is a
structural Sharpe shortfall, not the MDD-only pattern that the
leverage-cap-retune fix addresses for the sizing-dial family. Grid test at
leverage_cap in {0.25,0.3,0.35}, pain_ratio_reference in {2,3,4}: total
pass_fraction only 0.333 (18/54), concentrated in mid/high-vol regimes
with zero low-vol passes — a materially worse and narrower pattern than
the sizing-dial retunes' typical 0.83 pass_fraction this cron trigger.

## Decision (Step 8)

**Rejected (crypto, this sub-iteration)** — the leverage-cap-aware retune
pattern that rescued 8 prior sizing-dial strategies this cron trigger does
NOT generalize to Pain-Ratio-based dynamic exposure scaling, because
crypto's underlying Sharpe here is marginal rather than comfortably
passing. Strategy file kept in `strategies/` as a record of this
unsuccessful crypto-only retune attempt (equity SPY/QQQ accept from
2026-09-13-051 is unaffected and remains live).
