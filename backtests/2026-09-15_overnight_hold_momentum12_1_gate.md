# 2026-09-15 Overnight-Hold Gated by 12-1 Skip-Month Momentum

**Hypothesis:** Per Lou/Polk/Skouras "A Tug of War: Overnight Versus
Intraday Expected Returns" (summarized at
https://alphaarchitect.com/overnight-momentum-vs-intraday-momentum/),
momentum strategy abnormal returns accrue almost entirely overnight. This
strategy holds QQQ/SPY overnight only (close->open, flat intraday), gated
by whether 12-1 skip-month momentum (Jegadeesh-Titman convention) is
positive as of the prior close.

**Source:** https://alphaarchitect.com/overnight-momentum-vs-intraday-momentum/
(paper: Lou, Polk, Skouras, "A Tug of War: Overnight Versus Intraday
Expected Returns")

**Primary config:** lookback_months=12, skip_months=1, mom_threshold=0.0,
bars_per_month=21

## Single-config validator results

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | 1.206 (pass, thr 1.0) | 0.274 (**FAIL**, thr 0.25) | 1.181 (pass) | 1.0 (pass) | 0.060 (pass) |
| SPY | 0.781 (**FAIL**, thr 1.0) | 0.294 (**FAIL**, thr 0.25) | 0.742 (pass) | 1.0 (pass) | 0.072 (pass) |

## Grid summary (lookback_months in [12,10] x skip_months in [1,0] x
mom_threshold in [0.0, 0.02], QQQ/SPY/BTC-USDT/ETH-USDT x low/mid/high vol
tercile, 96 cells total)

- pass_fraction: 0.396 (38/96)
- by_asset_class: equity 32/48 passed; crypto 6/48 passed
- by_vol_regime: low 16/32; mid 22/32; high 0/32 (strategy decisively fails
  in high realized-vol regimes across every param combo/asset)
- best_cell: QQQ, lookback=12/skip=0/mom_threshold=0.02, low-vol regime,
  Sharpe 2.68
- worst_cell: BTC/USDT, lookback=10/skip=0/mom_threshold=0.02, mid-vol
  regime, Sharpe -0.78

## Outcome: REJECTED (both QQQ and SPY on the primary/full-sample config)

QQQ fails max-drawdown (0.274 vs 0.25 threshold) despite passing every
other validator -- a genuine near-miss. SPY fails both Sharpe (0.781) and
MDD (0.294). The grid confirms the strategy only works in low/mid
volatility regimes (0/32 high-vol passes across the board) -- the
overnight-hold, unlike a full intraday+overnight trend-following exposure,
has no mechanism to de-risk during high-vol overnight gap risk, which is
exactly what likely drives the full-sample MDD breach (the QQQ full-sample
MDD-relevant drawdown is plausibly concentrated in a high-vol period like
2022 or the 2020 COVID crash).

Crypto (BTC/USDT, ETH/USDT) fails decisively (6/48 grid passes) -- 24/7
markets have no discrete "overnight" session boundary in the same sense,
so the close->next-open window is somewhat arbitrary for crypto; this
strategy family should be considered equity-only going forward.

**Follow-up direction for a future iteration:** add a volatility regime
gate (flat overnight during high-vol regimes, following this repo's
established pattern from 2026-09-03-001) to see if it rescues the QQQ MDD
near-miss and SPY's shortfall, similar to how 2026-09-08-053's trend-filter
addition improved on the plain unconditional overnight hold.
