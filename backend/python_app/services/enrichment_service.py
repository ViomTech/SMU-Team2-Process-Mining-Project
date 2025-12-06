from datetime import timedelta
import pandas as pd
from sqlalchemy.orm import joinedload

from services.models import db, EventLog
from services.mapping_service import canonicalize # Use the central mapping service

# --- CONFIGURATION DICTIONARIES ---   

# A map of canonical activities to their expected time windows for enrichment.
ACTIVITY_TIME_WINDOWS = {
    # --- Instant / Automated Events (Short Window) ---
    # These events happen immediately after a trigger.
    "Customer Profile Queried": timedelta(minutes=5),
    "Loan Status Updated": timedelta(minutes=5),
    "Underwriting Approved": timedelta(minutes=5),

    "KYC Lookup Start": timedelta(minutes=15),
    "KYC Verification Initiated": timedelta(minutes=15),
    "PAN Validation Initiated": timedelta(minutes=15),

    "Application Submitted": timedelta(minutes=30),
    "Application Accepted": timedelta(minutes=30),
    "Application Inserted": timedelta(minutes=30),
    "Fetch Credit Report": timedelta(minutes=30),
    "Property Verified": timedelta(minutes=30),
    "Processing Fee Payment Initiated": timedelta(minutes=30),
    "Processing Fee Payment Confirmed": timedelta(minutes=30),

    "Email Sent": timedelta(hours=1),
    "SMS Sent": timedelta(hours=1),
    "Push Sent": timedelta(hours=1),

    # --- Quick Follow-up Steps (Medium Window) ---
    # These are often the next logical steps in the process, happening within hours.
    "Customer Profile Created": timedelta(hours=1),
    "KYC Completed": timedelta(hours=1),
    "Approval Sent": timedelta(hours=1),
    "Credit Check Completed": timedelta(hours=1),
    "Sanction Letter Updated": timedelta(hours=1),

    "Credit Score Updated": timedelta(hours=4),
    "Application Validated": timedelta(hours=4),
    "Temporary Documents Cleanup": timedelta(hours=4),

    "Documents Scanned": timedelta(hours=12),
    "Documents Verified": timedelta(hours=12),

    "Aadhaar/PAN KYC Check": timedelta(days=1),
    
    # --- Human-Driven / Long Delays (Long Window) ---
    # These steps often involve manual work or waiting for external systems.
    "Property Verification Initiated": timedelta(days=3),
    "Underwriter Review": timedelta(days=3),
    "Underwriter Decision Note": timedelta(days=3),

    "Credit Check (CIBIL)": timedelta(days=2),
    # "Credit Report Fetched": timedelta(days=2), Commented out cos it's now "Fetch Credit Report"
    "Credit Check Completed" : timedelta(days=2),
    "Risk Analysis & Eligibility": timedelta(days=2),

    # --- Statuses & Mismatches (Variable Window) ---
    # These can happen at various points, so a general window is often best.
    #"Set Status = Under Review": timedelta(hours=8),
    "KYC Mismatch (PAN)": timedelta(hours=8),
    "Score Below Threshold": timedelta(hours=8),

    # --- NEW, DATA-DRIVEN WINDOWS ---
    "Loan Disbursed": timedelta(days=2), # Actual was 1 day, giving a buffer
    "Sanction Letter Issued": timedelta(hours=12),
    "Post-Disbursal Compliance & EMI Setup": timedelta(days=3),
}

# A default window for any activity not listed above.
DEFAULT_TIME_WINDOW = timedelta(days=1)

