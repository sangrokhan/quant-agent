# RESEARCH_LOOP.md — Procedure for the Research Agent LLM turn

This is the step-by-step procedure the Hermes cronjob's LLM turn follows
**after** `gatekeeper/check_gate.py` has approved running (`approved: true`).
There is no separate "Research Agent" process — you, the LLM executing this
turn, ARE the Research Agent.

## Outer loop — up to 10 iterations per cron trigger, gated every time

The cronjob fires once per hour, but each firing should attempt **up to 10**
research-loop iterations (Steps 1-9 below), not just one — re-checking the
gate before every single iteration, not just once at the start:

```
for i in range(1, 11):
    gate = run `python gatekeeper/check_gate.py`   # re-run LIVE every time, not cached
    if not gate["approved"]:
        log "stopped after N-1 iterations: <gate.reason>", then STOP the outer loop
    else:
        run one full Steps 1-9 iteration (research -> hypothesis -> code -> grid-test -> validate -> log -> commit)
        continue to next i
STOP after 10 iterations even if still approved (avoid unbounded runs from one cron trigger)
```

Why re-check every iteration instead of once at the start: usage climbs
*during* the outer loop as each iteration consumes tokens, and the
**universal 95% safety floor is what makes this safe** — an iteration that
would push usage close to the ceiling gets caught by the *next* iteration's
gate check before it starts, rather than the outer loop blindly running all
10 regardless of live usage. Never skip the re-check to "save time" — the
whole point of checking every iteration is that usage during business hours
especially can climb fast enough that iteration 3 or 4 already shouldn't run
even though iteration 1 was approved.

If the gate blocks before iteration 1 (i.e. the very first check for this
cron trigger fails), do nothing else this trigger — no knowledge base reads,
no file writes — and report the block reason in one line, exactly as before.
If the gate blocks partway through (e.g. after iteration 4), stop cleanly:
finish committing whatever the current iteration already produced (don't
leave a half-written strategy/report/knowledge-base entry), then stop — do
not start iteration 5.

Read `SAFETY.md` once at the start of your first loop if you haven't already
internalized it: **never write, call, or scaffold any real order-placement
function.** This procedure only ever produces backtested/paper-traded
strategy code.

## Per-iteration steps (repeat for each of the up-to-10 iterations above)

## Step 0 — Confirm gate approval and workload

You should already have the gatekeeper's JSON output for this iteration
(re-run per the outer loop above). Note `suggested_workload`
(`light|normal|max`) — use it to scope how much you attempt this iteration
(e.g. under `light`, skip a full walk-forward sweep and prefer
refining/documenting an existing near-miss idea instead of prototyping a
brand-new one from scratch).

## Step 1 — Read the knowledge base

Read, in full:

- `knowledge_base/strategies_log.jsonl` — every prior hypothesis, its
  outcome, and (for rejections) why it failed. This is your memory across
  loop iterations; nothing else persists your past reasoning.
- `knowledge_base/strategies_log.md` — schema reference if you need a
  refresher on the field contract before writing a new entry.

Build a mental model of: what's been tried, what passed and is currently
"live" in `strategies/`, and what failed and why (especially recorded
near-misses worth revisiting with a tweak — check the `notes` field).

## Step 2 — Research pipeline: keyword -> search -> extract -> candidates

Ideas do NOT come from the model's own training-data recall alone. Every
iteration runs an external-research sub-pipeline first, so hypotheses and
their parameters are grounded in something you actually read this run, with
an access-control ledger so the same page is never processed twice.

1. **Keyword discovery.** Pick 1-2 search queries for this iteration. Vary
   them iteration to iteration — use `knowledge_base/strategies_log.jsonl`
   (what's been tried) and `knowledge_base/visited_pages.jsonl` (what's been
   read) to steer toward unexplored angles rather than re-searching the same
   terms (e.g. don't just search "mean reversion strategy" every time; branch
   into specific factors, asset classes, regimes, papers, forum threads).
2. **Search.** Use `web_search` with each keyword.
3. **Dedupe against the ledger.** Before fetching ANY result URL, check it
   (normalized — strip tracking params/trailing slash) against every `url`
   already in `knowledge_base/visited_pages.jsonl`. Skip anything already
   present. Pick 1-3 new, unvisited URLs that look relevant.
