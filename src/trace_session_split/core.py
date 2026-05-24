"""Split a JSONL log by a session/run-id field into separate files."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


class TraceSplitError(Exception):
    """Base exception for trace-session-split failures."""


# Fields tried in order when auto-detecting the split key.
_DEFAULT_KEY_CANDIDATES = ("run_id", "session_id", "session", "run", "trace_id", "lane")


def _detect_split_key(event: dict[str, Any]) -> str | None:
    for k in _DEFAULT_KEY_CANDIDATES:
        if k in event and isinstance(event[k], str) and event[k].strip():
            return k
    return None


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSONL file into a list of event dicts. Blank lines skipped."""
    p = Path(path)
    if not p.exists():
        raise TraceSplitError(f"file does not exist: {p}")
    events: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise TraceSplitError(f"{p}:{lineno}: invalid JSON: {e.msg}") from e
            if not isinstance(obj, dict):
                raise TraceSplitError(
                    f"{p}:{lineno}: expected JSON object, got {type(obj).__name__}"
                )
            events.append(obj)
    return events


def split_by_key(
    events: Iterable[dict[str, Any]],
    *,
    key: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Group events by a field value.

    Args:
        events: iterable of event dicts.
        key: the field to split on. If None, auto-detected from the first
             event that has a value in (run_id, session_id, session, run,
             trace_id, lane).

    Returns:
        dict mapping field value → list of events (in input order).
        Events missing the key are grouped under the special key "".

    Raises:
        TraceSplitError if key is None and no candidate field is found in
        the first event.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    effective_key = key
    first = True

    for ev in events:
        if first and effective_key is None:
            detected = _detect_split_key(ev)
            if detected is None:
                raise TraceSplitError(
                    f"no split key found on first event; tried {_DEFAULT_KEY_CANDIDATES}. "
                    "Pass key= explicitly."
                )
            effective_key = detected
            first = False
        elif first:
            first = False

        val = ev.get(effective_key, "") if effective_key else ""
        val_str = str(val) if not isinstance(val, str) else val
        groups[val_str].append(ev)

    return dict(groups)


def write_splits(
    groups: dict[str, list[dict[str, Any]]],
    output_dir: str | Path,
    *,
    prefix: str = "",
    suffix: str = ".jsonl",
    safe_filenames: bool = True,
) -> dict[str, Path]:
    """Write each group to a separate JSONL file.

    Args:
        groups: output of split_by_key.
        output_dir: directory to write files to. Created if missing.
        prefix: prepended to each filename (after output_dir).
        suffix: file extension (default ".jsonl").
        safe_filenames: if True, replace characters unsafe in filenames
            (spaces, slashes, colons, etc.) with underscores.

    Returns:
        dict mapping group key → Path of the written file.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}

    for group_key, events in groups.items():
        filename = group_key if group_key else "_no_key_"
        if safe_filenames:
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
            safe = safe.strip("_") or "_"
        else:
            safe = filename
        path = out / f"{prefix}{safe}{suffix}"
        with path.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev, ensure_ascii=False))
                f.write("\n")
        written[group_key] = path

    return written


def split_file(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    key: str | None = None,
    prefix: str = "",
    suffix: str = ".jsonl",
) -> dict[str, Path]:
    """Convenience: load a JSONL file, split it, write outputs.

    Returns dict mapping group key → output file Path.
    """
    events = load_jsonl(input_path)
    groups = split_by_key(events, key=key)
    return write_splits(groups, output_dir, prefix=prefix, suffix=suffix)
