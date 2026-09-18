import importlib.util
import sys
from datetime import datetime
import itertools

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity, load_crypto  # noqa: E402
from validators import check_sharpe_ratio, check_max_drawdown  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_ehlers_emd_trend_mode.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

for sym, loader in [("QQQ", load_equity), ("SPY", load_equity)]:
    price_df = loader(sym, start, end)
    best = None
    for period, fraction, max_hold_days in itertools.product([15, 20, 30], [3.0, 5.0, 8.0], [40, 60]):
        r = strat.generate_returns(price_df, period=period, fraction=fraction, max_hold_days=max_hold_days)
        sh_pass, sh_ev = check_sharpe_ratio(r)
        mdd_pass, mdd_ev = check_max_drawdown(r)
        sharpe = sh_ev.get("value")
        mdd = mdd_ev.get("value")
        if best is None or (sharpe or -99) > best[0]:
            best = (sharpe, mdd, period, fraction, max_hold_days)
    print(sym, best)
