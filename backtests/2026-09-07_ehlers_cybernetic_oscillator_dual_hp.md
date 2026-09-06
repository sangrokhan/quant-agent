# 2026-09-07: Ehlers Cybernetic Oscillator Dual-Highpass Trend Confirmation (SPY)

## Hypothesis
Ehlers' Cybernetic Oscillator swing-trading system smooths close with a
lowpass filter, then applies a 2-pole highpass filter at two different
cutoff lengths (a short one for swings, a long one for the underlying
trend). Going long only when the 2-bar rate-of-change of BOTH
highpass-filtered series is simultaneously positive requires short-term
and long-term momentum agreement before committing; exit as soon as either
turns negative.

Source: https://financial-hacker.com/the-cybernetic-oscillator/ (TASC June
2025 Ehlers article, reproduced with full EasyLanguage-derived code and
concrete default parameters: smooth_len=20, short_hp_len=55,
long_hp_len=156, roc_lag=2). Source's own SPY 2009-2025 backtest (Zorro
platform, in-sample optimized): ~180 trades, 60% win rate, profit factor 2.

First strategy in this repo requiring two different-timescale
highpass-filtered momentum signals to agree before entry -- distinct from
all other Ehlers-family strategies already tried (Roofing Filter, Decycler
Oscillator, MESA Stochastic, Trendflex, Voss Predictive Filter, Ultimate
Smoother, Center of Gravity), none of which use a dual-cutoff highpass ROC
agreement rule.

## Strategy file
`strategies/2026-09-07_ehlers_cybernetic_oscillator_dual_hp.py`

## Grid test (Step 6)
`param_grid={"short_hp_len": [30, 55, 80], "long_hp_len": [125, 156, 200]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **108 total cells, 25 passed (pass_fraction = 0.231)**
- By asset class: **equity 25/54 passed**, crypto 0/54 (complete failure --
  highpass-filter cutoff lengths tuned to daily-equity cycle lengths don't
  transfer to crypto's different volatility/cycle structure)
- By vol regime: low 15/36 (best), mid 5/36, high 5/36 -- edge concentrated
  in low-vol regimes
- Best cell: source's own default params (`short_hp_len=55,
  long_hp_len=156`), SPY, low-vol regime, Sharpe 2.196
- Worst cell: `short_hp_len=30, long_hp_len=125`, BTC/USDT, low-vol regime,
  Sharpe -0.218

## Single-config validation (Step 7) — source's own default params (`short_hp_len=55, long_hp_len=156`)

### SPY (full sample, 2019-2026)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ PASS | 1.043 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 0.153 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 124 trades) | ✅ PASS | 0.773 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback -- `vbt.utils.splitting` repo-wide bug) | ✅ PASS | 4/4 splits positive | ≥ 0.75 |
| Parameter sensitivity (9-combo grid) | ✅ PASS | relative_std 0.119 | ≤ 0.5 |

**All 5 validators pass on SPY.**

### QQQ (same params, for comparison — NOT part of the accepted scope)

| Validator | Result | Value |
|---|---|---|
| Sharpe ratio | ❌ FAIL | 0.624 |
| Max drawdown | ❌ FAIL | 0.299 |
| Transaction cost survival | ❌ FAIL | 0.447 |

QQQ fails decisively on the same config -- the strategy's edge does not
transfer even within equities to a higher-vol/higher-beta index, consistent
with the grid's own "edge concentrated in low-vol regime" finding.

## Decision: ACCEPT — SPY only, low/mid-vol-tilted equity scope

All 5 validators pass cleanly for SPY with the source's own default
parameters (no cherry-picked tuning). Kept as a live strategy in
`strategies/`, scoped explicitly to SPY (or similarly low-beta broad
equity indices) — NOT validated for QQQ or crypto, both of which fail
decisively on the grid and single-config check. A future loop should not
assume this generalizes beyond SPY-like low-vol-regime equity exposure.
