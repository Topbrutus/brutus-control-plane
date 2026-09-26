from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
EVENT_URL = "http://127.0.0.1:8872/api/event"

SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s]+"),
]


def safe_text(text: str, limit: int = 500) -> str:
    value = text.strip()
    for pattern in SECRET_PATTERNS:
        value = pattern.sub(r"\1[REDACTED]", value)
    return value[:limit]


def emit(kind: str, label: str, detail: str = "", status: str = "INFO") -> None:
    payload = json.dumps({
        "source": "ASTRA",
        "kind": kind,
        "label": safe_text(label, 160),
        "detail": safe_text(detail, 500),
        "status": status,
    }).encode("utf-8")
    req = Request(EVENT_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=0.5):
            pass
    except (URLError, OSError):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command and mirror safe progress into the local live dashboard.")
    parser.add_argument("--label", default="Commande Astra")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("missing command after --")

    emit("COMMAND_START", args.label, " ".join(command), "RUN")
    started = time.time()

    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        cleaned = safe_text(line)
        if cleaned:
            emit("OUTPUT", args.label, cleaned, "RUN")

    code = proc.wait()
    elapsed = time.time() - started
    status = "PASS" if code == 0 else "FAIL"
    emit("COMMAND_END", args.label, f"exit={code} · {elapsed:.3f}s", status)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
