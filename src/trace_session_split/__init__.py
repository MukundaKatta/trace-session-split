"""trace-session-split: split a multi-session JSONL log by run_id/session_id into separate files.

Public API:
    split_by_key(events, *, key=None)     -> dict[str, list[dict]]
    write_splits(groups, output_dir, ...) -> dict[str, Path]
    split_file(input_path, output_dir, ...) -> dict[str, Path]
    load_jsonl(path)                      -> list[dict]
    TraceSplitError                       — base exception
"""

from .core import TraceSplitError, load_jsonl, split_by_key, split_file, write_splits

__all__ = ["split_by_key", "write_splits", "split_file", "load_jsonl", "TraceSplitError"]
__version__ = "0.1.0"
