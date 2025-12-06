# backend/python_app/services/merge_service.py
from __future__ import annotations
import hashlib
import pandas as pd
from typing import List, Tuple, Optional
from sqlalchemy import text
from services.db import db
from services.models import File, EventLog, Project, ConsolidatedEvent, MergeRun
from services.merge_core import merge_normalized_sources

def _pull_project_eventlog_df(project_id: int) -> pd.DataFrame:
    q = (
        db.session.query(
            EventLog.case_id,
            EventLog.activity,
            EventLog.canonical_activity,
            EventLog.timestamp,
            File.filename.label("source")
        )
        .join(File, File.file_id == EventLog.file_id)
        .filter(EventLog.project_id == project_id)
    )
    rows = q.all()
    if not rows:
        return pd.DataFrame(columns=["case_id","activity","canonical_activity","timestamp","source"])
    df = pd.DataFrame(rows, columns=["case_id","activity","canonical_activity","timestamp","source"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df

def _upsert_csv_artifact(
    *, project_id: int, user_id: int, filename: str, csv_bytes: bytes
) -> None:
    """Keep exactly one consolidated CSV per project; update in place if it exists."""
    file_hash = hashlib.sha256(csv_bytes).hexdigest()

    # Prefer a single row keyed by (project_id, filename)
    row = File.query.filter_by(user_id=user_id, project_id=project_id, filename=filename).first()
    if row:
        # update contents + hash (will not violate the (user_id, project_id, file_hash) unique constraint)
        row.file_data = csv_bytes
        row.file_hash = file_hash
        row.status = 1
        db.session.commit()
        return

    # If a row with identical content already exists under a different filename, reuse it
    same_hash = File.query.filter_by(user_id=user_id, project_id=project_id, file_hash=file_hash).first()
    if same_hash:
        same_hash.filename = filename
        same_hash.file_data = csv_bytes
        same_hash.status = 1
        db.session.commit()
        return

    # Otherwise insert a new artifact
    new_file = File(
        user_id=user_id,
        project_id=project_id,
        filename=filename,
        file_hash=file_hash,
        file_data=csv_bytes,
        status=1,
    )
    db.session.add(new_file)
    db.session.commit()

def consolidate_project_event_logs_snapshot_and_artifact(
    project_id: int,
    extra_sources: Optional[List[Tuple[str, pd.DataFrame]]] = None,
    artifact_filename: Optional[str] = None,   # default: do NOT write a CSV
) -> pd.DataFrame:
    """
    1) Build consolidated DataFrame (standardize + dedupe + sort)
    2) Replace snapshot rows in consolidated_event_log (linked to new MergeRun)
    3) Upsert CSV artifact in files
    """
    # --- 1) Build consolidated dataframe
    base_df = _pull_project_eventlog_df(project_id)
    named_sources: List[Tuple[str, pd.DataFrame]] = [("db_normalized", base_df)]
    if extra_sources:
        named_sources.extend(extra_sources)

    consolidated = merge_normalized_sources(named_sources)
    if not consolidated.empty:
        consolidated = consolidated.copy()
        consolidated["timestamp"] = pd.to_datetime(consolidated["timestamp"], utc=True)

    # --- 2) Create a new MergeRun record
    proj = Project.query.get(project_id)
    if not proj:
        raise ValueError(f"Project {project_id} not found")

    merge_run = MergeRun(
        project_id=project_id,
        user_id=proj.user_id,
        status="completed",
        event_count=int(consolidated.shape[0]),
        source_fingerprints=",".join(sorted(set(str(f) for f, _ in named_sources))),
    )
    db.session.add(merge_run)
    db.session.commit()  # flush to get merge_run_id

    # --- 3) Replace snapshot for this project
    try:
        # clear old snapshot for this project
        db.session.execute(
            text("DELETE FROM consolidated_event_log WHERE project_id = :pid"),
            {"pid": project_id},
        )

        if not consolidated.empty:
            deduped = consolidated.drop_duplicates(
                subset=["case_id", "timestamp", "canonical_activity", "activity", "source"],
                keep="first",
                ignore_index=True,
            )

            # update merge_run with actual count
            merge_run.event_count = int(deduped.shape[0])
            db.session.commit()

            events = [
                ConsolidatedEvent(
                    merge_run_id=merge_run.merge_run_id,
                    project_id=project_id,
                    case_id=None if pd.isna(r["case_id"]) else str(r["case_id"]),
                    activity=str(r["activity"]) if pd.notna(r["activity"]) else "UNKNOWN_ACTIVITY",
                    canonical_activity=None if pd.isna(r["canonical_activity"]) else str(r["canonical_activity"]),
                    timestamp=pd.to_datetime(r["timestamp"], utc=True).to_pydatetime(),
                    source=None if pd.isna(r["source"]) else str(r["source"]),
                )
                for _, r in deduped.iterrows()
            ]

            BATCH_SIZE = 500
            for i in range(0, len(events), BATCH_SIZE):
                batch = events[i:i+BATCH_SIZE]
                db.session.bulk_save_objects(batch)
                db.session.commit()
                

    except Exception:
        db.session.rollback()
        raise


    # --- 4) Upsert CSV artifact (idempotent)  <-- remove the word 'Upsert' if you'd like
    if artifact_filename:
        if consolidated.empty:
            csv_bytes = b"case_id,activity,canonical_activity,timestamp,source\n"
        else:
            df_out = consolidated.copy()
            df_out["timestamp"] = pd.to_datetime(df_out["timestamp"], utc=True) \
                                    .dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            csv_bytes = df_out.to_csv(index=False).encode("utf-8")

        _upsert_csv_artifact(
            project_id=project_id,
            user_id=proj.user_id,
            filename=artifact_filename,
            csv_bytes=csv_bytes,
        )
    return consolidated