4. **Extract.** Use `web_extract` on each chosen URL. Summarize what it
   covers and whether it yields a testable hypothesis (specific
   entry/exit logic, or at least specific parameters/thresholds — not just
   "moving averages can work"). Append one line per visited URL to
   `knowledge_base/visited_pages.jsonl` immediately (see
   `knowledge_base/visited_pages.md` for the schema) — do this even for
   pages that turn out unhelpful, so they're never re-fetched.
5. **Extract candidate strategies.** From the page(s) that yielded something
   usable, write down the concrete hypothesis + starting parameter values
   (e.g. "20-day Bollinger band, 2 std, mean-revert to SMA" — not just "mean
   reversion").

If a search/extract round yields nothing testable, that's a valid (if
unproductive) iteration outcome: log the visited pages anyway (so they're
never re-visited), pick a different keyword, and try again within this same
iteration's budget rather than falling back to inventing a hypothesis from
pure model recall.

## Step 3 — Novelty check + select ONE strategy to test this iteration

Same principle as before, now applied to the research-derived candidate(s)
from Step 2 rather than a freely-invented idea:

1. Compare each candidate hypothesis against every `hypothesis` string
   already in `strategies_log.jsonl`. Skip near-duplicates of something
   already `rejected` for a fundamental (non-fixable) reason, unless you're
   meaningfully varying it (different asset, parameter regime, or
   specifically addressing the prior rejection reason). Skip near-duplicates
   of something already `accepted` and still live in `strategies/`.
2. From the surviving candidates, pick exactly ONE to implement and test
   this iteration (Steps 4 onward). If Step 2 produced multiple candidates,
   the others aren't wasted — they can seed a future iteration's Step 1
   novelty check as "known candidates from source X, not yet tested".