# A map of "child" activities to their "parent" anchor event.
# It tells the function, "For this specific 'child' event, don't look for an event with the same name; look for its 'parent' instead." - condition 1 can/may meet
# A map of "child" activities to their "parent" anchor event.
CHILD_PARENT_MAP = {
    # --- Application & Profile Children ---
    'Customer Profile Created': 'Application Submitted',
    'Contact Info Updated': 'Application Submitted',
    'Customer Profile Queried': 'Application Submitted',
    'CRM Sync': 'Application Submitted',
    #'Application Validated': 'Application Submitted',

    # --- KYC & Document Children (All now point to a stronger anchor) ---
    'Aadhaar/PAN KYC Check': 'Customer Profile Created', 
    'Documents Scanned': 'Customer Profile Created',       
    'Documents Verified': 'Documents Scanned', 
    'KYC Mismatch (PAN)': 'Aadhaar/PAN KYC Check',
    'PAN Validation Failed': 'Aadhaar/PAN KYC Check',
    'Verification passed': 'Documents Verified',
    'Mismatch found in PAN': 'Documents Verified',
    'KYC Completed': 'KYC Verification Initiated',

    # --- Credit Check Children ---
    'Application Validated': 'Credit Check (CIBIL)',
    'Credit Report Fetched': 'Credit Check (CIBIL)',
    'Score Below Threshold': 'Credit Check (CIBIL)',
    'Credit Score Updated': 'Credit Check (CIBIL)',
    'Loan risk analysis complete': 'Credit Check (CIBIL)',
    'Credit Check Completed': 'Credit Check (CIBIL)',

    # --- Underwriting & Approval Children ---
    'Property Verification': 'Underwriter Review',
    'Loan approval sent': 'Underwriter Decision Note',
    'Sanction Letter Issued': 'Underwriter Decision Note',
    'Sanction Letter Updated': 'Underwriter Decision Note',

    # --- Post-Approval & System Children ---
    'Temporary Documents Cleanup': 'Loan Disbursed',

    # --- Notification & Status Outcomes (Many-to-One) ---
    'Loan Status Updated': [
        'Documents Verified',
        'Underwriter Decision Note',
        'Loan Disbursed',
        'Aadhaar/PAN KYC Check'
    ],
    'Email Sent': [
        'Application Submitted',
        'Underwriter Decision Note',
        'Processing Fee Payment Confirmed',
        'Aadhaar/PAN KYC Check'
    ],
    'SMS Sent': [
        'Application Submitted',
        'Underwriter Decision Note',
        'Processing Fee Payment Confirmed',
        'Aadhaar/PAN KYC Check'
    ],
    'Push Sent': [
        'Application Submitted',
        'Underwriter Decision Note',
        'Processing Fee Payment Confirmed'
    ]
}

