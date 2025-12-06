import textwrap
import pytest
import services.mapping_service as ms

def _write_tmp_mapping(tmp_path, yaml_text):
    p = tmp_path / "mapping.yaml"
    p.write_text(textwrap.dedent(yaml_text), encoding="utf-8")
    return str(p)

def _reload_with(monkeypatch, path):
    ms._load_yaml.cache_clear()
    ms.load_rules.cache_clear()
    monkeypatch.setattr(
        ms,
        "load_rules",
        lambda path=path, _orig=ms.load_rules: _orig(path),
        raising=False,
    )

def test_load_rules_compiles_and_skips_invalid(tmp_path, monkeypatch):
    path = _write_tmp_mapping(tmp_path, """
      default_activity: Application Submitted
      rules:
        - source: db
          pattern: "("        # invalid regex -> skipped
          activity: bad
        - source: db
          pattern: "submit"
          activity: "Application Submitted"
        - pattern: "verify"
          activity: "Documents Verified"
    """)
    _reload_with(monkeypatch, path)
    cfg = ms.load_rules()
    assert cfg["default_activity"] == "Application Submitted"
    assert len(cfg["rules"]) == 2

def test_canonicalize_respects_source_and_global(tmp_path, monkeypatch):
    path = _write_tmp_mapping(tmp_path, """
      default_activity: Application Submitted
      rules:
        - source: "db"
          pattern: "submitted"
          activity: "Application Submitted"
        - source: "api"
          pattern: "submitted"
          activity: "API Submit"
        - source: "   "
          pattern: "approve"
          activity: "Approval Sent"
        - pattern: "verify"
          activity: "Documents Verified"
    """)
    _reload_with(monkeypatch, path)
    assert ms.canonicalize("SUBMITTED now", "db") == "Application Submitted"
    assert ms.canonicalize("submitted then", "api") == "API Submit"
    assert ms.canonicalize("please APPROVE", "anysrc") == "Approval Sent"
    assert ms.canonicalize("approve now", None) == "Approval Sent"

@pytest.mark.parametrize("default_val,expected", [
    ("Unknown", "Unknown"),
    ("activity_raw", "Some Raw Label"),
])
def test_canonicalize_default_behaviors(tmp_path, monkeypatch, default_val, expected):
    path = _write_tmp_mapping(tmp_path, f"""
      default_activity: {default_val}
      rules: []
    """)
    _reload_with(monkeypatch, path)
    assert ms.canonicalize("Some Raw Label", None) == expected

def test_rule_missing_activity_returns_raw(tmp_path, monkeypatch):
    path = _write_tmp_mapping(tmp_path, """
      default_activity: activity_raw
      rules:
        - pattern: "verify"
    """)
    _reload_with(monkeypatch, path)
    assert ms.canonicalize("please verify", "api") == "please verify"

def test_case_insensitive_matching(tmp_path, monkeypatch):
    path = _write_tmp_mapping(tmp_path, """
      default_activity: activity_raw
      rules:
        - pattern: "approve"
          activity: "Approval Sent"
    """)
    _reload_with(monkeypatch, path)
    assert ms.canonicalize("PLEASE APPROVE THIS", "db") == "Approval Sent"
    assert ms.canonicalize("please ApproVe this", "db") == "Approval Sent"

def test_first_match_wins(tmp_path, monkeypatch):
    path = _write_tmp_mapping(tmp_path, """
      default_activity: activity_raw
      rules:
        - pattern: "submit"
          activity: "Application Submitted"
        - pattern: "submit"
          activity: "Submitted Generic"
        - pattern: "sub"
          activity: "Too Broad"
    """)
    _reload_with(monkeypatch, path)
    assert ms.canonicalize("please submit the docs", "db") == "Application Submitted"

def test_load_rules_missing_file(monkeypatch, tmp_path):
    ms._load_yaml.cache_clear()
    ms.load_rules.cache_clear()
    path = str(tmp_path / "doesnotexist.yaml")
    rules = ms.load_rules(path)
    assert "rules" in rules and isinstance(rules["rules"], list)

def test_load_rules_invalid_regex(tmp_path, monkeypatch):
    path = _write_tmp_mapping(tmp_path, """
      default_activity: fallback
      rules:
        - pattern: "[unclosed"
          activity: "Invalid"
    """)
    _reload_with(monkeypatch, path)
    rules = ms.load_rules()
    assert rules["rules"] == []
