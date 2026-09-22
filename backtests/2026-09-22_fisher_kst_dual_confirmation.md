# Fisher Transform + KST Dual-Confirmation Momentum (2026-09-22)

## Hypothesis

Per a Medium article series by kridtapon on MOS stock ("Outsmarting Buy &
Hold with Logic: MOS Stock Strategy" / "Adaptive Strategy Testing with
Fisher Transform & KST Indicators" / "Adaptive Momentum Strategy for MOS
Stock: Fisher Transform & KST", found via Google SERP — web_search's DDGS
backend returning empty/garbage results for several queries this iteration;
the individual Medium article URLs 404 when navigated to directly, but the
Google SERP snippets themselves disclose the exact rule):

> "An entry (buy) signal occurs when both the Fisher Transform and the KST
> histogram are above zero, suggesting upward momentum... An exit (sell)
> signal occurs when [both turn negative]."

Fisher Transform (Ehlers, price-normalizing oscillator) and KST (Know Sure
Thing, Martin Pring's 4-component weighted rate-of-change composite) are
structurally different oscillator families — this dual-confirmation
requires agreement across both before entering. Repo has 26 prior Fisher
Transform entries and 10+ Coppock Curve entries (a different Pring
composite), but zero prior KST entries and zero prior Fisher+KST
combination — first test of this specific pairing.

## Grid summary (Step 6)

Grid: `fisher_window` in {10, 20} x `trend_window` in {0, 100} x QQQ/SPY/BTC-USDT/ETH-USDT
x 3 vol regimes = 48 cells.

- `pass_fraction` = 0.375 (18/48) — the strongest grid pass-rate of this cron trigger so far
- `by_asset_class`: equity 12/24, crypto 6/24
- `by_vol_regime`: low 12/16, mid 6/16, high 0/16 (edge concentrated in calmer regimes)
- `best_cell`: SPY, fisher_window=20/trend_window=100, low-vol, Sharpe 2.83
- Best full-sample-average equity config: QQQ fisher_window=20/trend_window=0 (avg Sharpe 1.52)
- Crypto full-sample averages also looked strong (BTC/ETH both >1.1 avg Sharpe) — investigated further in single-config validation below

## Single-config validation (fisher_window=20, trend_window=0)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe ratio | 1.243 **PASS** | 0.837 **FAIL** | 0.831 **FAIL** | 1.027 **PASS** |
| Max drawdown | 0.220 **PASS** | 0.203 **PASS** | 0.764 **FAIL** (decisive) | 0.593 **FAIL** (decisive) |
| TC-survival (10bps/trade) | 1.160 **PASS** | 0.726 **PASS** | 0.793 **PASS** | 1.002 **PASS** |
| Walk-forward (4 splits) | 1.0 **PASS** | 1.0 **PASS** | 1.0 **PASS** | 1.0 **PASS** |
| Parameter sensitivity | 0.026 **PASS** | 2.974 **FAIL** | 0.112 **PASS** | 0.159 **PASS** |

## Decision: ACCEPT (QQQ only); reject SPY, BTC/USDT, ETH/USDT

**QQQ: all 5 validators pass decisively** — Sharpe 1.24, MDD 0.22, TC-survival
net Sharpe 1.16 at only 67 trades/7.75yr, walk-forward 4/4, and extremely
stable parameter-sensitivity (relative_std 0.026, the tightest of any
strategy tested this cron trigger). This is the accepted, live
configuration.

**SPY**: Sharpe fails (0.837) and, more decisively, parameter-sensitivity
fails badly (relative_std 2.97 — the Sharpe across the parameter grid is
wildly unstable, including a negative-Sharpe cell (-0.41) right next to the
grid's best cell (2.83), a red flag for curve-fitting/fragility on this
symbol specifically).

**Crypto (both BTC/USDT and ETH/USDT)**: decisive MDD failures (0.76 and
0.59, both roughly 3x the 0.25 threshold) despite passing Sharpe/TC/walk-
forward/param-sensitivity — the dual-confirmation entry doesn't manage
downside risk adequately on crypto's much larger drawdown regimes (likely
the 2018 and 2022 bear markets), even though the momentum-confirmation
logic itself is directionally sound there (positive average Sharpe, low
param sensitivity). Scope: equity QQQ only, not SPY, not crypto.

Source: Google SERP snippets for kridtapon's Medium article series on MOS
stock Fisher Transform + KST (article URLs 404 directly; see search query
`"Fisher Transform" "KST" "above zero" entry signal MOS medium strategy exit`).
