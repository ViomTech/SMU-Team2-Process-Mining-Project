# backend/python_app/services/fake_data.py
import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path
# Optional: if you later want to read runtime.yml, uncomment the next line and use yaml.safe_load
# import yaml

# --- Path setup -------------------------------------------------------------
# This file lives in backend/python_app/services/
# mapping.yaml and runtime.yml live in backend/python_app/
SERVICES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVICES_DIR.parent  # -> backend/python_app

MAPPING_PATH = PROJECT_ROOT / "mapping.yaml"
RUNTIME_PATH = PROJECT_ROOT / "runtime.yml"

# You can print/log these if needed for debugging:
# print("MAPPING_PATH:", MAPPING_PATH)
# print("RUNTIME_PATH:", RUNTIME_PATH)

# fake_data.py
SAMPLE_LOGS_DIR = PROJECT_ROOT / "sample_logs"              # .../backend/python_app/sample_logs
MOCK_DATA_DIR   = PROJECT_ROOT / "mock_data"                # .../backend/python_app/mock_data

mock = pd.read_csv(MOCK_DATA_DIR / "home_loan_mock_data_5000_final.csv", low_memory=False)
mock["application_date"] = pd.to_datetime(mock["application_date"], errors="coerce")
mock = mock.dropna(subset=["application_date"]).reset_index(drop=True)

# Limit to first 50
mock50 = mock.head(50).copy()
mock50["case_id"] = ["APP{:05d}".format(i+1) for i in range(len(mock50))]
mock50["customer_id"] = ["CUST{:05d}".format(i+1) for i in range(len(mock50))]

# helper to fetch safe value
def getval(row, colname, default=None):
    return row[colname] if colname in row and pd.notna(row[colname]) else default

# --- Offsets (seconds) ------------------------------------------------------
# NOTE: Kept inline for now. Labels are updated to match mapping.yaml.
VAL_TO_RISK = 2520
RISK_TO_APPROVAL = 12540
PAY_I_TO_C = 2

OFFSETS = {
    "Application Submitted": 0,
    "Customer Profile Created": 5*60,
    "Aadhaar/PAN KYC Check": 60*60,
    "Documents Scanned": int(1.5*60*60),
    "Documents Verified": int(3*60*60),
    "Credit Check (CIBIL)": int(6*60*60),
    "Property Verification": int(28*60*60),
    "Validation Queue Wait": 60*60,
    "Risk Analysis & Eligibility": VAL_TO_RISK,
    "Set Status = Under Review": 5*60,
    "Underwriter Review": int(2*60*60),
    "Approval Sent": RISK_TO_APPROVAL,
    "Sanction Letter Issued": 30*60,
    "Processing Fee Payment Initiated": 30*60,
    "Processing Fee Payment Confirmed": PAY_I_TO_C,
    "Disbursed": int(24*60*60),

    # Canonical notification labels from mapping.yaml:
    # We'll emit three "Email Sent" events at different milestones.
    "Email Sent (post-approval)": 5*60,
    "Email Sent (post-payment-confirmed)": 5*60,
    "Email Sent (post-disbursed)": 5*60,

    "Post-Disbursal Compliance & EMI Setup": int(48*60*60),
}

# --- Sources (align to mapping.yaml where possible) -------------------------
SOURCES = {
    "Application Submitted": "APIGateway",
    "Customer Profile Created": "CRM",
    "Aadhaar/PAN KYC Check": "KYCService",       # source in mapping.yaml uses KYCService
    "Documents Scanned": "DocVerifier",
    "Documents Verified": "DocVerifier",
    "Credit Check (CIBIL)": "CreditCheck",
    "Property Verification": "PropertyVerifier",  # not in mapping rules; fine to keep
    "Application Validated": "LoanProcessor",
    "Risk Analysis & Eligibility": "LoanProcessor",
    "Set Status = Under Review": "APIGateway",
    "Underwriter Review": "UnderwriterConsole",
    "Approval Sent": "LoanProcessor",
    "Sanction Letter Issued": "LoanProcessor",
    "Processing Fee Payment Initiated": "PaymentGateway",
    "Processing Fee Payment Confirmed": "PaymentGateway",
    "Disbursed": "LoanProcessor",
    "Email Sent": "NotificationService",          # canonical label
    "Post-Disbursal Compliance & EMI Setup": "LoanProcessor",
}

