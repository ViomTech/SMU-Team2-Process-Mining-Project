# backend/python_app/services/merge_core.py
from __future__ import annotations
import pandas as pd
from typing import Iterable, Tuple, List

REQUIRED_COLS = ["case_id", "activity", "timestamp"]
OPTIONAL_CANON = "canonical_activity"

def _standardize(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Standardize to canonical schema & types."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["case_id","activity","canonical_activity","timestamp","source"])

    out = df.copy()

    # rename variants to lower
    rename_map = {}
    for c in df.columns:
        lc = c.lower()
        if lc in ["case_id","activity","timestamp","canonical_activity"]:
            rename_map[c] = lc
    out = out.rename(columns=rename_map)

    # ensure columns exist
    for c in REQUIRED_COLS:
        if c not in out.columns:
            out[c] = None
    if OPTIONAL_CANON not in out.columns:
        out[OPTIONAL_CANON] = None

    # types
    out["case_id"] = out["case_id"].astype("string").fillna("CASE_UNKNOWN")
    out["activity"] = out["activity"].astype("string").fillna("UNKNOWN_ACTIVITY")
    out["canonical_activity"] = out["canonical_activity"].astype("string")
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)

    # add source & filter bad timestamps
    out["source"] = source_name
    out = out.dropna(subset=["timestamp"])

    return out[["case_id","activity","canonical_activity","timestamp","source"]]

def merge_normalized_sources(
    named_sources: Iterable[Tuple[str, pd.DataFrame]],
    dedup_on: List[str] | None = None
) -> pd.DataFrame:
    """Combine, standardize, drop duplicates, sort => consolidated event log."""
    if dedup_on is None:
        # de-dupe across sources using canonical_activity if present; fall back to activity
        dedup_on = ["case_id","timestamp","canonical_activity","activity"]

    standardized = [
        _standardize(df, src) for (src, df) in named_sources
        if df is not None and len(df) > 0
    ]
    if not standardized:
        return pd.DataFrame(columns=["case_id","activity","canonical_activity","timestamp","source"])

    merged = pd.concat(standardized, ignore_index=True)
    merged = merged.sort_values(by=["timestamp","case_id","canonical_activity","activity"], kind="stable")
    merged = merged.drop_duplicates(subset=dedup_on, keep="first", ignore_index=True)

    return merged[["case_id","activity","canonical_activity","timestamp","source"]]