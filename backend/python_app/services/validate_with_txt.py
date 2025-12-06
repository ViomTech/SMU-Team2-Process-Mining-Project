from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import argparse, json, re
from datetime import datetime, timedelta

import yaml  # pip install pyyaml
from dateutil import parser as dtparse  # pip install python-dateutil

# --------------------------------------------------------------------------------------
# Paths
# This file lives in backend/python_app/services/
# mapping.yaml and runtime.yml live in backend/python_app/
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent          # .../backend/python_app/services
ROOT_DIR = BASE_DIR.parent                          # .../backend/python_app

MAPPING_PATH = ROOT_DIR / "mapping.yaml"
RUNTIME_PATH = ROOT_DIR / "runtime.yml"             # <-- fix: .yml (matches your repo)

# --------------------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------------------
@dataclass
class Event:
    ts: Optional[datetime]
    source: str
    raw: str
    message: str
    application_id: Optional[str]
    activity: Optional[str] = None  # filled after mapping

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def load_yaml(p: Path) -> Dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def try_parse_ts(s: str) -> Optional[datetime]:
    try:
        return dtparse.parse(s)
    except Exception:
        return None

def parse_line(line: str, fallback_source: str, app_rx: Optional[re.Pattern]) -> Event:
    line = line.rstrip("\n")
    # JSON line
    try:
        obj = json.loads(line)
        ts = obj.get("timestamp") or obj.get("time") or obj.get("ts")
        source = obj.get("source") or fallback_source
        message = obj.get("message") or obj.get("msg") or obj.get("log") or line
        app = obj.get("application_id") or obj.get("app_id") or obj.get("appId")
        if not app and app_rx:
            m = app_rx.search(line)
            if m:
                app = m.group(0)
        msg = re.sub(r"^\[(DEBUG|INFO|WARN|ERROR)\]\s+", "", str(message), flags=re.IGNORECASE)
        return Event(try_parse_ts(str(ts)) if ts else None, str(source), line, msg, app)
    except Exception:
        pass

    # Pipe: ts|source|message|application_id?
    if "|" in line:
        parts = [p.strip() for p in line.split("|")]
        ts = try_parse_ts(parts[0]) if parts else None
        source = parts[1] if len(parts) > 1 else fallback_source
        message = parts[2] if len(parts) > 2 else line
        app = parts[3] if len(parts) > 3 else None
        if not app and app_rx:
            m = app_rx.search(line)
            if m:
                app = m.group(0)
        msg = re.sub(r"^\[(DEBUG|INFO|WARN|ERROR)\]\s+", "", message, flags=re.IGNORECASE)
        return Event(ts, source, line, msg, app)

    # Bracketed: [ts] [source] message
    m = re.match(r"^\[(?P<ts>[^\]]+)\]\s*\[(?P<src>[^\]]+)\]\s*(?P<msg>.*)$", line)
    if m:
        ts = try_parse_ts(m.group("ts"))
        source = m.group("src") or fallback_source
        message = re.sub(r"^\[(DEBUG|INFO|WARN|ERROR)\]\s+", "", m.group("msg"), flags=re.IGNORECASE)
        app = None
        if app_rx:
            mm = app_rx.search(line)
            if mm:
                app = mm.group(0)
        return Event(ts, source, line, message, app)

    # Loose text: "YYYY-mm-dd HH:MM:SS <msg>"
    m2 = re.match(r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})\s+(?P<msg>.*)$", line)
    ts = try_parse_ts(m2.group("ts")) if m2 else None
    message = m2.group("msg") if m2 else line
    message = re.sub(r"^\[(DEBUG|INFO|WARN|ERROR)\]\s+", "", message, flags=re.IGNORECASE)
    app = None
    if app_rx:
        mm = app_rx.search(line)
        if mm:
            app = mm.group(0)
    return Event(ts, fallback_source, line, message, app)

