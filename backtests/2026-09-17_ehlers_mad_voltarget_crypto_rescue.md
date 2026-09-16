# 2026-09-17 — Ehlers MAD zero-line crossover + inverse-vol sizing crypto rescue

**Hypothesis:** Direct fix for 2026-09-17-061's decisive crypto rejection
(BTC/USDT MDD 58.7%, ETH/USDT MDD 43.5%, both ~2x the 25% threshold, at full
binary exposure of the MAD zero-line crossover signal). Same MAD base signal
(TASC Oct 2021 Ehlers "Cycle/Trend Analytics And The MAD Indicator", full
formula already confirmed in 2026-09-17-061), but replaces the discrete
{0,1} position with a continuous inverse-volatility scaled exposure +
no-trade rebalance buffer (this repo's standard fix pattern, per
strategies/2026-09-07_sma_trend_voltarget_buffer.py, source
https://blave.org/agent/en/learn/vol_targeting, already in this repo's
ledger -- no new external research this sub-iteration).

## Grid summary (target_vol={0.15,0.25} x vol_cap={0.5,1.0} x rebalance_buffer={0.10,0.20}, symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3, 2019-01-01 to 2026-09-01, 96 cells)

- Overall pass_fraction: 0.5625 (54/96) -- crypto jumped from 13/96 (0.135, 2026-09-17-061's binary version) to 30/48 (0.625)
- By asset class: equity 24/48, crypto 30/48
- By vol regime: low 28/32, mid 20/32, high 6/32
- Best cell: SPY low-vol Sharpe 2.80 (target_vol=0.15, vol_cap=1.0, rebalance_buffer=0.2)
- Worst cell: ETH/USDT high-vol Sharpe -0.20

## Single-best-config validators (target_vol=0.25, vol_cap=0.5, rebalance_buffer=0.2, 2018-01-01 to 2026-09-01)

| Metric | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|
| Sharpe | 1.112 | 0.866 | >=1.0 |
| Max Drawdown | 0.214 | 0.266 | <=0.25 |
| TC-adjusted Sharpe | 0.977 | 0.753 | >=0.5 |
| Walk-forward (manual 4-slice) | 1.0 | 1.0 | >=0.75 |
| Parameter sensitivity (rel std) | 0.033 | 0.059 | <=0.5 |
| **Verdict** | **PASS all 5** | FAIL Sharpe+MDD (both near-miss) |

## Verdict: ACCEPTED for BTC/USDT. REJECTED for ETH/USDT (Sharpe 0.866 vs 1.0 near-miss, MDD 26.6% vs 25% near-miss -- both close, otherwise clean on TC/walk-forward/param-sensitivity).

The inverse-vol sizing overlay dramatically improved crypto's MDD profile
(BTC/USDT 58.7% -> 21.4%, well under threshold; ETH/USDT 43.5% -> 26.6%,
just barely over). BTC/USDT now fully validated and accepted. ETH/USDT is a
double near-miss worth a future targeted fine-tune (e.g. slightly lower
target_vol or tighter vol_cap specifically for ETH).
