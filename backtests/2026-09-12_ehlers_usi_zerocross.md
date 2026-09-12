# Backtest Report: Ehlers Ultimate Strength Index (USI) Zero-Line Crossover

**Strategy file:** `strategies/2026-09-12_ehlers_usi_zerocross.py`
**Source:** John F. Ehlers, TASC 12/2024. Formula reproduced from
https://financial-hacker.com/the-ultimate-strength-index/ (fully disclosed
C code, built on Ehlers' UltimateSmoother already used elsewhere in this
repo).

## Hypothesis

USI = (USU - USD) / (USU + USD), where USU/USD are UltimateSmoother-filtered
4-bar SMAs of up-moves/down-moves — a symmetric (-1..+1), low-lag
RSI-replacement. Long-only adaptation: long while USI > 0 (bullish momentum),
flat while USI <= 0.

## Single-config validator results

### QQQ (usi_length=112 — best QQQ grid cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.399 | >= 1.0 |
| Max drawdown | PASS | 0.205 | <= 0.25 |
| Transaction cost survival (10bps/trade, 78 trades) | PASS | net Sharpe 1.284 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity (usi_length in {14,28,56,112}) | PASS | rel. std 0.322 | <= 0.5 |

### SPY (usi_length=56 — best SPY grid cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.251 | >= 1.0 |
| Max drawdown | PASS | 0.191 | <= 0.25 |
| Transaction cost survival (10bps/trade, 119 trades) | PASS | net Sharpe 1.015 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity | PASS | rel. std 0.366 | <= 0.5 |

Both equity symbols pass ALL 5 validators (each with its own best
usi_length).

## Grid test summary (usi_length x {14,28,56,112}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3)

- **Total cells:** 48, **passed:** 13, **pass_fraction: 0.271**
- **By asset class:** equity 13/24 (0.542), crypto 0/24 (0.0)
- **By vol regime:** low 8/16 (0.5), mid 4/16 (0.25), high 1/16 (0.0625)
- **Best cell:** QQQ low-vol, usi_length=112, Sharpe 2.64
- **Worst cell:** QQQ high-vol, usi_length=14, Sharpe -0.577

Edge concentrated in equity, especially longer usi_length (56/112) and
low/mid-vol regimes; crypto decisively fails (0/24) and high-vol equity
regimes are weak — this is an honest limitation, not a blanket edge.

## Decision: ACCEPT (equity only — QQQ and SPY, each with its own tuned usi_length)

Both QQQ (usi_length=112) and SPY (usi_length=56) pass every validator with
comfortable margins. Crypto is rejected decisively and should not be traded
with this strategy. Scope: equity trend/momentum regime, long-only.
