# 2026-09-23 — Protective Asset Allocation (PAA) Graduated Crash-Protection Weight

## Hypothesis

Per Keller & Keuning's PAA paper, summarized by Allocate Smartly
(https://allocatesmartly.com/protective-asset-allocation/, read via
browser_exec this iteration — web_search DDGS/Yahoo backend TLS-errored on
every query attempted): monthly MOM=(close/SMA(13mo))-1 across a 12-asset
global universe; n=count with MOM>0; if n<=6, 100% crash-protection asset;
else CP%=(12-n)/6, remainder split equally among the top-6 MOM assets.
Adapted to this repo's single-asset contract: the primary traded asset
(QQQ or SPY) is held at weight=(1-CP%)/6 whenever it is both MOM-positive
and in the cross-sectional top-6 of the 12-asset universe (SPY, QQQ, IWM,
VGK, EWJ, EEM, VNQ, DBC, GLD, HYG, LQD, TLT), else flat.

Source URL: https://allocatesmartly.com/protective-asset-allocation/

## Light-workload screening result (suggested_workload=light per gate)

| symbol | mom_months | full-sample Sharpe | full-sample MDD |
|---|---|---|---|
| QQQ | 10 | 0.621 | 0.036 |
| QQQ | 13 | 0.375 | 0.039 |
| SPY | 10 | 0.515 | 0.045 |
| SPY | 13 | 0.395 | 0.047 |

All 4 cells (2 symbols × 2 lookback windows, the source's own disclosed
13-month lookback plus a 10-month variant per the Faber-family convention
already used elsewhere in this repo) miss the min_sharpe=1.0 threshold
decisively, and by a wide/consistent margin — this is not a near-miss.

MDD is very low (3.6%-4.7%) because the single-asset adaptation is only
invested a small fraction of the time (the primary asset rarely lands in
the cross-sectional top-6 of a 12-asset universe that includes commodities,
gold, and bonds which frequently outrank equities on 10-13mo momentum), so
low absolute drawdown comes at the cost of very low realized Sharpe — the
graduated crash-protection weighting does not translate into a useful
single-asset trading signal without the full 12-asset diversified portfolio
this repo's single-symbol architecture cannot represent.

## Decision: REJECTED (no full grid/validator suite run — decisive full-sample
Sharpe miss across all 4 screening cells makes further validation
uninformative per RESEARCH_LOOP.md Step 7's light-workload guidance)

Rejected at the light-workload full-sample screening stage. All 4 cells
missed Sharpe >= 1.0 by 0.4-0.6 with no cell close to passing.
