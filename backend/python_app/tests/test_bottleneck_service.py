import pandas as pd
import numpy as np
import pytest
from sqlalchemy import select, func

from services.db import db
from services.models import EventLog, BottleneckMetric
from services import bottleneck_service as bs


# ----------------------------- helpers ----------------------------------------

def _add_event(*, project_id, case_id, activity=None, canonical_activity=None, ts_iso=None, file_id=None):
    """Insert an EventLog row with UTC timestamp parsing."""
    ev = EventLog(
        file_id=file_id,
        project_id=project_id,
        case_id=case_id,
        activity=activity,
        canonical_activity=canonical_activity,
        timestamp=pd.to_datetime(ts_iso, utc=True).to_pydatetime() if ts_iso else None,
    )
    db.session.add(ev)
    db.session.commit()
    return ev


# -------- _events_df_for_project ----------------------------------------------

def test_events_df_for_project_empty_returns_schema(app, make_user, make_project):
    with app.app_context():
        u = make_user()
        # FIX: do not pass unexpected kwargs like assigned_bpo_id
        p = make_project(u, "Empty Project")
        df = bs._events_df_for_project(p.project_id)
        assert list(df.columns) == ["case_id", "timestamp", "label"]
        assert df.empty


def test_events_df_label_fallback_and_sorted(app, make_user, make_project, make_file):
    with app.app_context():
        u = make_user()
        p = make_project(u, "Fallback Project")
        f = make_file(u, p, filename="x.csv", file_data=b"x")

        # canonical label should be preferred
        _add_event(project_id=p.project_id, case_id="A", activity="Submit",
                   canonical_activity="Application Submitted",
                   ts_iso="2024-01-01T00:00:00Z", file_id=f.file_id)

        # no canonical -> fallback to raw activity
        _add_event(project_id=p.project_id, case_id="A", activity="Verify",
                   canonical_activity=None,
                   ts_iso="2024-01-01T00:05:00Z", file_id=f.file_id)

        # NOTE: We do not insert an invalid row here because `event_log.activity` is NOT NULL in the DB schema.

        df = bs._events_df_for_project(p.project_id)
        # two rows; correct labels & order
        assert df.shape[0] == 2
        assert df["label"].tolist() == ["Application Submitted", "Verify"]
        assert str(df.iloc[0]["timestamp"].tz) == "UTC"
        assert df.iloc[0]["timestamp"] < df.iloc[1]["timestamp"]


# -------------------- _percentile_threshold -----------------------------------

def test_percentile_threshold_empty_series_returns_inf():
    s = pd.Series([], dtype=float)
    assert np.isinf(bs._percentile_threshold(s))


def test_percentile_threshold_computes_correct_value():
    s = pd.Series([1.0, 2.0, 3.0, 10.0])
    val = bs._percentile_threshold(s, q=0.90)
    assert val == pytest.approx(np.nanpercentile(s.to_numpy(), 90))


# ---- compute_activity_and_transition_metrics ---------------------------------

def test_compute_metrics_empty_project(app, make_user, make_project):
    with app.app_context():
        u = make_user()
        p = make_project(u, "No Data")
        act, trans = bs.compute_activity_and_transition_metrics(p.project_id, percentile=0.90)
        assert act.empty and trans.empty


def test_compute_metrics_simple_chain_stats_and_flags(app, make_user, make_project, make_file):
    with app.app_context():
        u = make_user()
        p = make_project(u, "Chain Project")
        f = make_file(u, p, filename="ev.csv", file_data=b"x")

        # Case A
        _add_event(project_id=p.project_id, case_id="A", activity="Submit",
                   canonical_activity="Application Submitted",
                   ts_iso="2024-01-01T00:00:00Z", file_id=f.file_id)
        _add_event(project_id=p.project_id, case_id="A", activity="Verify",
                   canonical_activity="Documents Verified",
                   ts_iso="2024-01-01T00:02:00Z", file_id=f.file_id)
        _add_event(project_id=p.project_id, case_id="A", activity="Approve",
                   canonical_activity="Approval Sent",
                   ts_iso="2024-01-01T00:10:00Z", file_id=f.file_id)

        # Case B with fallback label (no canonical)
        _add_event(project_id=p.project_id, case_id="B", activity="SubmitRaw",
                   canonical_activity=None,
                   ts_iso="2024-01-01T01:00:00Z", file_id=f.file_id)
        _add_event(project_id=p.project_id, case_id="B", activity="Verify",
                   canonical_activity="Documents Verified",
                   ts_iso="2024-01-01T01:03:00Z", file_id=f.file_id)

        act, trans = bs.compute_activity_and_transition_metrics(p.project_id, percentile=0.90)

        assert set(["activity","count","avg_seconds","median_seconds","p90_seconds","is_bottleneck"]).issubset(act.columns)
        assert set(["source_activity","target_activity","count","avg_seconds","median_seconds","p90_seconds","is_bottleneck"]).issubset(trans.columns)

        # Expect canonicalized labels where available
        assert "Application Submitted" in act["activity"].values
        assert "Documents Verified" in act["activity"].values
        # And fallback to raw activity where canonical is missing
        assert "SubmitRaw" in act["activity"].values

        have_pairs = set(trans[["source_activity","target_activity"]].apply(tuple, axis=1))
        assert {("Application Submitted","Documents Verified"),
                ("Documents Verified","Approval Sent"),
                ("SubmitRaw","Documents Verified")}.intersection(have_pairs)

        assert act["is_bottleneck"].dtype == bool
        assert trans["is_bottleneck"].dtype == bool


