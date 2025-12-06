import pandas as pd
import pytest
from services.merge_core import _standardize, merge_normalized_sources

def test_standardize_handles_missing_and_defaults():
    df = pd.DataFrame({
        "Case_ID": ["A", None, "C"],
        "Activity": ["Submit", "Verify", None],
        "Timestamp": ["2024-01-01T00:00:00Z", "bad", "2024-01-01T00:05:00Z"],
        "canonical_activity": ["Application Submitted", None, "Documents Verified"],
    })
    out = _standardize(df, "src")
    assert len(out) == 2
    assert set(out.columns) == {"case_id","activity","canonical_activity","timestamp","source"}

def test_standardize_empty_returns_schema():
    out = _standardize(pd.DataFrame(), "s")
    assert list(out.columns) == ["case_id","activity","canonical_activity","timestamp","source"]
    assert out.empty

def test_standardize_adds_defaults_for_missing():
    df = pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z", None]})
    out = _standardize(df, "mysrc")
    assert len(out) == 1
    row = out.iloc[0]
    assert row["case_id"] == "CASE_UNKNOWN"
    assert row["activity"] == "UNKNOWN_ACTIVITY"
    assert pd.isna(row["canonical_activity"])

def test_standardize_with_none_source():
    out = _standardize(None, "mysrc")
    assert out.empty

def test_standardize_mixed_case_columns_and_types():
    df = pd.DataFrame({
        "CASE_ID": ["APP1"],
        "Activity": ["Approve"],
        "Timestamp": [pd.to_datetime("2024-01-03T00:00:00Z")],
        "canonical_activity": [None],
    })
    out = _standardize(df, "Db")
    assert out.iloc[0]["source"] == "Db"
    assert pd.isna(out.iloc[0]["canonical_activity"])

def test_merge_merges_and_dedupes_and_sorts():
    df1 = pd.DataFrame({
        "case_id": ["A","A","B"],
        "activity": ["Submit","Submit","Verify"],
        "canonical_activity": ["Application Submitted","Application Submitted","Documents Verified"],
        "timestamp": ["2024-01-01T00:00:00Z","2024-01-01T00:00:00Z","2024-01-02T00:00:00Z"],
    })
    df2 = pd.DataFrame({
        "CASE_ID": ["A","C"],
        "Activity": ["Submit","Approve"],
        "Timestamp": ["2024-01-01T00:00:00Z","2024-01-03T00:00:00Z"],
        "canonical_activity": ["Application Submitted", "Approval Sent"],
    })
    merged = merge_normalized_sources([("s1", df1), ("s2", df2)])
    assert len(merged) == 3
    assert list(merged["case_id"]) == ["A","B","C"]

def test_merge_custom_dedup_on_fewer_keys():
    df = pd.DataFrame({
        "case_id": ["A","A","A"],
        "activity": ["a1","a1","a2"],
        "canonical_activity": ["X","X","Y"],
        "timestamp": ["2024-01-01T00:00:00Z"]*3,
    })
    merged = merge_normalized_sources([("s", df)], dedup_on=["case_id","timestamp"])
    assert len(merged) == 1

@pytest.mark.parametrize("sources", [
    [("s1", pd.DataFrame(columns=["case_id","activity","timestamp"])), ("s2", None)],
    [],
])
def test_merge_empty_sources(sources):
    merged = merge_normalized_sources(sources)
    assert merged.empty
