from collections import defaultdict
from datetime import datetime
import numpy as np
import pandas as pd

from services.db import db
from services.models import EventLog, BottleneckMetric

# Helpers ----------------------------------------------------------------------

def _events_df_for_project(project_id: int) -> pd.DataFrame:
    """
    Load consolidated/normalized events for a project as a DataFrame.
    Columns expected: case_id, timestamp (UTC), canonical_activity or activity.
    If canonical_activity is missing, fallback to activity.
    """
    # Pull from EventLog table scoped by project.
    # If your schema uses ConsolidatedEvent, swap the model here accordingly.
    rows = (
        db.session.query(EventLog.case_id, EventLog.timestamp, EventLog.canonical_activity, EventLog.activity)
        .filter(EventLog.project_id == project_id)
        .order_by(EventLog.case_id.asc(), EventLog.timestamp.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["case_id", "timestamp", "label"])

    df = pd.DataFrame(rows, columns=["case_id","timestamp","canonical_activity","activity"])
    # robust label selection
    df["label"] = df["canonical_activity"].fillna(df["activity"])
    # coerce to datetime (UTC safe)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["case_id","timestamp","label"]).reset_index(drop=True)
    return df

def _percentile_threshold(values: pd.Series, q: float = 0.90) -> float:
    if values.empty:
        return float("inf")
    return float(np.nanpercentile(values.to_numpy(dtype=float), q * 100))

# Core analytics ---------------------------------------------------------------

def compute_activity_and_transition_metrics(project_id: int, percentile: float = 0.90):
    """
    Returns two DataFrames:
      activities: [activity, count, avg_seconds, median_seconds, p90_seconds, is_bottleneck]
      transitions: [source_activity, target_activity, count, avg_seconds, median_seconds, p90_seconds, is_bottleneck]
    NOTE:
      - Without explicit start/complete lifecycle, we treat 'activity duration' as
        the sojourn/wait time until the *next* event in the same case.
      - Transitions represent wait times between consecutive activities.
    """
    df = _events_df_for_project(project_id)
    if df.empty:
        return (pd.DataFrame(), pd.DataFrame())

    # sort per case
    df = df.sort_values(["case_id","timestamp"])
    # compute deltas to next event inside each case
    df["next_timestamp"] = df.groupby("case_id")["timestamp"].shift(-1)
    df["next_label"] = df.groupby("case_id")["label"].shift(-1)
    df["delta_sec"] = (df["next_timestamp"] - df["timestamp"]).dt.total_seconds()

    # drop tail rows (no next event)
    trans_df = df.dropna(subset=["next_timestamp","next_label","delta_sec"]).copy()

    # --- Activity sojourn (time from activity to next event)
    act = (
        trans_df.groupby("label")["delta_sec"]
        .agg(["count", "mean", "median", (lambda s: np.nanpercentile(s, 90))])
        .reset_index()
        .rename(columns={"label":"activity","mean":"avg_seconds","median":"median_seconds","<lambda_0>":"p90_seconds"})
    )

    # threshold for activities
    act_thr = _percentile_threshold(act["p90_seconds"], q=percentile)
    act["is_bottleneck"] = act["p90_seconds"] >= act_thr

    # --- Transition waiting times (between consecutive activities)
    trans = (
        trans_df.groupby(["label","next_label"])["delta_sec"]
        .agg(["count","mean","median", (lambda s: np.nanpercentile(s, 90))])
        .reset_index()
        .rename(columns={"label":"source_activity","next_label":"target_activity","mean":"avg_seconds",
                         "median":"median_seconds","<lambda_0>":"p90_seconds"})
    )
    trans_thr = _percentile_threshold(trans["p90_seconds"], q=percentile)
    trans["is_bottleneck"] = trans["p90_seconds"] >= trans_thr

    return (act, trans)

def persist_bottleneck_metrics(project_id: int, activities_df: pd.DataFrame, transitions_df: pd.DataFrame):
    # clear previous metrics snapshot (optional: keep history by skipping delete)
    db.session.query(BottleneckMetric).filter(BottleneckMetric.project_id == project_id).delete()
    db.session.commit()

    # store activities
    for _, r in activities_df.iterrows():
        db.session.add(BottleneckMetric(
            project_id=project_id,
            kind="activity",
            activity=str(r["activity"]),
            count=int(r["count"]),
            avg_seconds=float(r["avg_seconds"]),
            median_seconds=float(r["median_seconds"]),
            p90_seconds=float(r["p90_seconds"]),
            is_bottleneck=bool(r["is_bottleneck"]),
        ))

    # store transitions
    for _, r in transitions_df.iterrows():
        db.session.add(BottleneckMetric(
            project_id=project_id,
            kind="transition",
            source_activity=str(r["source_activity"]),
            target_activity=str(r["target_activity"]),
            count=int(r["count"]),
            avg_seconds=float(r["avg_seconds"]),
            median_seconds=float(r["median_seconds"]),
            p90_seconds=float(r["p90_seconds"]),
            is_bottleneck=bool(r["is_bottleneck"]),
        ))

    db.session.commit()

def compute_and_store_bottlenecks(project_id: int, percentile: float = 0.90):
    act, trans = compute_activity_and_transition_metrics(project_id, percentile)
    persist_bottleneck_metrics(project_id, act, trans)
    return act, trans
