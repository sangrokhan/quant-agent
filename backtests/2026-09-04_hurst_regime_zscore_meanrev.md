# Hurst Exponent Regime-Gated Z-Score Mean Reversion (QQQ) — REJECTED

**Hypothesis:** Rolling Hurst exponent H (R/S analysis): H < hurst_threshold
(anti-persistent/mean-reverting regime) should make a z-score mean-reversion
entry (close z-score < -entry_z_threshold vs its own 20d SMA/STD) more
reliable, directly addressing why the plain (regime-unaware) z-score
mean-reversion strategy (2026-09-04-082) was rejected across all symbols —
this is the theoretically-motivated inverse pairing of the trend-following
x high-Hurst strategy (2026-09-04-155, also rejected), testing whether the
Hurst-regime CONCEPT works better paired with a mean-reversion base signal
instead.

**Source:** Combination of two already-cited sources: Hurst-exponent
regime concept from https://fractalcycles.com/guides/hurst-exponent-explained
(2026-09-04-155) and the plain z-score mean-reversion base rule from
changelly.com (2026-09-04-082). No new external research this iteration —
this is a direct novelty-motivated recombination flagged as a "future loop"
idea in 2026-09-04-155's own notes field.

**Novelty:** Same Hurst estimator as 2026-09-04-155 but inverted threshold
direction (H < threshold instead of H > threshold) and paired with
mean-reversion instead of trend-following — distinct combination not
previously tested.

## Best config: hurst_window=100, hurst_threshold=0.5, zscore_window=20, entry_z_threshold=1.5, max_hold_days=10 (QQQ, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.432 | >= 1.0 | **FAIL** |
| Max drawdown | 10.98% | <= 25% | PASS |
| Transaction cost survival (5bps/trade, 46 trades) | net Sharpe 0.389 | >= 0.5 | **FAIL** |
| Walk-forward | SKIPPED | n/a | Repo-wide `vectorbt.utils.splitting` API issue, see 2026-09-04-154 |
| Parameter sensitivity | not computed | n/a | Grid pass_fraction already decisive (4.2%), skipped for time budget |

## Step 6 grid summary (hurst_threshold in [0.4,0.45,0.5] x entry_z_threshold in [1.5,2.0], symbols QQQ/SPY equity + BTC/ETH crypto, vol_regime_splits=3)

- **Overall pass_fraction: 4.2%** (3/72 cells) — weaker than the trend-following x high-Hurst pairing (18.1%, 2026-09-04-155).
- **By asset class:** equity 3/36 (8.3%); crypto 0/36 (0%).
- **By vol regime:** low 0/24, mid 1/24, high 2/24 — the few passes cluster in high-vol, opposite of where a cautious mean-reversion-only-when-anti-persistent strategy might be expected to help most (low-vol, range-bound conditions).
- **Best cell:** QQQ, hurst_threshold=0.5, entry_z_threshold=1.5, high-vol regime, Sharpe 1.36 (single favorable slice); worst cell same config, mid-vol regime, Sharpe -1.21 — high variance across regimes even for the "best" param combo.

## Decision: REJECT

Confirms the inverse-pairing idea does not rescue the Hurst-regime concept:
full-sample QQQ Sharpe (0.43) and net-of-cost Sharpe (0.39) both miss
thresholds, and the grid pass_fraction (4.2%) is markedly weaker than even
the already-rejected trend-following pairing (18.1%, 2026-09-04-155). Both
the H>threshold-with-trend-following and H<threshold-with-mean-reversion
pairings are now rejected for this repo's Hurst estimator/parameter
ranges; the Hurst-regime concept itself does not appear to add exploitable
value here — a future loop should treat "Hurst exponent regime gating" as
a closed line of inquiry for QQQ/SPY/BTC/ETH daily bars unless a
substantially different estimator (e.g. DFA instead of R/S) or a
different base signal family is tried.