def compile_rules(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for r in mapping.get("rules", []):
        pat = r.get("pattern", "")
        try:
            rx = re.compile(pat, re.IGNORECASE)
        except re.error as e:
            raise RuntimeError(f"Bad regex in mapping rule '{pat}': {e}")
        out.append({"source": r.get("source"), "activity": r.get("activity"), "rx": rx})
    return out

def apply_mapping(source: str, message: str, rules_compiled: List[Dict[str, Any]], default_activity: str) -> str:
    for r in rules_compiled:
        if r["source"] and r["source"] != source:
            continue
        if r["rx"].search(message):
            return r["activity"]
    return default_activity

def segment_sessions(events: List[Event], gap_minutes: int, start_activities: List[str]) -> List[List[Event]]:
    events = sorted([e for e in events if e.ts], key=lambda x: x.ts)
    sessions, cur = [], []
    last_ts: Optional[datetime] = None
    gap = timedelta(minutes=gap_minutes)
    for ev in events:
        open_new = False
        if cur and ev.activity in start_activities:
            open_new = True
        elif last_ts and (ev.ts - last_ts) > gap:
            open_new = True
        if open_new:
            sessions.append(cur)
            cur = [ev]
        else:
            cur.append(ev)
        last_ts = ev.ts
    if cur:
        sessions.append(cur)
    return sessions

def check_slas(events: List[Event], sla_map: Dict[str, float], anchors: List[str]) -> List[str]:
    errs: List[str] = []
    anchor_ev = next((e for e in events if e.activity in anchors and e.ts), None)
    if not anchor_ev:
        return errs
    for ev in events:
        if ev.activity in sla_map and ev.ts:
            dt = (ev.ts - anchor_ev.ts).total_seconds()
            if dt > float(sla_map[ev.activity]):
                errs.append(
                    f"{ev.activity} at {ev.ts} is +{int(dt)}s from {anchor_ev.activity} "
                    f"(SLA {int(sla_map[ev.activity])}s)"
                )
    return errs

# --- path resolving for --logs ---------------------------------------------------------
def resolve_logs_dir(arg: str) -> Path:
    p = Path(arg)
    if not p.is_absolute():
        p = (ROOT_DIR / arg).resolve()
    return p

def collect_log_files(log_dir: Path) -> List[Path]:
    files = sorted(list(log_dir.glob("*.txt")) + list(log_dir.glob("*.log")))
    if files:
        return files
    # fallback: try recursive if top-level empty
    files = sorted(list(log_dir.rglob("*.txt")) + list(log_dir.rglob("*.log")))
    return files

# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Validate mapping/runtime against .txt/.log files.")
    ap.add_argument("--logs", type=str, required=True, help="Path to logs folder (relative to project root or absolute)")
    ap.add_argument("--anchors", type=str, default="", help="Comma-separated SLA anchors to prefer")
    ap.add_argument("--gap-min", type=int, default=None, help="Override session gap_minutes")
    args = ap.parse_args()

    # Load config
    mapping = load_yaml(MAPPING_PATH)
    runtime = load_yaml(RUNTIME_PATH)
    default_activity = mapping.get("default_activity", "Other")
    rules_compiled = compile_rules(mapping)

    # Identifiers
    app_rx_text = (runtime.get("identifiers") or {}).get("application_id_regex") or ""
    app_rx = re.compile(app_rx_text) if app_rx_text else None

    # Session & SLA settings
    gap_minutes = int(args.gap_min if args.gap_min is not None else (runtime.get("session") or {}).get("gap_minutes", 60))
    start_activities = list((runtime.get("session") or {}).get("start_activities") or [])
    sla_map = {k: float(v) for k, v in (runtime.get("sla_offsets_sec") or {}).items()}

    forced_anchors = [a.strip() for a in args.anchors.split(",") if a.strip()]
    if forced_anchors:
        anchors = forced_anchors
    else:
        zero_sla = [k for k, v in sla_map.items() if float(v) == 0]
        anchors = list(dict.fromkeys([*start_activities, *zero_sla])) or ["Application Submitted"]

    # Logs dir & files
    log_dir = resolve_logs_dir(args.logs)
    if not log_dir.exists() or not log_dir.is_dir():
        print(f"❌ Logs directory not found: {log_dir}")
        return

    files = collect_log_files(log_dir)
    if not files:
        print(f"❌ No .txt/.log files in {log_dir}")
        return

    print(f"Scanning {len(files)} file(s) from: {log_dir}")
    for f in files:
        print(" -", f.relative_to(ROOT_DIR))

    # Read & map
    all_events: List[Event] = []
    for p in files:
        source = p.stem  # filename sans extension as source
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                ev = parse_line(line, source, app_rx)
                ev.activity = apply_mapping(ev.source, ev.message, rules_compiled, default_activity)
                all_events.append(ev)

    # Coverage overview
    total = len(all_events)
    mapped = sum(1 for e in all_events if e.activity and e.activity != default_activity)
    fallback = total - mapped
    print(f"\n== Mapping coverage ==")
    print(f"Total lines: {total} | Mapped: {mapped} | Fallback ('{default_activity}'): {fallback}")

    if fallback:
        print("\nTop 10 unmapped examples:")
        shown = 0
        for e in all_events:
            if e.activity == default_activity:
                print(f" - [{e.source}] {e.raw[:160]}")
                shown += 1
                if shown >= 10:
                    break

    # Group by file (source) because many module logs lack application_id
    print("\n== Session & SLA checks (per file/source) ==")
    by_source: Dict[str, List[Event]] = {}
    for e in all_events:
        by_source.setdefault(e.source, []).append(e)

    for source, evs in by_source.items():
        # Build sessions
        sessions = segment_sessions(evs, gap_minutes, start_activities)
        print(f"\n[{source}] sessions: {len(sessions)} (gap={gap_minutes}m, starts={start_activities or '[]'}, anchors={anchors or '[]'})")
        for i, sess in enumerate(sessions, start=1):
            errs = check_slas(sess, sla_map, anchors)
            if errs:
                print(f"  - Session {i}: SLA violations:")
                for msg in errs[:20]:
                    print(f"      * {msg}")
            else:
                print(f"  - Session {i}: OK")

    print("\n✅ Done.")

if __name__ == "__main__":
    main()