rows = []
for _, r in mock50.iterrows():
    case_id = r["case_id"]
    cust_id = r["customer_id"]
    t0 = r["application_date"]

    # parallel maxima for join
    t_kyc = t0 + timedelta(seconds=OFFSETS["Aadhaar/PAN KYC Check"])
    t_doc_scan = t0 + timedelta(seconds=OFFSETS["Documents Scanned"])
    t_doc_ver = t0 + timedelta(seconds=OFFSETS["Documents Verified"])
    t_cibil = t0 + timedelta(seconds=OFFSETS["Credit Check (CIBIL)"])
    t_prop = t0 + timedelta(seconds=OFFSETS["Property Verification"])
    parallel_done = max(t_kyc, t_doc_ver, t_cibil, t_prop)

    t_valid = parallel_done + timedelta(seconds=OFFSETS["Validation Queue Wait"])
    t_risk_start = t_valid
    t_risk_done = t_risk_start + timedelta(seconds=OFFSETS["Risk Analysis & Eligibility"])
    t_under_review = t_risk_start + timedelta(seconds=OFFSETS["Set Status = Under Review"])
    t_uw = t_risk_start + timedelta(seconds=OFFSETS["Underwriter Review"])
    t_approval = t_risk_done + timedelta(seconds=OFFSETS["Approval Sent"])
    t_sanction = t_approval + timedelta(seconds=OFFSETS["Sanction Letter Issued"])
    t_pay_i = t_sanction + timedelta(seconds=OFFSETS["Processing Fee Payment Initiated"])
    t_pay_c = t_pay_i + timedelta(seconds=OFFSETS["Processing Fee Payment Confirmed"])
    t_disb = t_pay_c + timedelta(seconds=OFFSETS["Disbursed"])

    # Canonical "Email Sent" moments (three separate emails, same label)
    t_email_after_approval = t_approval + timedelta(seconds=OFFSETS["Email Sent (post-approval)"])
    t_email_after_payment = t_pay_c + timedelta(seconds=OFFSETS["Email Sent (post-payment-confirmed)"])
    t_email_after_disb = t_disb + timedelta(seconds=OFFSETS["Email Sent (post-disbursed)"])

    t_post = t_disb + timedelta(seconds=OFFSETS["Post-Disbursal Compliance & EMI Setup"])

    # Sequence with labels aligned to mapping.yaml
    seq = [
        ("Application Submitted", t0),
        ("Customer Profile Created", t0 + timedelta(seconds=OFFSETS["Customer Profile Created"])),
        ("Aadhaar/PAN KYC Check", t_kyc),
        ("Documents Scanned", t_doc_scan),
        ("Documents Verified", t_doc_ver),
        ("Credit Check (CIBIL)", t_cibil),
        ("Property Verification", t_prop),
        ("Application Validated", t_valid),                # canonical
        ("Risk Analysis & Eligibility", t_risk_done),
        ("Set Status = Under Review", t_under_review),
        ("Underwriter Review", t_uw),
        ("Approval Sent", t_approval),
        ("Sanction Letter Issued", t_sanction),
        ("Processing Fee Payment Initiated", t_pay_i),
        ("Processing Fee Payment Confirmed", t_pay_c),
        ("Disbursed", t_disb),
        ("Email Sent", t_email_after_approval),            # canonical
        ("Email Sent", t_email_after_payment),             # canonical
        ("Email Sent", t_email_after_disb),                # canonical
        ("Post-Disbursal Compliance & EMI Setup", t_post),
    ]

    # enrich with outputs if present
    enrich = {
        "risk_grade": getval(r, "risk_grade"),
        "eligibility_status": getval(r, "eligibility_status"),
        "sanction_letter_issued": getval(r, "sanction_letter_issued"),
        "disbursal_amount": getval(r, "disbursal_amount"),
        "disbursal_date": pd.to_datetime(getval(r, "disbursal_date"), errors="coerce"),
        "status": getval(r, "status"),
        "underwriter_comments": getval(r, "underwriter_comments"),
    }

    for act, ts in seq:
        row = {
            "case_id": case_id,
            "customer_id": cust_id,
            "activity": act,
            "timestamp": ts,
            "source": SOURCES.get(act, SOURCES.get("Email Sent", "System") if act == "Email Sent" else "System"),
            "reference": "mock_anchored_e2e",
        }
        # attach relevant enrichment at key steps
        if act in ["Risk Analysis & Eligibility", "Approval Sent", "Sanction Letter Issued", "Disbursed", "Post-Disbursal Compliance & EMI Setup"]:
            row.update(enrich)
        rows.append(row)

reconstructed = pd.DataFrame(rows).sort_values(["case_id","timestamp"]).reset_index(drop=True)

outpath = PROJECT_ROOT / "reconstructed_event_log.csv"
reconstructed.to_csv(outpath, index=False)

str(outpath)
