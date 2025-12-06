# mapping_service.py (hardened for prod)
from __future__ import annotations
import os, re, yaml
from functools import lru_cache
from typing import Optional, Dict, Any, List

def _candidate_paths() -> list[str]:
    env_path = os.getenv("MAPPING_YAML_PATH")
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    return [p for p in [
        env_path,
        os.path.join(here, "mapping.yaml"),
        os.path.join(cwd, "mapping.yaml"),
        "/opt/app/mapping.yaml",
        "/opt/app/TripleThreatx2/backend/python_app/mapping.yaml",
    ] if p]

def _first_existing(paths: list[str]) -> Optional[str]:
    for p in paths:
        try:
            if p and os.path.isfile(p):
                return p
        except Exception:
            pass
    return None

@lru_cache(maxsize=1)
def _load_yaml() -> Dict[str, Any]:
    path = _first_existing(_candidate_paths())
    if not path:
        # log once so you can see this in journalctl
        print("[mapping] mapping.yaml NOT FOUND in candidates:", _candidate_paths())
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            print(f"[mapping] loaded mapping.yaml from: {path} (rules={len(data.get('rules') or [])})")
            return data
    except Exception as e:
        print(f"[mapping] failed to read {path}: {e}")
        return {}

def reload_mapping_rules() -> None:
    """Call this after deploying a new mapping file or changing MAPPING_YAML_PATH."""
    _load_yaml.cache_clear()
    load_rules.cache_clear()
    _load_yaml()  # repopulate once

@lru_cache(maxsize=1)
def load_rules() -> Dict[str, Any]:
    data = _load_yaml()
    compiled: List[Dict[str, Any]] = []
    for r in (data.get("rules") or []):
        patt = r.get("pattern")
        if not patt:
            continue
        try:
            rx = re.compile(patt, re.IGNORECASE)
        except re.error:
            print(f"[mapping] invalid regex skipped: {patt}")
            continue
        compiled.append({
            "source": (r.get("source") or "").strip() or None,
            "pattern": rx,
            "activity": r.get("activity"),
        })
    return {
        "rules": compiled,
        "default_activity": (data.get("default_activity") or "activity_raw"),
    }

def canonicalize(activity_raw: str, source: Optional[str]) -> str:
    cfg = load_rules()
    rules = cfg["rules"]
    default_activity = cfg["default_activity"]
    text = activity_raw or ""
    src = (source or "").lower()
    for r in rules:
        rsrc = (r["source"] or "").lower()
        if rsrc and src and rsrc != src:
            continue
        if r["pattern"].search(text):
            return r.get("activity") or text
    return text if default_activity == "activity_raw" else default_activity
