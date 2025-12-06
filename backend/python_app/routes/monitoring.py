# backend/python_app/routes/monitoring.py
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from services.db import db
from services.models import Project, EventLog
import pandas as pd
import numpy as np
from sqlalchemy import or_

monitoring_bp = Blueprint("monitoring", __name__)

# ---- helper: tolerant parse of FE inputs ----
def _parse_iso_like(s: str | None):
    """
    Accepts either 'YYYY-MM-DDTHH:MM' (no TZ) from <input type="datetime-local">
    or full ISO (with/without 'Z'). Returns naive datetime in UTC-equivalent
    comparison context (DB usually stores naive UTC).
    """
    if not s:
        return None
    try:
        # drop trailing Z if present so fromisoformat works
        return datetime.fromisoformat(s.replace("Z", ""))
    except Exception:
        return None

def _events_df_for_project_and_window(project_id: int, start_iso: str | None, end_iso: str | None) -> pd.DataFrame:
    q = db.session.query(
        EventLog.case_id,
        EventLog.timestamp,
        EventLog.canonical_activity,
        EventLog.activity,
    ).filter(EventLog.project_id == project_id)

    start_dt = _parse_iso_like(start_iso)
    end_dt = _parse_iso_like(end_iso)

    if start_dt is not None:
        q = q.filter(EventLog.timestamp >= start_dt)
    if end_dt is not None:
        q = q.filter(EventLog.timestamp <= end_dt)

    rows = q.order_by(EventLog.case_id.asc(), EventLog.timestamp.asc()).all()
    if not rows:
        return pd.DataFrame(columns=["case_id", "timestamp", "label"])

    df = pd.DataFrame(rows, columns=["case_id", "timestamp", "canonical_activity", "activity"])
    df["label"] = df["canonical_activity"].fillna(df["activity"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["case_id", "timestamp", "label"]).reset_index(drop=True)
    return df

@monitoring_bp.route("/processes", methods=["GET"])
def list_processes():
    """
    Return processes the current user can view:
    - Creator of the process (Project.user_id)
    - Assigned BPO for the process (Project.assigned_bpo_id)
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    projects = (
        db.session.query(Project.project_id, Project.project_name)
        .filter(or_(Project.user_id == user_id, Project.assigned_bpo_id == user_id))
        .order_by(Project.created_at.desc())
        .all()
    )
    return jsonify([{"project_id": pid, "project_name": name} for (pid, name) in projects])

# ---- NEW: expose available date range for a process ----
@monitoring_bp.route("/range", methods=["GET"])
def process_range():
    """
    User may view if they are:
    - Creator (Project.user_id)
    - Assigned BPO (Project.assigned_bpo_id)
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "Missing project_id"}), 400

    proj = (
        db.session.query(Project)
        .filter(Project.project_id == project_id)
        .filter(or_(Project.user_id == user_id, Project.assigned_bpo_id == user_id))
        .first()
    )
    if not proj:
        return jsonify({"error": "Project not found or access denied"}), 404

    row = (
        db.session.query(
            db.func.min(EventLog.timestamp),
            db.func.max(EventLog.timestamp),
            db.func.count(EventLog.case_id.distinct())
        )
        .filter(EventLog.project_id == project_id)
        .first()
    )
    min_ts, max_ts, cases = row if row else (None, None, 0)
    return jsonify({
        "project_id": project_id,
        "cases": int(cases or 0),
        "min": min_ts.isoformat() if min_ts else None,
        "max": max_ts.isoformat() if max_ts else None,
    })

@monitoring_bp.route("/metrics", methods=["GET"])
def dashboard_metrics():
    """
    User may view if they are:
    - Creator (Project.user_id)
    - Assigned BPO (Project.assigned_bpo_id)
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "Missing project_id"}), 400

    proj = (
        db.session.query(Project)
        .filter(Project.project_id == project_id)
        .filter(or_(Project.user_id == user_id, Project.assigned_bpo_id == user_id))
        .first()
    )
    if not proj:
        return jsonify({"error": "Project not found or access denied"}), 404

    start = request.args.get("start")
    end = request.args.get("end")

    df = _events_df_for_project_and_window(project_id, start, end)
    if df.empty:
        return jsonify({
            "project_id": project_id,
            "cases": 0,
            "activities": [],
            "transitions": [],
        })

    df = df.sort_values(["case_id", "timestamp"])
    df["next_timestamp"] = df.groupby("case_id")["timestamp"].shift(-1)
    df["next_label"] = df.groupby("case_id")["label"].shift(-1)
    df["delta_sec"] = (df["next_timestamp"] - df["timestamp"]).dt.total_seconds()
    trans_df = df.dropna(subset=["next_timestamp", "next_label", "delta_sec"]).copy()

    act = (
        trans_df.groupby("label")["delta_sec"]
        .agg(["count", "mean", "median", lambda s: np.nanpercentile(s, 90)])
        .reset_index()
        .rename(columns={
            "label": "activity",
            "mean": "avg_seconds",
            "median": "median_seconds",
            "<lambda_0>": "p90_seconds",
        })
    )
    trans = (
        trans_df.groupby(["label", "next_label"])["delta_sec"]
        .agg(["count", "mean", "median", lambda s: np.nanpercentile(s, 90)])
        .reset_index()
        .rename(columns={
            "label": "source_activity",
            "next_label": "target_activity",
            "mean": "avg_seconds",
            "median": "median_seconds",
            "<lambda_0>": "p90_seconds",
        })
    )

    if not act.empty:
        act_thr = float(np.nanpercentile(act["p90_seconds"].to_numpy(dtype=float), 90))
        act["is_bottleneck"] = act["p90_seconds"] >= act_thr
    else:
        act["is_bottleneck"] = []

    if not trans.empty:
        trans_thr = float(np.nanpercentile(trans["p90_seconds"].to_numpy(dtype=float), 90))
        trans["is_bottleneck"] = trans["p90_seconds"] >= trans_thr
    else:
        trans["is_bottleneck"] = []

    payload = {
        "project_id": project_id,
        "cases": int(df["case_id"].nunique()),
        "activities": [
            {
                "activity": str(r.activity),
                "count": int(r["count"]),
                "avg_seconds": float(r.avg_seconds),
                "median_seconds": float(r.median_seconds),
                "p90_seconds": float(r.p90_seconds),
                "is_bottleneck": bool(r.is_bottleneck),
            }
            for _, r in act.sort_values("p90_seconds", ascending=False).iterrows()
        ],
        "transitions": [
            {
                "source_activity": str(r.source_activity),
                "target_activity": str(r.target_activity),
                "count": int(r["count"]),
                "avg_seconds": float(r.avg_seconds),
                "median_seconds": float(r.median_seconds),
                "p90_seconds": float(r.p90_seconds),
                "is_bottleneck": bool(r.is_bottleneck),
            }
            for _, r in trans.sort_values("p90_seconds", ascending=False).iterrows()
        ],
    }
    return jsonify(payload), 200
