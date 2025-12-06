# backend/python_app/services/normalization_service.py

import re
import pandas as pd
import yaml
from typing import List, Dict, Tuple, Any
from io import BytesIO
from datetime import timedelta
from services.db import db
from services.models import File, EventLog, Project
from sqlalchemy.dialects.postgresql import insert  # <-- add

# NEW: mapping import
from services.mapping_service import canonicalize  # NEW

LOG_PATTERNS = [
    re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) '
        r'\[(?P<level>\w+)\] '
        r'(?P<activity>.+)$'
    ),
    re.compile(
        r'^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] '
        r'(?P<activity>.+)$'
    )
]

CASE_ID_PATTERN = re.compile(r'(APP\d+)')

def _parse_log_line(line: str) -> Dict[str, Any] | None:
    """
    Attempts to parse a single log line using the predefined patterns.
    Helper function intended for internal use within this service.
    """
    for pattern in LOG_PATTERNS:
        match = pattern.match(line)
        if match:
            data = match.groupdict()
            activity = data.get('activity', '').strip()
            # Search for a case ID
            case_id_match = CASE_ID_PATTERN.search(activity)
            case_id = case_id_match.group(1) if case_id_match else None
            # If a case ID was found, remove it and surrounding text from the activity
            if case_id:
                activity = re.sub(r'\s*for application ID.*', '', activity, flags=re.IGNORECASE)
            return {
                "timestamp": data['timestamp'],
                "activity": activity.strip(),
                "case_id": case_id
            }
    return None

