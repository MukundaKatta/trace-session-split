# trace-session-split

Split a multi-session agent JSONL log by run_id, session_id, or any field into separate files. Auto-detects the split key. Zero runtime dependencies.

```bash
pip install trace-session-split
```

## Why

If you log all your Hermes agent runs to one file, you eventually want to split it — one file per run, so you can feed each run into [trace-merge](https://github.com/MukundaKatta/trace-merge), [trace-stats](https://github.com/MukundaKatta/trace-stats), or [trace-anomaly](https://github.com/MukundaKatta/trace-anomaly).

## CLI

```bash
# Auto-detect the split key (tries run_id, session_id, session, run, trace_id, lane)
python3 -m trace_session_split all_runs.jsonl ./runs/

# Explicit key
python3 -m trace_session_split all_runs.jsonl ./runs/ --key run_id
```

Output:
```
'run-a'               -> runs/run-a.jsonl
'run-b'               -> runs/run-b.jsonl
'run-c'               -> runs/run-c.jsonl

3 files written to runs/
```

## Python API

```python
from trace_session_split import split_file, split_by_key, write_splits, load_jsonl

# One-shot: load, split, write
written = split_file("all_runs.jsonl", "./runs/")

# Or step by step:
events = load_jsonl("all_runs.jsonl")
groups = split_by_key(events, key="run_id")   # or key=None to auto-detect

for key, evs in groups.items():
    print(f"{key}: {len(evs)} events")

written = write_splits(groups, "./runs/")
```

## Auto-detected keys

When `key` is omitted, trace-session-split tries these fields in order:
`run_id`, `session_id`, `session`, `run`, `trace_id`, `lane`

The first field found on the first event is used.

## Safe filenames

By default, characters that are unsafe in filenames (slashes, colons, spaces) are replaced with underscores. Pass `safe_filenames=False` to write the raw key value.

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/ -q
# 15 passed
```

Zero runtime dependencies. Python 3.10+. MIT license.
