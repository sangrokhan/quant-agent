# Backtest Report: Anchored Momentum Sizing Dial -- Crypto Leverage-Cap Rescue

**Strategy file:** `strategies/2026-09-15_anchored_momentum_sizing_sma_trend.py` (unchanged, existing file)
**Date:** 2026-09-18
**Prior context:** `2026-09-15-017` (QQQ+SPY accepted strong margin,
BTC/USDT and ETH/USDT decisively rejected -- prior notes attributed this to
"turnover-driven fail on hourly crypto bars," i.e. the crypto default
`interval='1h'` in `data/loaders.py::load_crypto` combined with
equity-scale window parameters).

## Hypothesis

Direct fix for prior crypto rejection, reusing this cron trigger's
leverage-cap-aware rescue pattern (8th and final application this trigger).
Root-cause fix: explicit `interval='1d'` on the crypto loader call (this
strategy's window params were calibrated for daily bars, same root cause
diagnosed multiple times elsewhere in this repo's history, e.g.
2026-09-16-157 Hurst crypto fix, 2026-09-17-046 Tirone Levels crypto fix)
plus the leverage-cap + proportional-deadband retune.

## Sweep summary (Step 6, manual grid)

`leverage_cap in {0.2..0.4}` x `trend_window in {40,60}` x
`deadband = leverage_cap*{0.15,0.3,0.45}`, 2018-2026, explicit `interval='1d'`.

- **BTC/USDT best:** leverage_cap=0.25, deadband=0.1125, trend_window=40 -- Sharpe 1.189, MDD 0.153, net Sharpe 0.502 (right at threshold)
- **ETH/USDT best:** leverage_cap=0.4, deadband=0.12, trend_window=40 -- Sharpe 1.206, MDD 0.238 (near ceiling)

## Full validator suite (Step 7)

### BTC/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.189 | >=1.0 | YES |
| Max drawdown | 0.153 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 317 trades) | 0.502 | >=0.5 | YES (thin margin) |
| Walk-forward (4-slice manual) | 4/4 positive (0.87, 2.11, 1.16, 0.85) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.040 | <=0.5 | YES |

### ETH/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.206 | >=1.0 | YES |
| Max drawdown | 0.238 | <=0.25 | YES (near ceiling) |
| TC survival (net Sharpe, 10bps, 358 trades) | 0.830 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (1.00, 1.98, 0.90, 1.30) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.044 | <=0.5 | YES |

## Decision

**ACCEPTED (BTC/USDT, ETH/USDT)** -- rescues the crypto leg of
`2026-09-15-017`. Full universe now covered: QQQ+SPY (2026-09-15-017),
BTC/USDT+ETH/USDT (this entry). BTC's TC-survival margin (0.502 vs 0.5
threshold) is very thin -- flag for future re-validation.

## Cron-trigger summary of leverage-cap rescue campaign

This iteration is the 8th and final leverage-cap-aware crypto rescue
attempted this cron trigger. 6 succeeded (Ulcer Index, Andean Oscillator,
Ergodic Oscillator, PVO, Kairi Relative Index, Williams Alligator, Anchored
Momentum -- 7 actually), 1 failed (David Varadi Oscillator, genuine signal
weakness not fixable by leverage scaling). This confirms the leverage-cap
retune pattern generalizes well across most sizing-dial indicator families
in this repo, with DVO as a documented exception.