def enrich_case_ids(project_id: int):
    """
    Fills in missing case_ids. Returns a status dictionary.
    This version is optimized to run in memory for performance.
    """
    # --- Initial State Check ---
    anchor_query = db.session.query(EventLog).filter(
        EventLog.project_id == project_id, EventLog.case_id.isnot(None)
    )
    unidentified_query = db.session.query(EventLog).filter(
        EventLog.project_id == project_id, EventLog.case_id.is_(None)
    )

    if not db.session.query(unidentified_query.exists()).scalar():
        return {"status": "NO_WORK", "message": "No events to enrich.", "count": 0}

    # --- THIS IS THE NEW LOGIC ---
    # If there's no rows with case_id, exit.
    if not db.session.query(anchor_query.exists()).scalar():
        print("--- Enrichment skipped: No anchor events with case_ids found. ---")
        return {
            "status": "NO_ANCHORS",
            "message": "Enrichment requires at least one event with a case ID.",
            "count": 0,
        }
    
    # 1. Load data from DB ONCE before the loop
    anchor_df = pd.read_sql(anchor_query.statement, db.engine)
    unidentified_df = pd.read_sql(unidentified_query.statement, db.engine)
    anchor_df['timestamp'] = pd.to_datetime(anchor_df['timestamp'])
    unidentified_df['timestamp'] = pd.to_datetime(unidentified_df['timestamp'])

    all_updates = {}
    
    while True:
        if unidentified_df.empty:
            break

        updates_in_this_pass = {}
        for index, event in unidentified_df.iterrows():
            
            activity_name = event['canonical_activity']
            time_window = ACTIVITY_TIME_WINDOWS.get(activity_name, DEFAULT_TIME_WINDOW)
            target_parents = CHILD_PARENT_MAP.get(activity_name, activity_name)
            
            # Condition 1: The activity name must be an exact match. Condition 2: The timestamp must be within a 5-minute window
            if isinstance(target_parents, list):
                match_condition = anchor_df['canonical_activity'].isin(target_parents)
            else:
                match_condition = (anchor_df['canonical_activity'] == target_parents)
            
            start_time = event['timestamp'] - time_window
            end_time = event['timestamp'] + time_window
            
            potential_matches = anchor_df[
                match_condition & (anchor_df['timestamp'].between(start_time, end_time))
            ]
            
            # Confidence check
            if not potential_matches.empty and potential_matches['case_id'].nunique() == 1:
                updates_in_this_pass[event['event_id']] = potential_matches['case_id'].iloc[0]

        if not updates_in_this_pass:
            break # No more matches can be found, exit the loop

        # 2. Update DataFrames IN MEMORY for the next pass (the "ripple effect")
        
        # Get the event_ids that were just updated
        updated_ids = list(updates_in_this_pass.keys())
        
        # Find the full rows from the unidentified_df
        newly_enriched_rows = unidentified_df[unidentified_df['event_id'].isin(updated_ids)].copy()
        
        # Assign the new case_ids to these rows
        newly_enriched_rows['case_id'] = newly_enriched_rows['event_id'].map(updates_in_this_pass)
        
        # "Promote" these rows by adding them to the anchor_df for the next loop
        anchor_df = pd.concat([anchor_df, newly_enriched_rows], ignore_index=True)
        
        # Remove these rows from the unidentified_df so we don't process them again
        unidentified_df = unidentified_df[~unidentified_df['event_id'].isin(updated_ids)]
        
        # Store all updates for the final database commit
        all_updates.update(updates_in_this_pass)
        print(f"Enriched {len(updates_in_this_pass)} events in this pass...")

    # 3. Commit all changes to the database ONCE at the end
    if all_updates:
        for event_id, case_id in all_updates.items():
            db.session.query(EventLog).filter(EventLog.event_id == event_id).update({"case_id": case_id})
        db.session.commit()
        
        message = f"Successfully enriched a total of {len(all_updates)} events."
        print(f"--- {message} ---")
        return {"status": "SUCCESS", "message": message, "count": len(all_updates)}
    else:
        message = "No new confident case ID matches were found."
        print(f"--- {message} ---")
        return {"status": "NO_MATCHES", "message": message, "count": 0}

# def enrich_case_ids(project_id: int):
#     """
#     Fills in missing case_ids using a looping, multi-stage approach
#     that handles both single and multiple possible parent activities.
#     """    
#     total_enriched_count = 0
    
#     # --- Initial State Check ---
#     anchor_query = db.session.query(EventLog).filter(
#         EventLog.project_id == project_id,
#         EventLog.case_id.isnot(None)
#     )
#     unidentified_query = db.session.query(EventLog).filter(
#         EventLog.project_id == project_id,
#         EventLog.case_id.is_(None)
#     )

#     has_anchors = db.session.query(anchor_query.exists()).scalar()
#     has_unidentified = db.session.query(unidentified_query.exists()).scalar()

#     # 👇 --- THIS IS THE NEW LOGIC ---
#     # If there's nothing to enrich, stop early.
#     if not has_unidentified:
#         return {"status": "NO_WORK", "message": "No events to enrich.", "count": 0}

#     # If there's work to do but no anchors, stop and report the problem.
#     if not has_anchors:
#         print("--- Enrichment failed: No anchor events with case_ids found. ---")
#         return {
#             "status": "NO_ANCHORS",
#             "message": "Enrichment requires at least one file containing events with a case ID. Please upload a file with case_id.",
#             "count": 0
#         }

#     # If we pass the checks, proceed with the enrichment loop...   
#     # Each pass through the while loop expands your pool of "known" anchor events, which creates a ripple effect.
#     while True:
#         anchor_query = db.session.query(EventLog).filter(
#             EventLog.project_id == project_id,
#             EventLog.case_id.isnot(None)
#         )
#         anchor_df = pd.read_sql(anchor_query.statement, db.engine)
        
#         unidentified_query = db.session.query(EventLog).filter(
#             EventLog.project_id == project_id,
#             EventLog.case_id.is_(None)
#         )
#         unidentified_df = pd.read_sql(unidentified_query.statement, db.engine)

