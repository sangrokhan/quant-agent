# Backtest Report: Apirine Rate Of Change With Bands (ROCWB) Reversal Confirmation

**Strategy file:** `strategies/2026-09-17_rocwb_reversal_confirmation.py`
**Source:** Traders.com Mar 2021 Traders' Tips (Vitali Apirine, "Rate Of
Change With Bands", TASC Mar 2021), TradeStation EasyLanguage code, read via
`browser_exec` this iteration --
`https://traders.com/Documentation/FEEDbk_docs/2021/03/TradersTips.html`.

## Hypothesis

MA-ROC (EMA of raw rate-of-change) with bands whose width is the RMS
(root-mean-square) of the RAW rate-of-change series -- distinct from every
prior plain-ROC/z-score-ROC strategy in this repo (which normalize with
mean+stdev). In an uptrend (close > EMA200), MA-ROC crossing UP through the
(negative) LowerBand marks a momentum-exhaustion recovery -- a
reversal-confirmation long entry rather than a simple dip-buy. Exit on
MA-ROC crossing down through UpperBand or trend regime flip.

## Grid test (Step 6)

`periods1` in [8,12,18] x `num_dev_dn` in [-0.8,-1.0,-1.3] x
`max_hold_days` in [15,30,45], symbols QQQ/SPY (equity) + BTC/USDT,
ETH/USDT (crypto), vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells.

- **pass_fraction: 0.176** (57/324) -- lower than typical for this repo
- by_asset_class: equity 51/162 (0.315), crypto 6/162 (0.037)
- by_vol_regime: low 13/108 (0.120), mid 23/108 (0.213), high 21/108 (0.194)
  -- notably this strategy favors MID/HIGH vol over low-vol (opposite of
  most strategies tested this trigger), consistent with the mechanic being
  specifically about momentum-spike exhaustion/recovery, which is more
  frequent and meaningful during volatile periods.
- No grid cell passed all 3 vol-regime terciles cleanly.

## Single-config validation (Step 7)

### QQQ, periods1=18, num_dev_dn=-1.3, max_hold_days=20 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.340 (threshold 1.0) |
| Max drawdown | **PASS** | 0.074 |
| Transaction cost survival (14 trades) | **PASS** | net Sharpe 1.302 |
| Walk-forward (4 manual equal splits -- `check_walk_forward` in validators.py broken: `vectorbt.utils.splitting` missing; computed manually) | **PASS** (all positive) | [0.443, 2.421, 0.728, 0.564] |
| Parameter sensitivity (periods1 in [15,18,21]) | **PASS** | relative_std 0.171; Sharpes [0.878, 1.340, 1.104] |

**Verdict: ACCEPT for QQQ.** Low but adequate trade count (14 over 7.5
years, ~1.9/year -- consistent with a reversal-confirmation signal being
relatively rare).

### SPY, periods1=12, num_dev_dn=-1.5, max_hold_days=20 -- REJECTED (fragile)

Full-sample Sharpe 1.154 with MDD 0.047 initially looked promising, but:
- Only **9 trades** over 7.5 years (~1.2/year), a thin sample.
- Parameter sensitivity around periods1=12 is a narrow spike: periods1=10
  gives Sharpe 0.206, periods1=14 gives 0.676, periods1=12 gives 1.154 --
  relative_std 0.570, barely under the 0.6 threshold but visibly a
  fragile local peak rather than a robust plateau.

**Verdict: REJECT for SPY** -- thin sample + fragile parameter sensitivity
despite technically passing the numeric threshold; not trustworthy enough
to accept alongside the more robust QQQ config.

### Crypto (BTC/USDT, ETH/USDT)

Grid pass_fraction for crypto was 0.037 (6/162). **Rejected decisively.**

## Overall decision

**ACCEPTED, QQQ only**: periods1=18, num_dev_dn=-1.3, max_hold_days=20. SPY
rejected (fragile/thin sample despite passing headline metrics). Crypto
rejected decisively. Notably this strategy favors mid/high-vol regimes,
opposite of most other strategies tested this trigger -- flagged as a
potentially useful diversifying signal for a future portfolio-combination
loop.