def test_compute_metrics_respects_activity_fallback_when_canonical_missing(app, make_user, make_project, make_file):
    with app.app_context():
        u = make_user()
        p = make_project(u, "Fallback Canonical")
        f = make_file(u, p, filename="ev2.csv", file_data=b"x")

        _add_event(project_id=p.project_id, case_id="X", activity="OnlyRaw",
                   canonical_activity=None,
                   ts_iso="2024-03-01T00:00:00Z", file_id=f.file_id)
        _add_event(project_id=p.project_id, case_id="X", activity="Next",
                   canonical_activity="Next",
                   ts_iso="2024-03-01T00:02:00Z", file_id=f.file_id)

        act, trans = bs.compute_activity_and_transition_metrics(p.project_id, percentile=0.90)
        assert "OnlyRaw" in act["activity"].values
        assert ("OnlyRaw","Next") in set(trans[["source_activity","target_activity"]].apply(tuple, axis=1))


# ---------------- persist_bottleneck_metrics ----------------------------------

def test_persist_bottleneck_metrics_upserts_and_clears_old(app, make_user, make_project):
    with app.app_context():
        u = make_user()
        p = make_project(u, "Persist Project")

        act_df = pd.DataFrame({
            "activity": ["A1"],
            "count": [3],
            "avg_seconds": [5.0],
            "median_seconds": [4.0],
            "p90_seconds": [9.0],
            "is_bottleneck": [True],
        })
        trans_df = pd.DataFrame({
            "source_activity": ["A1"],
            "target_activity": ["A2"],
            "count": [2],
            "avg_seconds": [7.0],
            "median_seconds": [6.0],
            "p90_seconds": [12.0],
            "is_bottleneck": [False],
        })

        bs.persist_bottleneck_metrics(p.project_id, act_df, trans_df)
        n1 = db.session.scalar(select(func.count()).select_from(BottleneckMetric))
        assert n1 == 2

        act_df2 = act_df.assign(activity=["A3"])
        trans_df2 = trans_df.assign(source_activity=["A3"])
        bs.persist_bottleneck_metrics(p.project_id, act_df2, trans_df2)
        rows = BottleneckMetric.query.filter_by(project_id=p.project_id).all()
        assert len(rows) == 2
        assert any(r.kind == "activity" and r.activity == "A3" for r in rows)
        assert any(r.kind == "transition" and r.source_activity == "A3" for r in rows)


# ---------------- compute_and_store_bottlenecks (E2E) -------------------------

def test_compute_and_store_bottlenecks_e2e(app, make_user, make_project, make_file):
    with app.app_context():
        u = make_user()
        p = make_project(u, "E2E Project")
        f = make_file(u, p, filename="ev.csv", file_data=b"x")

        _add_event(project_id=p.project_id, case_id="C", activity="Start",
                   canonical_activity="Start",
                   ts_iso="2024-02-01T00:00:00Z", file_id=f.file_id)
        _add_event(project_id=p.project_id, case_id="C", activity="Next",
                   canonical_activity="Next",
                   ts_iso="2024-02-01T00:05:00Z", file_id=f.file_id)

        a_df, t_df = bs.compute_and_store_bottlenecks(p.project_id, percentile=0.90)
        assert not a_df.empty
        assert not t_df.empty

        saved = BottleneckMetric.query.filter_by(project_id=p.project_id).all()
        kinds = {r.kind for r in saved}
        assert {"activity", "transition"}.issubset(kinds)


# ---------------- MICRO-FLOW SUBSET VALUE TEST (APPENDED) ---------------------

