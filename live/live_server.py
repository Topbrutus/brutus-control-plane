from __future__ import annotations

import json
import re
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from z_stereo_formula_adapters import f1_pell_rank_21_power
from z_stereo_ninefold import fanout3, mirror4, recombine3, recombine4, route4
import publish_public_safe as zel_publisher

HOST = "127.0.0.1"
PORT = 8872
LOCK = threading.Lock()
RUNNER: threading.Thread | None = None
STOP = threading.Event()
EVENTS: deque[dict[str, object]] = deque(maxlen=120)
EVENT_SEQ = 0
TRACE_COUNTS = [1, 4, 13, 49, 58, 61, 62]
ZEL_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="zel-publish")

PUBLIC_SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s]+"),
]
PUBLIC_REDACTIONS = [
    (re.compile(r"(?i)https?://\S+"), "[URL]"),
    (re.compile(r"(?i)\b[A-Z]:\\[^\s\"']+"), "[LOCAL_PATH]"),
    (re.compile(r"(?i)(?:/home|/Users|/mnt|/tmp)/[^\s\"']+"), "[LOCAL_PATH]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
    (re.compile(r"\b[A-Fa-f0-9]{24,}\b"), "[ID]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
]
STAGE_NAMES = [
    "ENTREE", "Z1 1->3", "F 3->9", "Z MIROIR 9->36",
    "CHECK 36->9", "RECOMB 9->3", "SORTIE 3->1",
]


def frac_payload(value: Fraction) -> dict[str, object]:
    return {"exact": str(value), "decimal": float(value)}


def emit_event(kind: str, label: str, detail: str = "", status: str = "INFO", source: str = "CONTROL_PLANE") -> dict[str, object]:
    global EVENT_SEQ
    with LOCK:
        EVENT_SEQ += 1
        event = {
            "seq": EVENT_SEQ,
            "timestamp": time.time(),
            "source": str(source)[:40],
            "kind": str(kind)[:40],
            "label": str(label)[:160],
            "detail": str(detail)[:600],
            "status": str(status)[:24],
        }
        EVENTS.append(event)
        return dict(event)


def sanitize_public_text(text: object, limit: int = 180) -> str:
    value = str(text or "").strip()
    for pattern in PUBLIC_SECRET_PATTERNS:
        value = pattern.sub(r"\1[REDACTED]", value)
    for pattern, replacement in PUBLIC_REDACTIONS:
        value = pattern.sub(replacement, value)
    return value[:limit]


def public_event(event: dict[str, object]) -> dict[str, object]:
    kind = str(event.get("kind", "EVENT"))
    status = str(event.get("status", "INFO"))
    detail = str(event.get("detail", ""))
    public_detail = ""

    if kind == "COMMAND_START":
        public_detail = "Validation lancée"
    elif kind == "COMMAND_END":
        match = re.search(r"exit=(-?\d+).*?([0-9]+(?:\.[0-9]+)?)s", detail)
        public_detail = (
            f"exit={match.group(1)} · {match.group(2)}s"
            if match else ("Validation terminée" if status != "FAIL" else "Validation échouée")
        )
    elif kind == "OUTPUT":
        if re.fullmatch(r"OK", detail.strip(), flags=re.IGNORECASE):
            public_detail = "Suite de tests: OK"
        else:
            summary = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+([0-9.]+)s", detail, flags=re.IGNORECASE)
            if summary:
                public_detail = f"{summary.group(1)} tests · {summary.group(2)}s"
            elif re.search(r"\.\.\.\s+ok\s*$", detail, flags=re.IGNORECASE):
                public_detail = "Test: PASS"
            elif re.search(r"\.\.\.\s+(fail|error)\s*$", detail, flags=re.IGNORECASE):
                public_detail = "Test: FAIL"
            else:
                public_detail = "Sortie de validation reçue"
    else:
        public_detail = sanitize_public_text(detail, 120)

    source = str(event.get("source", "SYSTEM")).upper()
    if source not in {"ASTRA", "CONTROL_PLANE", "ANTMUX"}:
        source = "SYSTEM"

    return {
        "seq": int(event.get("seq", 0)),
        "timestamp": float(event.get("timestamp", 0.0)),
        "source": source,
        "kind": sanitize_public_text(kind, 32),
        "label": sanitize_public_text(event.get("label", "activité"), 80),
        "detail": sanitize_public_text(public_detail, 140),
        "status": sanitize_public_text(status, 16),
    }


def build_frames(x: Fraction, route_mode: str) -> list[list[Fraction]]:
    level1 = list(fanout3(x, Fraction(2, 7)))
    majors: list[Fraction] = []
    for i, parent in enumerate(level1):
        majors.extend(fanout3(parent, Fraction(i + 1, 11)))

    mirrors: list[Fraction] = []
    local: list[Fraction] = []
    permutation = (0, 1, 2, 3) if route_mode == "identity" else (0, 2, 1, 3)
    for i, major in enumerate(majors):
        m = mirror4(major, Fraction(i + 1, 37))
        routed = route4(m, permutation)
        mirrors.extend(routed)
        local.append(recombine4(routed))

    level3 = [recombine3(local[i:i + 3]) for i in range(0, 9, 3)]
    output = [recombine3(level3)]
    return [[x], level1, majors, mirrors, local, level3, output]
STATE: dict[str, object] = {
    "input": "17/5",
    "route": "identity",
    "k": 3,
    "index": 0,
    "status": "STOP",
}


def snapshot() -> dict[str, object]:
    with LOCK:
        x = Fraction(str(STATE["input"]))
        route_mode = str(STATE["route"])
        index = int(STATE["index"])
        frames = build_frames(x, route_mode)
        frame = frames[index]
        output = frames[-1][0]
        f1 = f1_pell_rank_21_power(int(STATE["k"]))
        return {
            "status": STATE["status"],
            "stage_index": index,
            "stage": STAGE_NAMES[index],
            "channels": len(frame),
            "trace_points": TRACE_COUNTS[index],
            "trace_total": 62,
            "route": route_mode,
            "input": frac_payload(x),
            "values": [frac_payload(v) for v in frame],
            "output": frac_payload(output),
            "global_error": frac_payload(output - x),
            "f1": {
                "k": int(STATE["k"]),
                "value": f1.value,
                "kind": f1.kind,
                "formula": "z_P(21^k)=4*21^(k-1)",
                "source_commit": f1.source_commit,
            },
            "events": list(EVENTS)[-40:],
            "event_seq": EVENT_SEQ,
            "timestamp": time.time(),
        }


def public_snapshot() -> dict[str, object]:
    with LOCK:
        x = Fraction(str(STATE["input"]))
        route_mode = str(STATE["route"])
        index = int(STATE["index"])
        frames = build_frames(x, route_mode)
        frame = frames[index]
        output = frames[-1][0]
        f1 = f1_pell_rank_21_power(int(STATE["k"]))
        safe_events = [public_event(event) for event in list(EVENTS)[-24:]]
        return {
            "mode": "PUBLIC_SAFE",
            "read_only": True,
            "status": STATE["status"],
            "stage_index": index,
            "stage": STAGE_NAMES[index],
            "channels": len(frame),
            "trace_points": TRACE_COUNTS[index],
            "trace_total": 62,
            "public_values": [frac_payload(v) for v in frame[:12]],
            "public_values_total": len(frame),
            "global_error": frac_payload(output - x),
            "f1": {
                "formula_id": "F1",
                "k": int(STATE["k"]),
                "value": f1.value,
                "kind": f1.kind,
                "formula": "z_P(21^k)=4*21^(k-1)",
                "source_commit_short": f1.source_commit[:12],
            },
            "events": safe_events,
            "event_seq": EVENT_SEQ,
            "timestamp": time.time(),
        }


def _publish_public_payload(payload: dict[str, object]) -> None:
    try:
        status = zel_publisher.publish(payload)
        print(f"[ZEL-PUBLISH] http={status} stage={payload.get('stage')} trace={payload.get('trace_points')}/{payload.get('trace_total')}")
    except Exception as exc:
        print(f"[ZEL-PUBLISH] WARN {type(exc).__name__}")


def queue_public_publish() -> None:
    if not zel_publisher.TOKEN:
        return
    payload = zel_publisher.canonical_payload(public_snapshot())
    ZEL_EXECUTOR.submit(_publish_public_payload, payload)


def advance() -> None:
    changed = False
    with LOCK:
        index = int(STATE["index"])
        if index < len(STAGE_NAMES) - 1:
            STATE["index"] = index + 1
            changed = True
        else:
            STATE["status"] = "DONE"
            STOP.set()
    if changed:
        queue_public_publish()


def runner() -> None:
    while not STOP.wait(0.65):
        advance()
        with LOCK:
            if STATE["status"] == "DONE":
                return


def start_run() -> None:
    global RUNNER
    with LOCK:
        if STATE["status"] == "RUN":
            return
        if int(STATE["index"]) >= len(STAGE_NAMES) - 1:
            STATE["index"] = 0
        STATE["status"] = "RUN"
    queue_public_publish()
    STOP.clear()
    RUNNER = threading.Thread(target=runner, daemon=True)
    RUNNER.start()


def pause_run() -> None:
    STOP.set()
    with LOCK:
        if STATE["status"] == "RUN":
            STATE["status"] = "PAUSE"


def reset_run() -> None:
    STOP.set()
    with LOCK:
        STATE["index"] = 0
        STATE["status"] = "STOP"
    queue_public_publish()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data: object, code: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self.send_json(snapshot())
            return
        if path == "/api/public-state":
            self.send_json(public_snapshot())
            return
        if path in ("/", "/index.html"):
            raw = (ROOT / "live" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        data = json.loads(body.decode("utf-8") or "{}")

        if path == "/api/start":
            start_run()
        elif path == "/api/pause":
            pause_run()
        elif path == "/api/step":
            pause_run()
            advance()
        elif path == "/api/reset":
            reset_run()
        elif path == "/api/event":
            event = emit_event(
                kind=data.get("kind", "EVENT"),
                label=data.get("label", "event"),
                detail=data.get("detail", ""),
                status=data.get("status", "INFO"),
                source=data.get("source", "ASTRA"),
            )
            self.send_json({"accepted": True, "event": event})
            return
        elif path == "/api/config":
            pause_run()
            with LOCK:
                if "input" in data:
                    Fraction(str(data["input"]))
                    STATE["input"] = str(data["input"])
                if data.get("route") in ("identity", "cross"):
                    STATE["route"] = data["route"]
                if "k" in data:
                    k = int(data["k"])
                    if k < 2:
                        raise ValueError("k must be >= 2")
                    STATE["k"] = k
                STATE["index"] = 0
                STATE["status"] = "STOP"
            queue_public_publish()
        else:
            self.send_error(404)
            return
        self.send_json(snapshot())

    def log_message(self, fmt: str, *args: object) -> None:
        print("[LIVE]", fmt % args)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ANTMUX/BRUTUS LIVE: http://{HOST}:{PORT}")
    print("Ctrl+C pour arreter.")
    queue_public_publish()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STOP.set()
        server.server_close()


if __name__ == "__main__":
    main()

