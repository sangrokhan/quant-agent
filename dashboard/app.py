"""Quant-agent dashboard.

Streamlit app that visualizes:
  1) Strategy research/validation history (knowledge_base/strategies_log.jsonl)
  2) Gatekeeper / cron execution history (~/.hermes/cron/output/<job_id>/*.md
     + gatekeeper/usage_state.json + knowledge_base/usage_tracking.md)

Run:
    cd /home/han/repo/quant-agent
    uv run streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0

Data is re-read from disk on every Streamlit rerun (no caching of file
contents across long TTL), so the dashboard always reflects the latest
knowledge_base / cron output state without needing a restart.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "knowledge_base"
GATEKEEPER_DIR = REPO_ROOT / "gatekeeper"
CRON_JOB_ID = "7252d5c819b0"  # quant-agent-research-loop
CRON_OUTPUT_DIR = Path.home() / ".hermes" / "cron" / "output" / CRON_JOB_ID

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="Quant Agent Dashboard", layout="wide", page_icon="📈")


# ---------------------------------------------------------------------------
# Data loading (no long-lived cache — always fresh on rerun)
# ---------------------------------------------------------------------------

def load_strategies_log() -> pd.DataFrame:
    path = KB_DIR / "strategies_log.jsonl"
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()

    df = pd.json_normalize(rows)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    if "outcome" in df.columns:
        def norm_outcome(o):
            if not isinstance(o, str):
                return "unknown"
            ol = o.lower()
            if "accept" in ol:
                return "accepted"
            if "reject" in ol:
                return "rejected"
            return "other"
        df["outcome_norm"] = df["outcome"].apply(norm_outcome)
    else:
        df["outcome_norm"] = "unknown"

    for col in ["validators.sharpe_ratio.value", "validators.max_drawdown.value"]:
        if col not in df.columns:
            df[col] = None
    return df


def load_usage_state() -> dict:
    path = GATEKEEPER_DIR / "usage_state.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def load_usage_tracking_md() -> str:
    path = KB_DIR / "usage_tracking.md"
    if not path.exists():
        return ""
    return path.read_text()


RESPONSE_RE = re.compile(r"## Response\s*\n(.*)\Z", re.DOTALL)
RUNTIME_RE = re.compile(r"\*\*Run Time:\*\*\s*(.+)")
GATE_APPROVED_RE = re.compile(r"approved[`'\"]?\s*[:=]\s*(true|false)", re.IGNORECASE)


def load_cron_runs() -> pd.DataFrame:
    if not CRON_OUTPUT_DIR.exists():
        return pd.DataFrame()
    rows = []
    for fp in sorted(CRON_OUTPUT_DIR.glob("*.md")):
        try:
            text = fp.read_text()
        except Exception:
            continue
        m_time = RUNTIME_RE.search(text)
        run_time = m_time.group(1).strip() if m_time else fp.stem.replace("_", " ")

        # Only look at the FINAL "## Response" section (last occurrence),
        # since continuity=true nests all previous runs' full text inside
        # "## Your previous run's output" blocks.
        last_response = ""
        idx = text.rfind("## Response")
        if idx != -1:
            last_response = text[idx + len("## Response"):].strip()

        gate_blocked = "approved: false" in last_response.lower() or "게이트 미승인" in last_response
        rows.append({
            "file": fp.name,
            "run_time": run_time,
            "gate_blocked": gate_blocked,
            "response": last_response,
            "mtime": datetime.fromtimestamp(fp.stat().st_mtime),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("mtime", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("📈 Quant Agent Dashboard")
st.caption(f"repo: {REPO_ROOT}  ·  새로고침(F5) 시 항상 최신 데이터를 다시 읽습니다.")

tab_strategies, tab_runs = st.tabs(["🧪 전략 탐색/검증 이력", "🚦 게이트키퍼 / 실행 로그"])

# --- Tab 1: strategy history ------------------------------------------------
with tab_strategies:
    df = load_strategies_log()
    if df.empty:
        st.info("strategies_log.jsonl 이 비어있거나 없습니다.")
    else:
        total = len(df)
        n_accepted = (df["outcome_norm"] == "accepted").sum()
        n_rejected = (df["outcome_norm"] == "rejected").sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 실험 수", total)
        c2.metric("채택 (accepted)", int(n_accepted))
        c3.metric("기각 (rejected)", int(n_rejected))
        c4.metric("채택률", f"{(n_accepted/total*100):.1f}%" if total else "-")

        st.divider()

        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.subheader("Outcome 분포")
            st.bar_chart(df["outcome_norm"].value_counts())
        with col_right:
            if "created_at" in df.columns and df["created_at"].notna().any():
                st.subheader("일자별 실험량")
                daily = (
                    df.dropna(subset=["created_at"])
                    .assign(date=lambda d: d["created_at"].dt.date)
                    .groupby(["date", "outcome_norm"]).size()
                    .unstack(fill_value=0)
                )
                st.bar_chart(daily)

        st.divider()
        st.subheader("Sharpe 분포 (채택 vs 기각)")
        sharpe_col = "validators.sharpe_ratio.value"
        if sharpe_col in df.columns and df[sharpe_col].notna().any():
            sharpe_df = df[[sharpe_col, "outcome_norm"]].dropna()
            sharpe_df = sharpe_df.rename(columns={sharpe_col: "sharpe_ratio"})
            st.scatter_chart(sharpe_df, x="outcome_norm", y="sharpe_ratio")
        else:
            st.caption("sharpe_ratio 값을 찾을 수 없습니다 (스키마가 다른 항목일 수 있음).")

        st.divider()
        st.subheader("전체 실험 로그")

        outcome_filter = st.multiselect(
            "outcome 필터", options=sorted(df["outcome_norm"].unique()),
            default=list(df["outcome_norm"].unique()),
        )
        search_text = st.text_input("검색어 (hypothesis / notes / tags 등, 대소문자 무시)", "")

        filtered = df[df["outcome_norm"].isin(outcome_filter)]
        if search_text:
            mask = filtered.apply(
                lambda row: search_text.lower() in json.dumps(row.to_dict(), default=str).lower(),
                axis=1,
            )
            filtered = filtered[mask]

        display_cols = [c for c in [
            "id", "created_at", "hypothesis", "asset_class", "outcome",
            "validators.sharpe_ratio.value", "validators.max_drawdown.value",
            "strategy_file", "backtest_report",
        ] if c in filtered.columns]

        st.dataframe(
            filtered[display_cols].sort_values(
                "created_at", ascending=False
            ) if "created_at" in filtered.columns else filtered[display_cols],
            width="stretch",
            height=420,
        )

        st.caption(f"{len(filtered)} / {total} 건 표시 중")

        with st.expander("선택한 행 상세 보기 (id로 조회)"):
            if "id" in df.columns:
                pick = st.selectbox("id 선택", options=["-"] + filtered["id"].tolist())
                if pick != "-":
                    row = df[df["id"] == pick].iloc[0]
                    st.json(row.dropna().to_dict())

# --- Tab 2: gatekeeper / cron run history -----------------------------------
with tab_runs:
    st.subheader("현재 게이트 상태 (usage_state.json)")
    usage = load_usage_state()
    if usage:
        c1, c2, c3 = st.columns(3)
        c1.metric("5h 사용량", f"{usage.get('usage_pct', '?')}%")
        c2.metric("limit_reached", str(usage.get("limit_reached")))
        c3.metric("업데이트 시각", usage.get("updated_at", "-"))
        with st.expander("raw usage_state.json"):
            st.json(usage)
    else:
        st.caption("usage_state.json 을 찾을 수 없습니다.")

    st.divider()
    st.subheader(f"cron 실행 이력 (job {CRON_JOB_ID}, 최신순)")
    runs = load_cron_runs()
    if runs.empty:
        st.info(f"{CRON_OUTPUT_DIR} 에 실행 로그가 없습니다.")
    else:
        n_blocked = int(runs["gate_blocked"].sum())
        n_ran = len(runs) - n_blocked
        c1, c2, c3 = st.columns(3)
        c1.metric("총 트리거 수", len(runs))
        c2.metric("게이트 승인 (실행됨)", n_ran)
        c3.metric("게이트 차단", n_blocked)

        for _, r in runs.iterrows():
            icon = "🚫" if r["gate_blocked"] else "✅"
            with st.expander(f"{icon} {r['run_time']}  —  {r['file']}"):
                st.text(r["response"][:4000] if r["response"] else "(응답 없음)")

    st.divider()
    st.subheader("Usage tracking 로그 (수동 측정)")
    md = load_usage_tracking_md()
    if md:
        st.markdown(md)
    else:
        st.caption("usage_tracking.md 없음.")