def normalize_logs(file_paths: List[str]) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Main service function to parse multiple log files and normalize them into an event log.
    """
    events = []
    invalid_entries = []

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    parsed_data = _parse_log_line(line)
                    if parsed_data:
                        events.append(parsed_data)
                    else:
                        invalid_entries.append({
                            "file": file_path.split('/')[-1],
                            "line_number": line_num,
                            "content": line
                        })
        except Exception as e:
            invalid_entries.append({
                "file": file_path.split('/')[-1],
                "line_number": 0,
                "content": f"Error reading file: {str(e)}"
            })

    if not events:
        return pd.DataFrame(columns=['case_id', 'activity', 'timestamp']), invalid_entries

    event_log_df = pd.DataFrame(events)
    event_log_df['timestamp'] = pd.to_datetime(event_log_df['timestamp'])
    event_log_df.sort_values(by='timestamp', inplace=True, ignore_index=True)

    return event_log_df[['case_id', 'activity', 'timestamp']], invalid_entries

# ---------- NEW: helpers to persist unstructured logs the SAME way as structured ----------
def _df_from_unstructured_text(text: str) -> pd.DataFrame:  # NEW
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = _parse_log_line(line)
        if parsed:
            rows.append(parsed)
    if not rows:
        return pd.DataFrame(columns=['case_id', 'activity', 'timestamp'])
    return pd.DataFrame(rows, columns=['case_id', 'activity', 'timestamp'])

def _infer_source_from_filename(filename: str | None) -> str | None:  # NEW
    """
    Heuristic to scope mapping rules by filename hint (e.g., 'db_logs.csv' -> 'DBLogs').
    Extend this as needed.
    """
    if not filename:
        return None
    name = filename.lower()
    if name == "db_logs.csv":
        return "DBLogs"

    mapping = {
        "apigateway": "APIGateway",
        "kycservice": "KYCService",
        "creditcheck": "CreditCheck",
        "docverifier": "DocVerifier",
        "underwriter": "UnderwriterConsole",
        "payment": "PaymentGateway",
        "crm": "CRM",
        "loanprocessor": "LoanProcessor",
        "notificationservice": "NotificationService",
    }
    for k, v in mapping.items():
        if k in name:
            return v
    return None

def normalize_unstructured_file(file_id: int, source_hint: str | None = None):  # NEW
    """
    Read unstructured bytes from files.file_data, parse with _parse_log_line,
    apply canonical mapping, and store to event_log—mirrors structured path.
    """
    file_record = File.query.get(file_id)
    if not file_record:
        return f"File with ID {file_id} not found"

    try:
        raw_text = BytesIO(file_record.file_data).read().decode("utf-8", errors="ignore")
        df = _df_from_unstructured_text(raw_text)
        if df.empty:
            raise ValueError("No valid events parsed from unstructured log.")

        src = (source_hint or "").strip() or _infer_source_from_filename(file_record.filename)
        df["canonical_activity"] = df["activity"].astype(str).apply(lambda s: canonicalize(s, source=src))

        message = store_events(df, file_id) # Calls store_events function to store logs 
        file_record.status = 1
        db.session.commit()
        return f"Unstructured Log ({file_record.filename}): {message}"

    except Exception as e:
        file_record.status = 2
        db.session.commit()
        return f"Error processing Unstructured Log ({file_record.filename}): {e}"

# --- Normalization Functions (structured) ---
def normalize_event_log(file_id):
    file_record = db.session.get(File, file_id)
    if not file_record:
        print(f"ERROR: File with ID {file_id} not found.")
        return "File not found"

    try:
        df_original = pd.read_csv(BytesIO(file_record.file_data))
        df = df_original[['case_id', 'activity', 'timestamp']].copy()
        if df.empty:
            raise ValueError("No valid events found in file.")

        # NEW: canonical labels for structured event_logs.csv (no specific source)
        df["canonical_activity"] = df["activity"].astype(str).apply(lambda s: canonicalize(s, source= None))  # NEW

        message = store_events(df, file_id)
        file_record.status = 1
        db.session.commit()
        print(f"SUCCESS: Normalized {file_record.filename}. {message}")
        return f"Event Log ({file_record.filename}): {message}"

    except Exception as e:
        db.session.rollback() # Ensure rollback on error
        file_record.status = 2
        db.session.commit()
        print(f"FAILURE: Processing {file_record.filename} failed. Reason: {e}")
        return f"Error processing Event Log ({file_record.filename}): {e}"

def normalize_database_log(file_id):
    file_record = db.session.get(File, file_id)
    if not file_record:
        return f"File with ID {file_id} not found"

    try:
        df = pd.read_csv(BytesIO(file_record.file_data))

        # --- Create case_id and activity ---
        if 'case_id' not in df.columns:
            df['case_id'] = None
        if 'query' not in df.columns:
            raise ValueError("File is missing the required 'query' column for activities.")
        df = df.rename(columns={'query': 'activity'})

        event_log_df = df[['case_id', 'activity', 'timestamp']].copy()

        # NEW: canonical mapping with DBLogs scope (picks up mapping.yaml rules for db_logs.csv)
        event_log_df["canonical_activity"] = event_log_df["activity"].astype(str).apply(
            lambda s: canonicalize(s, source="DBLogs")
        )  # NEW

        # --- Store the events and update the file status ---
        message = store_events(event_log_df, file_id)
        file_record.status = 1
        db.session.commit()
        print(f"SUCCESS: Normalized {file_record.filename}. {message}")
        return f"Database Log ({file_record.filename}): {message}"

    except Exception as e:
        file_record.status = 2
        db.session.commit()
        print(f"FAILURE: Processing {file_record.filename} failed. Reason: {e}")
        return f"Error processing Database Log ({file_record.filename}): {e}"

#  --- Function to store normalised files in EventLog table ---
def store_events(df, file_id):
    """
    To prevent duplicates in eventlog table when a file is normalized again (eg. user add extra files),
    first delete all existing records associated with that file's ID and then inserts the new ones.
    """
    try:
        file_rec = db.session.get(File, file_id)
        if not file_rec:
            return f"File {file_id} not found."

        # Clear existing
        EventLog.query.filter_by(file_id=file_id).delete()

        # Prepare types
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        has_canonical = 'canonical_activity' in df.columns

        # Insert
        for _, row in df.iterrows():
            ts = row['timestamp']
            if pd.isna(ts):
                continue  # skip bad timestamps
            ev = EventLog(
                project_id=file_rec.project_id,   # <-- now valid
                file_id=file_id,
                case_id=(row.get('case_id') if pd.notna(row.get('case_id')) else None),
                activity=(str(row.get('activity')) if pd.notna(row.get('activity')) else "UNKNOWN_ACTIVITY"),
                canonical_activity=(str(row['canonical_activity']) if has_canonical and pd.notna(row['canonical_activity']) else None),
                timestamp=ts.to_pydatetime(),     # sqlalchemy handles tz-aware from pandas
            )
            db.session.add(ev)

        db.session.commit()
        return f"Successfully stored {len(df)} log events."
    except Exception as e:
        db.session.rollback()
        return f"Database error while storing events: {e}"

