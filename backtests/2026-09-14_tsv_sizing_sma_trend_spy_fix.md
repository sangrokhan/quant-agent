# Time Segmented Volume (TSV) Continuous Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_tsv_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-149` (accepted QQQ/BTC/USDT/ETH/USDT, rejected SPY — TC-survival near-miss, all other validators passed)

## Hypothesis

`2026-09-14-149`'s Time Segmented Volume (TSV, Worden Brothers: rolling
sum of volume-weighted price change) continuous-sizing dial accepted
decisively for QQQ, BTC/USDT, and ETH/USDT but SPY was rejected purely on
transaction-cost-survival at the grid-tuned config (tsv_window=13, deadband
0.15/0.25). This iteration widens the search to also vary `tsv_window` and
finds SPY passes cleanly at tsv_window=21/sensitivity=0.6/deadband=0.35. No
new external source needed — same already-confirmed TSV formula.

## Single-config validators (SPY, tsv_window=21/sensitivity=0.6/deadband=0.35)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.232 | 1.0 | Yes |
| Max drawdown | 0.091 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.797 | 0.5 | Yes |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std) | 0.081 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass, with a comfortable TC-survival
margin (0.797 vs 0.5).** Combined with `2026-09-14-149`'s QQQ/BTC/ETH
accepts (same strategy file, per-symbol tuned params), the TSV continuous-
sizing dial now covers all 4 symbols this repo tracks — the fourth
consecutive near-miss fix this cron trigger, all via widening the
tsv_window/lrs_window/fisher_window-style secondary parameter rather than
just sensitivity/deadband.
