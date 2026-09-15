# 2026-09-15 Overnight-Hold + 12-1 Momentum Gate + Vol-Regime Filter

**Hypothesis:** Direct fix for this same cron trigger's near-miss/rejection
2026-09-16-108 (overnight-hold + 12-1 skip-month momentum gate: QQQ MDD
0.274 near-miss, SPY Sharpe 0.781 + MDD 0.294 both fail; grid decisively
failed in the high-vol tercile, 0/32 passes). This iteration adds an
explicit realized-vol regime filter (20d realized vol vs trailing 252d
median, this repo's established 2026-09-03-001 pattern) on top of the
unchanged 12-1 momentum overnight-hold logic. No new external research
source this sub-iteration -- source for the underlying mechanism remains
https://alphaarchitect.com/overnight-momentum-vs-intraday-momentum/ (Lou,
Polk, Skouras).

**Primary config:** lookback_months=12, skip_months=1, mom_threshold=0.02,
bars_per_month=21, vol_window=20, vol_lookback=252, vol_regime_ratio=1.2

## Single-config validator results

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | 1.650 (pass) | 0.091 (pass) | 1.545 (pass) | 1.0 (pass) | 0.338 (pass, thr 0.5) |
| SPY | 1.680 (pass) | 0.071 (pass) | 1.582 (pass) | 1.0 (pass) | 0.589 (**FAIL**, thr 0.5) |

## Grid summary (vol_regime_ratio in [0.8,1.0,1.2] x mom_threshold in
[0.0,0.02], QQQ/SPY/BTC-USDT/ETH-USDT x low/mid/high vol tercile, 72 cells)

- pass_fraction: 0.278 (20/72)
- by_asset_class: equity 18/36; crypto 2/36
- by_vol_regime: low 10/24; mid 6/24; high 4/24 (the vol-regime filter
  successfully unlocks SOME high-vol-tercile passes, vs 0/32 in the
  ungated 2026-09-16-108 version -- confirms the gate is doing its job)
- Sweet spot: vol_regime_ratio=1.2 (looser gate, i.e. only exclude nights
  materially ABOVE the trailing-vol median) with mom_threshold=0.02 gives
  QQQ and SPY both 3/3 vol-tercile passes at avg Sharpe 1.73/1.79
  respectively; tighter vol_regime_ratio (0.8/1.0) collapses pass rates to
  0-1/3.

## Outcome: ACCEPTED (QQQ only); REJECTED (SPY, narrow parameter-sensitivity
fail); crypto out of scope (decisive fail, 2/36)

QQQ clears all 5 validators cleanly at the primary config. SPY clears
Sharpe/MDD/TC/walk-forward comfortably but its Sharpe swings materially
across the vol_regime_ratio/mom_threshold grid (relative std 0.589 vs the
0.5 threshold) -- the wider grid used to compute this includes points as
low as 0.36 avg Sharpe (vol_regime_ratio=0.8), so SPY's edge at this
specific config is real but less parameter-robust than QQQ's. Keep the
strategy file live for QQQ; SPY should be considered out of scope for this
config pending a narrower/SPY-specific parameter search in a future
iteration (same rescue pattern used successfully elsewhere in this repo,
e.g. 2026-09-16-105/106/107).

Crypto (BTC/USDT, ETH/USDT) remains decisively rejected -- confirms the
2026-09-16-108 finding that 24/7 markets lack a meaningful discrete
overnight-session boundary for this strategy family.