import math
from datetime import datetime, timezone
from sqlalchemy import select  # ensure this import exists near the top

def _utc(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)

@pytest.mark.parametrize("percentile", [0.90])
def test_subset_flow_application_accepted_to_inserted(app, make_user, make_project, make_file, percentile):
    """
    Minimal, isolated proof that bottleneck analysis captures the inefficiency between:
        'Application Accepted'  ->  'Application Inserted'

    We insert only a few synthetic cases with known deltas, run the real pipeline,
    and assert the exact activity & transition metrics for this pair.
    """
    with app.app_context():
        user = make_user()
        proj = make_project(user, "Subset Flow Project")

        # Create a real File row because event_log.file_id is NOT NULL in schema.
        f = make_file(user, proj, filename="subset_flow.csv", file_data=b"x")

        # Case A: 2 minutes
        db.session.add_all([
            EventLog(project_id=proj.project_id, file_id=f.file_id, case_id="APP_A",
                     activity="Application Accepted", canonical_activity="Application Accepted",
                     timestamp=_utc(2025, 1, 1, 10, 0, 0)),
            EventLog(project_id=proj.project_id, file_id=f.file_id, case_id="APP_A",
                     activity="Application Inserted", canonical_activity="Application Inserted",
                     timestamp=_utc(2025, 1, 1, 10, 2, 0)),
        ])

        # Case B: 10 minutes
        db.session.add_all([
            EventLog(project_id=proj.project_id, file_id=f.file_id, case_id="APP_B",
                     activity="Application Accepted", canonical_activity="Application Accepted",
                     timestamp=_utc(2025, 1, 1, 11, 0, 0)),
            EventLog(project_id=proj.project_id, file_id=f.file_id, case_id="APP_B",
                     activity="Application Inserted", canonical_activity="Application Inserted",
                     timestamp=_utc(2025, 1, 1, 11, 10, 0)),
        ])

        # Case C: also 10 minutes
        db.session.add_all([
            EventLog(project_id=proj.project_id, file_id=f.file_id, case_id="APP_C",
                     activity="Application Accepted", canonical_activity="Application Accepted",
                     timestamp=_utc(2025, 1, 1, 12, 0, 0)),
            EventLog(project_id=proj.project_id, file_id=f.file_id, case_id="APP_C",
                     activity="Application Inserted", canonical_activity="Application Inserted",
                     timestamp=_utc(2025, 1, 1, 12, 10, 0)),
        ])

        db.session.commit()

        # Run production computation with the parametrized percentile
        bs.compute_and_store_bottlenecks(proj.project_id, percentile=percentile)

        # Pull back what was saved
        rows = db.session.execute(
            select(BottleneckMetric).where(BottleneckMetric.project_id == proj.project_id)
        ).scalars().all()

        # Focus only on the rows we care about
        act_rows = [
            r for r in rows
            if r.kind == "activity" and r.activity in {"Application Accepted", "Application Inserted"}
        ]
        tr_rows = [
            r for r in rows
            if r.kind == "transition"
            and r.source_activity == "Application Accepted"
            and r.target_activity == "Application Inserted"
        ]

        # ----- Ground truth from our three cases -----
        # Durations (seconds) from 'Accepted' -> 'Inserted'
        deltas = np.array([2*60, 10*60, 10*60], dtype=float)  # [120, 600, 600]
        exp_count  = len(deltas)
        exp_avg    = deltas.mean()
        exp_median = float(np.median(deltas))
        exp_p90    = float(np.percentile(deltas, percentile * 100))

        # Activity metrics for 'Application Accepted' reflect time-until-next-step
        act_map = {r.activity: r for r in act_rows}
        assert "Application Accepted" in act_map, "Activity metrics for 'Application Accepted' missing"
        aa = act_map["Application Accepted"]

        def approx(a, b, tol=1e-6):
            return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)

        assert aa.count == exp_count
        assert approx(aa.avg_seconds, exp_avg)
        assert approx(aa.median_seconds, exp_median)
        assert approx(aa.p90_seconds, exp_p90)

        # Transition metrics for Accepted -> Inserted
        assert len(tr_rows) == 1, "Expected exactly one transition row for Accepted->Inserted"
        tr = tr_rows[0]
        assert tr.count == exp_count
        assert approx(tr.avg_seconds, exp_avg)
        assert approx(tr.median_seconds, exp_median)
        assert approx(tr.p90_seconds, exp_p90)

        # Sanity: presence/type of bottleneck flags
        assert isinstance(tr.is_bottleneck, (bool, np.bool_))
        assert isinstance(aa.is_bottleneck, (bool, np.bool_))