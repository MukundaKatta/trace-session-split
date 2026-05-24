"""CLI: split a JSONL log by a session/run-id field.

Usage:
    python3 -m trace_session_split PATH OUTPUT_DIR [--key KEY]
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="trace-session-split",
        description="Split a JSONL log by run_id/session_id into separate files.",
    )
    parser.add_argument("path", help="JSONL file to split")
    parser.add_argument("output_dir", help="directory to write split files into")
    parser.add_argument("--key", help="field name to split on (auto-detected if omitted)")
    parser.add_argument("--prefix", default="", help="filename prefix")
    args = parser.parse_args(argv)

    from . import TraceSplitError, split_file

    try:
        written = split_file(
            args.path,
            args.output_dir,
            key=args.key or None,
            prefix=args.prefix,
        )
    except TraceSplitError as e:
        print(f"trace-session-split: {e}", file=sys.stderr)
        sys.exit(1)

    for key, path in sorted(written.items()):
        print(f"{key!r:30} -> {path}")

    print(f"\n{len(written)} files written to {args.output_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
