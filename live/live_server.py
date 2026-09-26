from __future__ import annotations

import json
import sys
import threading
import time
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from z_stereo_formula_adapters import f1_pell_rank_21_power
from z_stereo_ninefold import fanout3, mirror4, recombine3, recombine4, route4

HOST = "127.0.0.1"
PORT = 8872
LOCK = threading.Lock()
RUNNER: threading.Thread | None = None
STOP = threading.Event()
TRACE_COUNTS = [1, 4, 13, 49, 58, 61, 62]
STAGE_NAMES = [
    "ENTREE", "Z1 1->3", "F 3->9", "Z MIROIR 9->36",
    "CHECK 36->9", "RECOMB 9->3", "SORTIE 3->1",
]


def frac_payload(value: Fraction) -> dict[str, object]:
    return {"exact": str(value), "decimal": float(value)}


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
            "timestamp": time.time(),
        }


def advance() -> None:
    with LOCK:
        index = int(STATE["index"])
        if index < len(STAGE_NAMES) - 1:
            STATE["index"] = index + 1
        else:
            STATE["status"] = "DONE"
            STOP.set()


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


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data: object, code: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self.send_json(snapshot())
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
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STOP.set()
        server.server_close()


if __name__ == "__main__":
    main()

