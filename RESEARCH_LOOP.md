# RESEARCH_LOOP.md — Procedure for the Research Agent LLM turn

This is the step-by-step procedure the Hermes cronjob's LLM turn follows
**after** `gatekeeper/check_gate.py` has approved running (`approved: true`).
There is no separate "Research Agent" process — you, the LLM executing this
turn, ARE the Research Agent.

## Outer loop — up to 10 iterations per cron trigger, gated every time

The cronjob fires once per hour, but each firing should attempt **up to 10**
research-loop iterations (Steps 1-7 below), not just one — re-checking the
gate before every single iteration, not just once at the start:

```
for i in range(1, 11):
    gate = run `python gatekeeper/check_gate.py`   # re-run LIVE every time, not cached
    if not gate["approved"]:
        log "stopped after N-1 iterations: <gate.reason>", then STOP the outer loop
    else:
        run one full Steps 1-7 iteration (hypothesis -> code -> validate -> log -> commit)
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

## Step 2 — Novelty check

There is no automated similarity search here — **you, the LLM, read the
summaries and judge novelty directly.** Before committing to a new
hypothesis:

1. Compare your candidate idea against every `hypothesis` string already in
   `strategies_log.jsonl`. If it's a near-duplicate of something already
   `rejected` for a fundamental reason (not a fixable data/feasibility gap),
   don't repeat it — either meaningfully vary it (different asset, different
   parameter regime, addressing the specific rejection reason) or pick a
   different idea entirely.
2. If it's a near-duplicate of something already `accepted` and still in
   `strategies/`, skip it — there's no value in re-deriving a strategy
   that's already logged as working.
3. Record your novelty judgment in the `notes` field of the eventual log
   entry, even briefly (e.g. "distinct from 2026-09-01-001: different
   timeframe and adds a regime filter").

If you conclude nothing sufficiently novel and testable is worth pursuing
this loop, it's fine to write a `rejected` knowledge base entry explaining
that and stop early — don't force a low-quality hypothesis through the rest
of the pipeline just to produce output.

## Step 3 — Formulate a hypothesis

Write one or two plain-English sentences: what pattern/edge you believe
exists, on what asset(s)/timeframe, and roughly why (economic/behavioral
rationale, not just "backtested well" — you haven't backtested it yet).
This becomes the `hypothesis` field of the knowledge base entry.

Keep scope tight enough to implement and validate within one loop iteration.
Prefer reusing library primitives (see Step 4) over inventing new machinery.

## Step 4 — Write strategy code

Create `strategies/<YYYY-MM-DD>_<short_slug>.py` (see naming convention in
README.md). Requirements:

- **Fetch data via `data/loaders.py`** (`load_equity` / `load_crypto`) —
  these are cache-first wrappers over `src/quant_agent/data`; don't call
  yfinance/ccxt directly and don't write new caching logic.
- Compute signals/positions using pandas/numpy — keep the actual trading
  logic here, but do not reimplement backtest execution mechanics
  (portfolio accounting, slippage/fee application) — that belongs to
  vectorbt in Step 5.
- Expose a simple callable, e.g. `def generate_signals(price_df) -> pd.Series`
  or similar, that Step 5's validators can call. There's no fixed interface
  enforced by code yet — just be consistent and document the function
  signature at the top of the file so validators/backtests know how to call
  it.
- **No order-placement code.** No broker/exchange authenticated trading
  clients. See `SAFETY.md`.

## Step 5 — Backtest and validate

Use `validation/validators.py` (all vectorbt-backed) to check the strategy:

- `check_sharpe_ratio`
- `check_max_drawdown`
- `check_transaction_cost_survival`
- `check_walk_forward`
- `check_parameter_sensitivity` (if the strategy has tunable parameters)

Run whichever subset is relevant given `suggested_workload` from Step 0 (at
minimum, Sharpe + max drawdown; skip walk-forward/param-sensitivity under
`light` if time/compute-constrained, but say so in the log entry's `notes`).

Each validator returns `(passed: bool, evidence: dict)` — collect these into
the `validators` object for the knowledge base entry.

Write a backtest report to `backtests/<YYYY-MM-DD>_<short_slug>.md`
containing: the hypothesis, the metrics table (from `evidence` dicts above),
and pass/fail per validator. Include a vectorbt-generated plot if convenient
(save as PNG next to the report and reference it), otherwise an ASCII/table
summary is sufficient.

Optionally, run the strategy's signals through
`paper_trading/simulator.py` (`PaperTradingSimulator`) over a short recent
window to sanity-check realistic fill behavior — this is not a substitute
for the vectorbt-based validators above, just an extra local sanity check.

## Step 6 — Decide accept/reject

- **Accept** if all validators you ran for this hypothesis passed. Keep the
  strategy file in `strategies/` and the report in `backtests/`.
- **Reject** if any validator failed. Delete or leave the strategy/backtest
  files as a record (your call — if you leave them, note in the log entry
  that they represent a rejected attempt so a future loop doesn't mistake
  them for a live strategy). At minimum, always write the knowledge base
  entry — rejections are exactly as valuable to log as acceptances.

## Step 7 — Log to the knowledge base

Append one JSON line to `knowledge_base/strategies_log.jsonl` following the
schema in `knowledge_base/strategies_log.md`. Never rewrite/delete prior
lines — this file is append-only. Double-check your JSON is valid (one
complete object per line, no trailing comma, no multi-line pretty-printing
that would break JSONL parsing).

## End of one iteration — return to the outer loop

That's one full Steps 1-7 cycle. Per the outer loop at the top of this
document: re-run `gatekeeper/check_gate.py` now (live, not cached) before
deciding whether to start another iteration this same cron trigger. Continue
up to iteration 10, or until the gate blocks (usage safety floor reached,
or business-hours 75% headroom exceeded), whichever comes first. If this
was the last iteration this trigger (gate blocked, or iteration 10 reached),
end this cron run's report there — the next hourly cronjob trigger will
start a fresh outer loop from iteration 1, with the knowledge base you just
updated.
