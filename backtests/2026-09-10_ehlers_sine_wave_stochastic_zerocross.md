# 2026-09-10 — Ehlers Sine Wave Stochastic, Zero-Line-Cross Confirmation (REJECTED, QQQ near-miss)

## Hypothesis

Per https://stonehillforex.com/2026/08/ehlers-sine-wave-stochastic-as-a-confirmation-indicator/:
a stochastic-based variant inspired by John Ehlers' digital-signal-
processing philosophy. Fast (green) and slow (gold) smoothed stochastic
lines from a StoPeriod=32/StoSmoothing=5/StoPrice=Close stochastic. Source
discloses two confirmation methods: two-line crossover (earlier, noisier)
and zero-line cross of the fast line (more conservative, stronger). This
implementation uses the zero-line-cross variant, approximated as a
StoSmoothing-period SMA of the raw %K stochastic crossing above/below its
own natural 50 centerline (source's underlying smoothing formula for the
actual Sine Wave lines wasn't fully disclosed, only settings and crossover
logic).

Strategy file: `strategies/2026-09-10_ehlers_sine_wave_stochastic_zerocross.py`

## Grid summary (sto_period in [21,32,50] x sto_smoothing in [3,5,8], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 24/108 cells passed (pass_fraction 0.222), all 24 on equity — crypto 0/54 decisively.
- By vol regime: low 17/36, mid 5/36, high 2/36 — edge concentrated in low-vol equity.
- Best cell: QQQ, sto_period=21, sto_smoothing=8, low-vol tercile, Sharpe 1.71.
- Worst cell: BTC/USDT, sto_period=50, sto_smoothing=8, mid-vol tercile, Sharpe 0.06.

## Single-config validators (sto_period=21, sto_smoothing=8, full sample 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.812 (FAIL, thr 1.0) | 0.229 (pass, thr 0.25) | 0.743 (pass) | 0.75 pass_fraction (pass; 3/4 splits) | rel_std 0.106 (pass) |
| SPY | 0.611 (FAIL) | 0.146 (pass) | 0.529 (pass, barely) | 0.75 pass_fraction (pass; 3/4 splits) | rel_std 0.200 (pass) |

Walk-forward used a manual 4-split RangeSplitter (vectorbt.utils.splitting
unavailable, same known repo-wide workaround as many prior entries).

## Decision: REJECT (QQQ is a moderate near-miss)

QQQ fails only Sharpe (0.812 vs 1.0, an 18.8% shortfall — not as tight as
some other near-misses in this repo but still the only failing validator).
All other validators (MDD, TC-survival, walk-forward, parameter sensitivity)
pass cleanly with low parameter sensitivity (rel_std 0.106), suggesting the
config isn't overfit even though it falls short. SPY fails Sharpe more
decisively (0.611). Crypto rejected decisively across the whole grid (0/54
cells) — the stochastic-zero-cross construction doesn't translate to
crypto's volatility regime. Worth a lighter-touch follow-up (e.g. an
uptrend filter or a min-hold gate) in a future loop given the low parameter
sensitivity on QQQ.
