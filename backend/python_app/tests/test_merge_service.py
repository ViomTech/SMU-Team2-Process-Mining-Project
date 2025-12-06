import pandas as pd
import pytest
from sqlalchemy import select, func
from unittest import mock
from services.db import db
from services.models import File, EventLog, Project, ConsolidatedEvent, MergeRun
from services.merge_service import consolidate_project_event_logs_snapshot_and_artifact, _pull_project_eventlog_df, _upsert_csv_artifact

@pytest.fixture(autouse=True)
def _sqlite_autoincrement_for_consolidated_event(monkeypatch):
    from sqlalchemy import func as _func
    import services.merge_service as ms
    from services.models import ConsolidatedEvent as CE

    def _patched_bulk_save_objects(objs, **kwargs):
        max_id = db.session.query(_func.max(CE.id)).scalar() or 0
        next_id = max_id + 1
        for o in objs:
            if isinstance(o, CE) and (getattr(o, "id", None) in (None, 0)):
                o.id = next_id
                next_id += 1
        db.session.add_all(objs)
        db.session.flush()
    monkeypatch.setattr(ms.db.session, "bulk_save_objects", _patched_bulk_save_objects)

def _add_event(dbfile, project_id, case_id, activity, canonical, ts):
    ev = EventLog(
        file_id=dbfile.file_id,
        project_id=project_id,
        case_id=case_id,
        activity=activity,
        canonical_activity=canonical,
        timestamp=pd.to_datetime(ts, utc=True).to_pydatetime(),
    )
    db.session.add(ev)
    db.session.commit()

def test_project_not_found_raises(app):
    with pytest.raises(ValueError):
        consolidate_project_event_logs_snapshot_and_artifact(project_id=9999)

@pytest.mark.parametrize("filename", ["consolidated.csv", None])
def test_roundtrip_and_artifact_paths(app, make_user, make_project, make_file, filename):
    u = make_user(email="m@example.com")
    p = make_project(u, "P1")
    f1 = make_file(u, p, filename="f1.csv", file_data=b"1")
    f2 = make_file(u, p, filename="f2.csv", file_data=b"2")
    _add_event(f1, p.project_id, "APP001", "Submit", "Application Submitted", "2024-01-01T00:00:00Z")
    _add_event(f2, p.project_id, "APP002", "Verify", "Documents Verified", "2024-01-02T00:00:00Z")

    df = consolidate_project_event_logs_snapshot_and_artifact(p.project_id, artifact_filename=filename)
    assert df.shape[0] >= 2
    assert db.session.scalars(select(func.count()).select_from(MergeRun)).one() == 1

def test_artifact_same_hash_rename_branch(app, make_user, make_project, make_file):
    u = make_user(email="a@example.com")
    p = make_project(u, "P2")
    f1 = make_file(u, p, filename="db.csv", file_data=b"x")
    _add_event(f1, p.project_id, "APP1", "Submit", "Application Submitted", "2024-01-01T00:00:00Z")
    df1 = consolidate_project_event_logs_snapshot_and_artifact(p.project_id, artifact_filename="consolidated.csv")
    df2 = consolidate_project_event_logs_snapshot_and_artifact(p.project_id, artifact_filename="consolidated.csv")
    assert not df2.empty

def test_extra_sources_and_dedupe(app, make_user, make_project, make_file):
    u = make_user(email="e@example.com")
    p = make_project(u, "P3")
    f = make_file(u, p, filename="db.csv", file_data=b"x")
    _add_event(f, p.project_id, "A", "Submit", "Application Submitted", "2024-01-01T00:00:00Z")
    extra = [("ext", pd.DataFrame({
        "case_id": ["A", "B"],
        "activity": ["Submit", "Approve"],
        "canonical_activity": ["Application Submitted", "Approval Sent"],
        "timestamp": ["2024-01-01T00:00:00Z", "2024-01-03T00:00:00Z"],
    }))]
    df = consolidate_project_event_logs_snapshot_and_artifact(p.project_id, extra_sources=extra)
    assert "B" in df["case_id"].values

def test_nulls_and_snapshot_conversion_via_extra_sources(app, make_user, make_project, make_file):
    u = make_user(email="nulls@example.com")
    p = make_project(u, "Nulls")
    f = make_file(u, p, filename="n.csv", file_data=b"n")
    _add_event(f, p.project_id, "SAFE", "Submit", "Application Submitted", "2024-01-04T00:00:00Z")
    extra = [("ext", pd.DataFrame({
        "case_id": [None],
        "activity": [None],
        "canonical_activity": [None],
        "timestamp": ["2024-01-05T00:00:00Z"],
    }))]
    consolidate_project_event_logs_snapshot_and_artifact(p.project_id, extra_sources=extra, artifact_filename="cons.csv")
    rows = ConsolidatedEvent.query.filter_by(project_id=p.project_id).all()
    assert any(r.activity == "UNKNOWN_ACTIVITY" for r in rows)

def test_handles_empty_project_gracefully(app, make_user, make_project):
    u = make_user(email="z@example.com")
    p = make_project(u, "Empty")
    df = consolidate_project_event_logs_snapshot_and_artifact(p.project_id, artifact_filename=None)
    assert df.empty

def test_rollback_on_snapshot_error(app, make_user, make_project, make_file):
    u = make_user(email="rb@example.com")
    p = make_project(u, "RB")
    f = make_file(u, p, filename="x.csv", file_data=b"x")
    _add_event(f, p.project_id, "APP9", "Submit", "Application Submitted", "2024-01-01T00:00:00Z")
    with mock.patch("services.merge_service.db.session.execute", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            consolidate_project_event_logs_snapshot_and_artifact(p.project_id, artifact_filename="c.csv")

def test_pull_project_eventlog_df_empty(app, make_user, make_project):
    u = make_user(email="p@example.com")
    p = make_project(u, "Proj")
    df = _pull_project_eventlog_df(p.project_id)
    assert df.empty

def test_upsert_csv_artifact_new_update_reuse(app, make_user, make_project):
    u = make_user(email="f@example.com")
    p = make_project(u, "Proj")
    csv_bytes = b"case_id,activity\nA,Submit\n"
    _upsert_csv_artifact(project_id=p.project_id, user_id=u.user_id,
                         filename="c1.csv", csv_bytes=csv_bytes)
    new_bytes = b"case_id,activity\nB,Verify\n"
    _upsert_csv_artifact(project_id=p.project_id, user_id=u.user_id,
                         filename="c1.csv", csv_bytes=new_bytes)
    _upsert_csv_artifact(project_id=p.project_id, user_id=u.user_id,
                         filename="alt.csv", csv_bytes=new_bytes)
    reused = File.query.filter_by(filename="alt.csv").first()
    assert reused.file_data == new_bytes
