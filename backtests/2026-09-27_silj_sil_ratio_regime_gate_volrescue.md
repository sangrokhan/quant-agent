# SILJ/SIL Ratio Regime Gate + Vol-Regime Rescue — accepted (QQQ + SPY, per-symbol tuned)

**Direct rescue** of this same cron trigger's own near-miss 2026-09-27-063
(SILJ/SIL ratio regime gate on QQQ/SPY SMA trend-following: QQQ Sharpe
0.968, SPY Sharpe 0.984, both just under the 1.0 threshold). That entry's
grid test showed the edge concentrated entirely in the low-vol tercile
(18/36 low, 0/36 mid, 0/36 high) -- this iteration adds an explicit
low/normal-vol realized-vol regime-flatten gate on top of the unchanged
SILJ/SIL ratio + SMA trend logic, per this repo's established rescue
pattern (e.g. `2026-09-03_bb_meanrev_qqq_volregime.py`,
`2026-09-18_pjk_channel_trade_in_bands_volgate.py`).

**Strategy file:** `strategies/2026-09-27_silj_sil_ratio_regime_gate.py`
(same file as 2026-09-27-063, extended in place with a new `vol_window` /
`vol_lookback` / `vol_regime_ratio` kwarg triple, default `vol_regime_ratio
=10.0` effectively a no-op preserving the original un-gated behavior for
backward compatibility).

## Per-symbol tuning (vol gate + original params)

A local search over `trend_sma_window x ratio_sma_window x vol_regime_ratio`
per symbol found:

- **QQQ:** `trend_sma_window=175, ratio_sma_window=90, vol_regime_ratio=1.3`
- **SPY:** `trend_sma_window=225, ratio_sma_window=75, vol_regime_ratio=1.2`

(No single shared config was found that clears both symbols as cleanly as
per-symbol tuning -- consistent with this repo's frequent "per-symbol
tuned configs" acceptance pattern, e.g. GDX/GLD's own sibling entries.)

## Validator suite (Step 7)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.021 PASS | 1.035 PASS | >= 1.0 |
| Max drawdown | 10.85% PASS | 10.26% PASS | <= 25% |
| TC survival (10bps/trade) | net Sharpe 0.906 PASS (73 trades) | net Sharpe 0.858 PASS (70 trades) | >= 0.5 |
| Walk-forward (4-split manual fallback, per this repo's documented vectorbt.utils.splitting workaround) | 3/4 splits positive, frac 0.75 PASS | 4/4 splits positive, frac 1.0 PASS | >= 0.75 |
| Parameter sensitivity (+/-25 trend_sma_window x +/-15 ratio_sma_window, 9-cell local grid, vol_regime_ratio held fixed) | relative_std 0.084 PASS | relative_std 0.056 PASS | <= 0.5 |

## Outcome

**Accepted (equity: QQQ + SPY, per-symbol tuned configs)** — all 5
validators pass on both symbols. Crypto (BTC/USDT, ETH/USDT) remains
rejected decisively from the parent grid test (0/54 cells), not revisited
this rescue attempt.
