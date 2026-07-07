import json
import os
import platform
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests


def _safe_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def list_directory(path: str = ".", max_entries: int = 200) -> dict:
    abs_path = _safe_path(path)
    entries = []
    for name in sorted(os.listdir(abs_path))[:max_entries]:
        full = os.path.join(abs_path, name)
        stat = os.stat(full)
        entries.append(
            {
                "name": name,
                "type": "dir" if os.path.isdir(full) else "file",
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
        )
    return {"path": abs_path, "entries": entries, "truncated": len(entries) >= max_entries}


def read_file(path: str, max_bytes: int = 20000) -> dict:
    abs_path = _safe_path(path)
    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(max_bytes)
    return {"path": abs_path, "content": content, "truncated": len(content) >= max_bytes}


def search_text(pattern: str, path: str = ".", max_results: int = 50, ignore_case: bool = True) -> dict:
    abs_path = _safe_path(path)
    flags = re.IGNORECASE if ignore_case else 0
    regex = re.compile(pattern, flags)
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
                        results.append({"path": candidate, "line": lineno, "text": line.rstrip("\n")})
                        if len(results) >= max_results:
                            return {"path": abs_path, "results": results, "truncated": True}
        except Exception:
            continue

    return {"path": abs_path, "results": results, "truncated": False}


def grep_lines(path: str, needle: str, max_results: int = 100, ignore_case: bool = True) -> dict:
    abs_path = _safe_path(path)
    needle_cmp = needle.lower() if ignore_case else needle
    results = []

    candidates = [abs_path] if os.path.isfile(abs_path) else [
        os.path.join(root, file)
        for root, _, files in os.walk(abs_path)
        for file in files
    ]

    for candidate in candidates:
        try:
            with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    hay = line.lower() if ignore_case else line
                    if needle_cmp in hay:
                        results.append({"path": candidate, "line": lineno, "text": line.rstrip("\n")})
                        if len(results) >= max_results:
                            return {"path": abs_path, "results": results, "truncated": True}
        except Exception:
            continue

    return {"path": abs_path, "results": results, "truncated": False}


def file_stats(path: str) -> dict:
    abs_path = _safe_path(path)
    stat = os.stat(abs_path)
    return {
        "path": abs_path,
        "size": stat.st_size,
        "mode": oct(stat.st_mode),
        "mtime": stat.st_mtime,
        "is_dir": os.path.isdir(abs_path),
        "is_file": os.path.isfile(abs_path),
    }


def system_info() -> dict:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "cwd": os.getcwd(),
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


def process_snapshot(limit: int = 50) -> dict:
    try:
        out = subprocess.check_output(["ps", "-eo", "pid,ppid,comm,%cpu,%mem", "--sort=-%cpu"], text=True)
        lines = out.strip().splitlines()[1 : limit + 1]
        return {"processes": lines, "truncated": len(lines) >= limit}
    except Exception as e:
        return {"error": str(e)}


def current_time(utc_offset: str = "+00:00") -> dict:
    from datetime import datetime, timedelta

    sign = 1 if utc_offset.startswith("+") else -1
    hours, minutes = map(int, utc_offset[1:].split(":"))
    offset = timedelta(hours=hours * sign, minutes=minutes * sign)
    now = datetime.utcnow() + offset
    return {"utc_offset": utc_offset, "now": now.isoformat(timespec="seconds")}


def web_search(query: str, max_results: int = 5) -> dict:
    """Lightweight DuckDuckGo HTML search."""
    url = "https://html.duckduckgo.com/html/"
    resp = requests.post(url, data={"q": query}, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    html = resp.text
    links = []
    for match in re.finditer(r'nofollow" class="result__a" href="([^"]+)".*?>(.*?)</a>', html, re.DOTALL):
        href = match.group(1)
        title = re.sub(r"<.*?>", "", match.group(2))
        links.append({"title": title, "url": href})
        if len(links) >= max_results:
            break
    return {"query": query, "results": links}


def builtin_tools() -> List[tuple]:
    return [
        ("list_directory", list_directory),
        ("read_file", read_file),
        ("search_text", search_text),
        ("grep_lines", grep_lines),
        ("file_stats", file_stats),
        ("system_info", system_info),
        ("process_snapshot", process_snapshot),
        ("current_time", current_time),
        ("web_search", web_search),
    ]
