# Backtest Report: Ehlers Jack & Jill Adaptive/Contra-Adaptive SuperSmoother Crossover

**Strategy file:** `strategies/2026-09-12_ehlers_jack_jill_crossover.py`
**Hypothesis ID:** 2026-09-12-189
**Source:** http://www.mesasoftware.com/papers/The%20Jack%20and%20Jill%20Indicator.pdf
(John F. Ehlers, MESA Software technical paper, 2025)

## Hypothesis

"Jack" is an adaptive SuperSmoother whose period shrinks as its own
RMS-normalized rate-of-change rises (tracks price closely in volatile
moves); "Jill" is a contra-adaptive SuperSmoother whose period widens under
the same signal (stays slow, "virtually devoid of cyclic information").
Source's literal rule: Jack above Jill = uptrend, Jack below Jill =
downtrend. Long-only adaptation: long while Jack > Jill.

## Grid test (Step 6): `period0` in {10, 20, 40}, symbols QQQ/SPY (equity)
+ BTC/USDT, ETH/USDT (crypto), vol_regime_splits=3, 2019-01-01 to
2026-09-01.

- **Overall pass_fraction: 0.278** (10/36 cells, `min_sharpe=1.0`,
  `max_allowed_mdd=0.25`)
- **By asset class:** equity 10/18 passed; **crypto 0/18** (decisive fail).
- **By vol regime:** low 6/12, mid 3/12, high 1/12 -- edge concentrated in
  low-vol regimes, weakens sharply in high-vol.
- **Best cell:** QQQ, low-vol, `period0=20` (Sharpe 2.86).
- **Worst cell:** QQQ, high-vol, `period0=10` (Sharpe -0.35).
- Best average-Sharpe config per symbol (across the 3 vol terciles):
  QQQ `period0=20` avg 1.388; SPY `period0=20` avg 1.289.

## Single-config validation (Step 7), `period0=20` for both symbols

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd pass_frac | Param-sens rel.std | Trades |
|---|---|---|---|---|---|---|
| QQQ | 0.971 (**FAIL**, thr 1.0) | 0.266 (**FAIL**, thr 0.25) | 0.907 (pass, thr 0.5) | 1.00 (pass) | 0.254 (pass) | 58 |
| SPY | 1.057 (pass, thr 1.0) | 0.159 (pass, thr 0.25) | 0.973 (pass, thr 0.5) | 1.00 (pass) | 0.146 (pass) | 55 |

QQQ fails both Sharpe (narrowly, full-sample averages out the strong
low-vol-regime performance against a weaker high-vol tail) and MDD
(narrowly, 0.266 vs 0.25 threshold). SPY passes all 5 validators cleanly.
Walk-forward used the manual 4-equal-slice fallback (documented since
2026-09-03-002: `vbt.utils.splitting.RangeSplitter` broken in this
vectorbt install).

## Decision: **ACCEPT (SPY only)**, reject QQQ and crypto

QQQ full-sample metrics narrowly miss both Sharpe and MDD thresholds despite
a strong best-cell (low-vol) grid Sharpe of 2.86 -- the strategy's edge on
QQQ appears regime-concentrated and doesn't survive averaging across the
full sample/all vol regimes. SPY passes cleanly with very low parameter
sensitivity (rel.std 0.146). Crypto (BTC/USDT, ETH/USDT) rejected
decisively at the grid stage (0/18 cells).
