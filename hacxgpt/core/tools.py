import os
import json
import re
from typing import List


def _safe_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def list_directory(path: str = ".") -> dict:
    """List files and directories in a path."""
    abs_path = _safe_path(path)
    entries = []
    for name in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, name)
        entries.append(
            {
                "name": name,
                "type": "dir" if os.path.isdir(full) else "file",
            }
        )
    return {"path": abs_path, "entries": entries}


def read_file(path: str, max_bytes: int = 20000) -> dict:
    """Read a text file from disk."""
    abs_path = _safe_path(path)
    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(max_bytes)
    return {"path": abs_path, "content": content}


def search_text(pattern: str, path: str = ".", max_results: int = 50) -> dict:
    """Search text files for a regex pattern."""
    abs_path = _safe_path(path)
    regex = re.compile(pattern)
    results = []

    if os.path.isfile(abs_path):
        candidates = [abs_path]
    else:
        candidates = []
        for root, _, files in os.walk(abs_path):
            for filename in files:
                candidates.append(os.path.join(root, filename))

    for candidate in candidates:
        try:
            with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    if regex.search(line):
                        results.append(
                            {
                                "path": candidate,
                                "line": lineno,
                                "text": line.rstrip("\n"),
                            }
                        )
                        if len(results) >= max_results:
                            return {"path": abs_path, "results": results}
        except Exception:
            continue

    return {"path": abs_path, "results": results}


def builtin_tools() -> List[tuple]:
    return [
        ("list_directory", list_directory),
        ("read_file", read_file),
        ("search_text", search_text),
    ]
