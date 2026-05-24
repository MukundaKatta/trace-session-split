"""Tests for trace_session_split."""

import json
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pytest
from trace_session_split import TraceSplitError, load_jsonl, split_by_key, split_file, write_splits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jsonl(rows: list[dict]) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w")
    for r in rows:
        tmp.write(json.dumps(r) + "\n")
    tmp.close()
    return Path(tmp.name)


def tmpdir() -> Path:
    d = tempfile.mkdtemp()
    return Path(d)


# ---------------------------------------------------------------------------
# split_by_key
# ---------------------------------------------------------------------------

def test_split_by_explicit_key():
    events = [
        {"run_id": "r1", "msg": "a"},
        {"run_id": "r2", "msg": "b"},
        {"run_id": "r1", "msg": "c"},
    ]
    groups = split_by_key(events, key="run_id")
    assert set(groups.keys()) == {"r1", "r2"}
    assert len(groups["r1"]) == 2
    assert len(groups["r2"]) == 1


def test_split_auto_detect_run_id():
    events = [
        {"run_id": "run-a", "step": 1},
        {"run_id": "run-b", "step": 2},
    ]
    groups = split_by_key(events)
    assert "run-a" in groups
    assert "run-b" in groups


def test_split_auto_detect_session_id():
    events = [
        {"session_id": "s1", "step": 1},
        {"session_id": "s2", "step": 2},
    ]
    groups = split_by_key(events)
    assert "s1" in groups
    assert "s2" in groups


def test_split_auto_detect_lane():
    events = [
        {"lane": "sup", "step": 1},
        {"lane": "worker1", "step": 2},
    ]
    groups = split_by_key(events)
    assert "sup" in groups
    assert "worker1" in groups


def test_split_missing_key_grouped_under_empty():
    events = [
        {"run_id": "r1", "step": 1},
        {"step": 2},  # no run_id
    ]
    groups = split_by_key(events, key="run_id")
    assert "" in groups
    assert len(groups[""]) == 1


def test_split_no_candidate_field_raises():
    events = [{"msg": "hello"}]
    with pytest.raises(TraceSplitError, match="no split key found"):
        split_by_key(events)


def test_split_empty_events():
    groups = split_by_key([], key="run_id")
    assert groups == {}


def test_split_preserves_order():
    events = [
        {"run_id": "r1", "step": 1},
        {"run_id": "r1", "step": 2},
        {"run_id": "r1", "step": 3},
    ]
    groups = split_by_key(events, key="run_id")
    steps = [e["step"] for e in groups["r1"]]
    assert steps == [1, 2, 3]


# ---------------------------------------------------------------------------
# write_splits
# ---------------------------------------------------------------------------

def test_write_splits_creates_files():
    groups = {"r1": [{"run_id": "r1", "step": 1}], "r2": [{"run_id": "r2", "step": 2}]}
    out = tmpdir()
    written = write_splits(groups, out)
    assert len(written) == 2
    for path in written.values():
        assert path.exists()


def test_write_splits_content_correct():
    groups = {"r1": [{"run_id": "r1", "x": 42}]}
    out = tmpdir()
    written = write_splits(groups, out)
    content = written["r1"].read_text()
    data = json.loads(content.strip())
    assert data["x"] == 42


def test_write_splits_safe_filenames():
    groups = {"run/id:1": [{"x": 1}]}
    out = tmpdir()
    written = write_splits(groups, out, safe_filenames=True)
    path = written["run/id:1"]
    assert "/" not in path.name
    assert ":" not in path.name


def test_write_splits_with_prefix():
    groups = {"r1": [{"x": 1}]}
    out = tmpdir()
    written = write_splits(groups, out, prefix="trace_")
    assert written["r1"].name.startswith("trace_")


def test_write_splits_empty_key_filename():
    groups = {"": [{"x": 1}]}
    out = tmpdir()
    written = write_splits(groups, out)
    # empty key maps to "_no_key_" which after strip("_") becomes "no_key"
    assert written[""].name == "no_key.jsonl"


# ---------------------------------------------------------------------------
# split_file
# ---------------------------------------------------------------------------

def test_split_file_end_to_end():
    events = [
        {"run_id": "run-a", "step": 1},
        {"run_id": "run-b", "step": 2},
        {"run_id": "run-a", "step": 3},
    ]
    p = make_jsonl(events)
    out = tmpdir()
    try:
        written = split_file(p, out)
        assert len(written) == 2
        run_a_events = load_jsonl(written["run-a"])
        assert len(run_a_events) == 2
    finally:
        p.unlink()


# ---------------------------------------------------------------------------
# load_jsonl
# ---------------------------------------------------------------------------

def test_load_jsonl_missing():
    with pytest.raises(TraceSplitError, match="does not exist"):
        load_jsonl("/tmp/__trace_split_no_such_file__.jsonl")
