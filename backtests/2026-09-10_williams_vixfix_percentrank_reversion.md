# 2026-09-10 — Williams VIX Fix PercentRank Capitulation-Spike Mean Reversion (ACCEPTED, QQQ only)

## Hypothesis

Per https://www.quantifiedstrategies.com/williamsvixfix/ (Larry Williams,
2007): the Williams VIX Fix (WVF) is a synthetic, instrument-agnostic VIX
proxy, WVF = (Highest(Close, wvf_window) - Low) / Highest(Close, wvf_window)
* 100. The source's own disclosed long strategy: enter long when WVF's own
PercentRank over a short lookback exceeds an extreme threshold (source
default rank_lookback=10, entry_percentile=98, i.e. WVF is in the top 2% of
its own recent range — a capitulation spike just occurred), exit on the very
next close that's higher than the prior close. Source's own backtest: 366
trades, avg 0.44%/trade, profit factor 1.78. This implementation follows the
source's rule directly with a max_hold_days backstop added (source's own
exit could theoretically hold indefinitely with no up-day). First Williams
VIX Fix strategy in this repo.

Strategy file: `strategies/2026-09-10_williams_vixfix_percentrank_reversion.py`

## Grid summary (rank_lookback in [10,20,50] x entry_percentile in [95,98], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 18/72 cells passed (pass_fraction 0.25), all 18 on equity — crypto 0/36 decisively.
- By vol regime: low 2/24, mid 4/24, high 12/24 — as expected for a
  volatility-capitulation-spike strategy, edge concentrated in the HIGH-vol
  tercile (opposite pattern from most mean-reversion strategies in this repo
  that concentrate in low-vol).
- Best cell: QQQ, rank_lookback=20, entry_percentile=95, high-vol tercile, Sharpe 2.34.
- Worst cell: QQQ, rank_lookback=50, entry_percentile=98, low-vol tercile, Sharpe -0.43.

## Single-config validators (rank_lookback=20, entry_percentile=95.0, full sample 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.514 (pass, thr 1.0) | 0.076 (pass, thr 0.25) | 1.128 (pass, thr 0.5) | 1.00 pass_fraction (pass, thr 0.75; 4/4 splits positive) | rel_std 0.157 (pass, thr 0.5) |
| SPY | 0.878 (FAIL, thr 1.0) | 0.167 (pass) | 0.611 (pass) | 0.75 pass_fraction (pass; 3/4 splits positive, only earliest 2017-2019 split negative) | rel_std 0.122 (pass) |

Walk-forward used a manual 4-split RangeSplitter (vectorbt.utils.splitting
unavailable in the installed vectorbt version, same known repo-wide
workaround as many prior entries).

## Decision: ACCEPT (QQQ-only scope)

QQQ passes all 5 validators cleanly (Sharpe 1.51, MDD 7.6%, robust across all
4 walk-forward splits, low parameter sensitivity). SPY is a genuine near-miss
— only Sharpe fails (0.878 vs 1.0 threshold, ~12% shortfall), every other
validator passes including walk-forward and transaction-cost survival, so
this is a real candidate for a future loop's parameter-tweak follow-up (e.g.
a slightly tighter/wider percentile or a trend filter) rather than a dead
end. Crypto rejected decisively across the whole grid (0/36 cells) —
consistent with several other threshold/percentile-based mean-reversion
strategies in this repo failing on crypto's different volatility structure.
Scope: QQQ only, edge concentrated in high-vol regime cells (as expected for
a capitulation-spike strategy) — record this explicitly for future loops.