#         if unidentified_df.empty:
#             break

#         updates_in_this_pass = {}

#         for index, event in unidentified_df.iterrows():
#             activity_name = event['canonical_activity']
#             time_window = ACTIVITY_TIME_WINDOWS.get(activity_name, DEFAULT_TIME_WINDOW)
            
#             # This can now be a single string OR a list of strings
#             target_parents = CHILD_PARENT_MAP.get(activity_name, activity_name)

#             # Condition 1: The activity name must be an exact match
#             if isinstance(target_parents, list):
#                 # If the target is a list, use .isin() to check for any of the parents
#                 match_condition = anchor_df['canonical_activity'].isin(target_parents)
#             else:
#                 # Otherwise, use the standard equality check
#                 match_condition = (anchor_df['canonical_activity'] == target_parents)
            
#             # Combine the match condition with the time window
#             potential_matches = anchor_df[
#                 match_condition &
#                 (abs(anchor_df['timestamp'] - event['timestamp']) <= time_window) # Condition 2: The timestamp must be within a 5-minute window
#             ]
            
#             # Confidence check
#             if not potential_matches.empty and potential_matches['case_id'].nunique() == 1:
#                 updates_in_this_pass[event['event_id']] = potential_matches['case_id'].iloc[0]

#         if not updates_in_this_pass:
#             break

#         for event_id, case_id in updates_in_this_pass.items():
#             db.session.query(EventLog).filter(EventLog.event_id == event_id).update({"case_id": case_id})
#         db.session.commit()
        
#         pass_count = len(updates_in_this_pass)
#         total_enriched_count += pass_count
#         print(f"Enriched {pass_count} events in this pass...")

#     if total_enriched_count > 0:
#         print(f"--- Successfully enriched a total of {total_enriched_count} events. ---")
#     else:
#         print("--- No confident case ID matches were found. ---")
        
#     return total_enriched_count

# # OLD (without multi-stage parent-child mapping)
# def enrich_case_ids(project_id: int):
#     """
#     Fills in missing case_ids by matching timestamps of
#     events that now share the same canonical activity name.
#     """
#     print(f"--- Starting Case ID Enrichment for project ID: {project_id} ---")

#     # 1. Fetch anchor and unidentified logs
#     anchor_query = db.session.query(EventLog).filter(
#         EventLog.project_id == project_id,
#         EventLog.case_id.isnot(None),
#         EventLog.canonical_activity.isnot(None)
#     )
#     anchor_df = pd.read_sql(anchor_query.statement, db.engine)

#     unidentified_query = db.session.query(EventLog).filter(
#         EventLog.project_id == project_id,
#         EventLog.case_id.is_(None),
#         EventLog.canonical_activity.isnot(None)
#     )
#     unidentified_df = pd.read_sql(unidentified_query.statement, db.engine)

#     # 2. Perform heuristic matching
#     updates_to_make = {}
#     time_window = timedelta(minutes=120)

#     for index, event in unidentified_df.iterrows():
        
#         # Look up the specific time window for this activity
#         activity_name = event['canonical_activity']
#         time_window = ACTIVITY_TIME_WINDOWS.get(activity_name, DEFAULT_TIME_WINDOW)

#         # Use this dynamic time_window in the filter
#         potential_matches = anchor_df[
#             (anchor_df['canonical_activity'] == activity_name) & # Condition 1: The activity name must be an exact match
#             (abs(anchor_df['timestamp'] - event['timestamp']) <= time_window) # Condition 2: The timestamp must be within a 5-minute window
#         ]
        
#         # Confidence check remains the same
#         if not potential_matches.empty and potential_matches['case_id'].nunique() == 1:
#             updates_to_make[event['event_id']] = potential_matches['case_id'].iloc[0]

#     # 3. Update the database
#     if updates_to_make:
#         for event_id, case_id in updates_to_make.items():
#             db.session.query(EventLog).filter(EventLog.event_id == event_id).update({"case_id": case_id})
#         db.session.commit()
#         print(f"Successfully enriched {len(updates_to_make)} events.")
#     else:
#         print("No confident case ID matches were found.")
    
#     return len(updates_to_make)