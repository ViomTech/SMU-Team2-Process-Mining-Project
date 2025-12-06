# routes/process_mining.py
from flask import Blueprint, request, jsonify, session
from services.process_mining_service import mine_process_from_csv
from services.bottleneck_service import compute_and_store_bottlenecks
from services.models import BottleneckMetric, EventLog
from services.db import db
import pandas as pd
import numpy as np  # ✅ added for percentile computation

process_bp = Blueprint("process", __name__)

@process_bp.route("/mine/<int:project_id>", methods=["POST"])
def mine_process_route(project_id):
    user_id = session.get("user_id")
    try:
        new_bpmn = mine_process_from_csv(user_id=user_id, project_id=project_id)
        # ⬇️ Immediately compute + store bottlenecks after mining
        compute_and_store_bottlenecks(project_id, percentile=0.90)
        return jsonify({
            "message": "Process mined successfully",
            "bpmnfile_id": new_bpmn.bpmnfile_id,
            "filename": new_bpmn.filename
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================================================
# UPDATED: list bottlenecks (now returns only top 10% by P90)
# ===========================================================
@process_bp.route("/bottlenecks/<int:project_id>", methods=["GET"])
def list_bottlenecks(project_id):
    # optional: recompute on demand by passing ?refresh=1
    refresh = request.args.get("refresh")
    if refresh == "1":
        compute_and_store_bottlenecks(project_id, percentile=0.90)

    rows = (
        db.session.query(BottleneckMetric)
        .filter(BottleneckMetric.project_id == project_id)
        .order_by(BottleneckMetric.p90_seconds.desc())
        .all()
    )

    if not rows:
        return jsonify([])

    # --- ✅ Determine 90th percentile of p90_seconds ---
    p90_values = [m.p90_seconds for m in rows if m.p90_seconds is not None]
    threshold = np.percentile(p90_values, 90) if p90_values else 0

    # --- ✅ Keep only entries at or above threshold ---
    top_bottlenecks = [m for m in rows if m.p90_seconds and m.p90_seconds >= threshold]

    def row_to_dict(m):
        base = {
            "id": m.id,
            "kind": m.kind,
            "count": m.count,
            "avg_seconds": m.avg_seconds,
            "median_seconds": m.median_seconds,
            "p90_seconds": m.p90_seconds,
            "is_bottleneck": True,  # always True since top 10%
            "bpmn_element_id": m.bpmn_element_id,
        }
        if m.kind == "activity":
            base["activity"] = m.activity
        else:
            base["source_activity"] = m.source_activity
            base["target_activity"] = m.target_activity
        return base

    return jsonify([row_to_dict(m) for m in top_bottlenecks])


# ===========================================================
# Drilldown endpoint (unchanged)
# ===========================================================
@process_bp.route("/bottlenecks/<int:project_id>/drilldown", methods=["GET"])
def drilldown_bottleneck(project_id):
    kind = request.args.get("kind")  # "activity" or "transition"
    a = request.args.get("activity")
    s = request.args.get("source_activity")
    t = request.args.get("target_activity")

    rows = (
        db.session.query(
            EventLog.case_id,
            EventLog.timestamp,
            EventLog.canonical_activity,
            EventLog.activity,
        )
        .filter(EventLog.project_id == project_id)
        .order_by(EventLog.case_id.asc(), EventLog.timestamp.asc())
        .all()
    )

    if not rows:
        return jsonify([])

    df = pd.DataFrame(rows, columns=["case_id", "timestamp", "canonical_activity", "activity"])
    df["label"] = df["canonical_activity"].fillna(df["activity"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["case_id", "timestamp", "label"]).sort_values(["case_id", "timestamp"])

    df["next_timestamp"] = df.groupby("case_id")["timestamp"].shift(-1)
    df["next_label"] = df.groupby("case_id")["label"].shift(-1)
    df["delta_sec"] = (df["next_timestamp"] - df["timestamp"]).dt.total_seconds()

    if kind == "activity" and a:
        sub = df[df["label"] == a].dropna(subset=["delta_sec"])
        out = sub[["case_id", "timestamp", "next_timestamp", "delta_sec"]].head(200)
    elif kind == "transition" and s and t:
        sub = df[(df["label"] == s) & (df["next_label"] == t)].dropna(subset=["delta_sec"])
        out = sub[["case_id", "timestamp", "next_timestamp", "delta_sec"]].head(200)
    else:
        return jsonify({"error": "Invalid query"}), 400

    payload = [
        {
            "case_id": str(r.case_id),
            "from": r.timestamp.isoformat(),
            "to": r.next_timestamp.isoformat() if pd.notna(r.next_timestamp) else None,
            "seconds": float(r.delta_sec) if pd.notna(r.delta_sec) else None,
        }
        for _, r in out.iterrows()
    ]
    return jsonify(payload)