3. Record your novelty judgment and the source URL(s) the hypothesis came
   from in the `notes` field of the eventual log entry (e.g. "from
   https://... ; distinct from 2026-09-01-001: different timeframe and adds
   a regime filter").

If nothing from Step 2 survives novelty screening, it's fine to log a
`rejected` entry explaining that (with `notes` pointing at what was tried)
and end this iteration early rather than forcing a low-quality test.

## Step 4 — Formulate the hypothesis statement

Write one or two plain-English sentences: what pattern/edge you believe
exists (grounded in what you read in Step 2), on what asset(s)/timeframe,
and why (the source's own rationale, or your own economic/behavioral
reasoning if the source didn't give one). This becomes the `hypothesis`
field of the knowledge base entry. Keep scope tight enough to implement and
validate within one loop iteration.

## Step 5 — Write strategy code

Create `strategies/<YYYY-MM-DD>_<short_slug>.py` (see naming convention in
README.md). Requirements:

- **Fetch data via `data/loaders.py`** (`load_equity` / `load_crypto`) —
  these are cache-first wrappers over `src/quant_agent/data`; don't call
  yfinance/ccxt directly and don't write new caching logic.
- Compute signals/positions using pandas/numpy — keep the actual trading
  logic here, but do not reimplement backtest execution mechanics
  (portfolio accounting, slippage/fee application) — that belongs to
  vectorbt in Step 6.
- Expose `generate_signals(price_df, **params) -> pd.Series` (0/1 position
  series) AND `generate_returns(price_df, **params) -> pd.Series` (daily
  strategy returns), both accepting the strategy's tunable parameters as
  keyword arguments (not hardcoded constants) — this keyword-args contract
  is required, not optional, because Step 6's grid test calls
  `generate_returns_fn(price_df, **params)` directly across a parameter
  grid. See `strategies/2026-09-03_bb_meanrev_qqq_volregime.py` for the
  reference shape.
- **No order-placement code.** No broker/exchange authenticated trading
  clients. See `SAFETY.md`.

## Step 6 — Grid-test across parameters, volatility regimes, and asset classes

Before the single-config validators (Step 7), run the strategy across a
grid using `validation/grid_test.py::run_strategy_grid` — this is the "test
across parameters, and check whether it holds up across asset classes
(stocks vs crypto) and different volatility conditions" requirement, not an
optional extra:

```python
from grid_test import run_strategy_grid, GridSpec

spec = GridSpec(
    param_grid={"<param1>": [...], "<param2>": [...]},  # a handful of values each, not exhaustive
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,  # low/mid/high realized-vol terciles
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec, start=..., end=...,
)
summary = result.summary()  # pass_fraction, by_asset_class, by_vol_regime, best/worst cell
```

Keep the grid modest under `suggested_workload="light"` (fewer param values,
maybe one asset class); under `normal`/`max`, cover both asset classes and
at least 2-3 values per tunable parameter as specced in Step 3/4 discussion.
`summary()`'s `pass_fraction`, `by_asset_class`, and `by_vol_regime`
breakdowns go directly into the knowledge base entry's `notes` (Step 9) —
this is what lets a future iteration judge "does this hold up broadly, or
only in one narrow slice" at a glance, without re-running the grid.

A strategy that only works in one asset class or one vol regime is not
automatically rejected — record that finding precisely (e.g. "passed on
equity/low-vol cells only, failed on all crypto cells") since a
narrower-but-honest accepted strategy is more useful than a falsely broad
one; but the honest scope belongs in `notes`/`symbols` so a future loop
doesn't over-trust it outside that scope.

## Step 7 — Backtest and validate (single best-config confirmation)

Use `validation/validators.py` (all vectorbt-backed) on the grid's
best-performing config from Step 6 (or your primary intended config) to get
the full validator suite:

- `check_sharpe_ratio`
- `check_max_drawdown`
- `check_transaction_cost_survival`
- `check_walk_forward`
- `check_parameter_sensitivity` (if the strategy has tunable parameters —
  Step 6's grid already gives you the raw material for this; you can derive
  `param_grid_results` directly from the grid's per-cell Sharpe values
  instead of re-running a separate sweep)

Run whichever subset is relevant given `suggested_workload` from Step 0 (at
minimum, Sharpe + max drawdown; skip walk-forward under `light` if
time/compute-constrained, but say so in the log entry's `notes`).

Each validator returns `(passed: bool, evidence: dict)` — collect these into
the `validators` object for the knowledge base entry.

Write a backtest report to `backtests/<YYYY-MM-DD>_<short_slug>.md`
containing: the hypothesis + source URL(s), the single-config metrics table
(from `evidence` dicts above), the Step 6 grid summary (pass fraction,
per-asset-class/per-vol-regime breakdown), and pass/fail per validator.
Include a vectorbt-generated plot if convenient (save as PNG next to the
report and reference it), otherwise an ASCII/table summary is sufficient.

Optionally, run the strategy's signals through
`paper_trading/simulator.py` (`PaperTradingSimulator`) over a short recent
window to sanity-check realistic fill behavior — this is not a substitute
for the vectorbt-based validators above, just an extra local sanity check.

## Step 8 — Decide accept/reject

- **Accept** if all validators you ran for the primary config passed. Keep
  the strategy file in `strategies/` and the report in `backtests/`.
- **Reject** if any validator failed. Delete or leave the strategy/backtest
  files as a record (your call — if you leave them, note in the log entry
  that they represent a rejected attempt so a future loop doesn't mistake
  them for a live strategy). At minimum, always write the knowledge base
  entry — rejections are exactly as valuable to log as acceptances.

## Step 9 — Log to the knowledge base

Append one JSON line to `knowledge_base/strategies_log.jsonl` following the
schema in `knowledge_base/strategies_log.md`. Include the Step 6 grid
summary and source URL(s) in `notes`. Never rewrite/delete prior lines —
this file is append-only. Double-check your JSON is valid (one complete
object per line, no trailing comma, no multi-line pretty-printing that
would break JSONL parsing).

Also double-check `knowledge_base/visited_pages.jsonl` got an entry for
every URL fetched in Step 2 this iteration (not just the one(s) that led to
the tested hypothesis) — this is what makes the access-control ledger
actually work across iterations.

## End of one iteration — return to the outer loop

That's one full Steps 1-9 cycle. Per the outer loop at the top of this
document: re-run `gatekeeper/check_gate.py` now (live, not cached) before
deciding whether to start another iteration this same cron trigger. Continue
up to iteration 10, or until the gate blocks (usage safety floor reached,
or business-hours 75% headroom exceeded), whichever comes first. If this
was the last iteration this trigger (gate blocked, or iteration 10 reached),
end this cron run's report there — the next hourly cronjob trigger will
start a fresh outer loop from iteration 1, with the knowledge base you just
updated.
