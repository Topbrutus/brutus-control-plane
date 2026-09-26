from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = 8873
INTERNAL_STATE_URL = "http://127.0.0.1:8872/api/public-state"

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    ),
}


def fetch_public_state() -> dict[str, object]:
    req = Request(INTERNAL_STATE_URL, headers={"Accept": "application/json"})
    with urlopen(req, timeout=1.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("mode") != "PUBLIC_SAFE" or payload.get("read_only") is not True:
        raise ValueError("internal endpoint did not return PUBLIC_SAFE state")
    return payload


class PublicHandler(BaseHTTPRequestHandler):
    def apply_headers(self) -> None:
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)

    def send_json(self, data: object, code: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.apply_headers()
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            try:
                self.send_json(fetch_public_state())
            except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
                self.send_json(
                    {
                        "mode": "PUBLIC_SAFE",
                        "read_only": True,
                        "status": "OFFLINE",
                        "error": "internal_feed_unavailable",
                    },
                    503,
                )
            return

        if path in ("/", "/index.html", "/public.html"):
            raw = (ROOT / "live" / "public.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.apply_headers()
            self.end_headers()
            self.wfile.write(raw)
            return

        self.send_error(404)

    def do_POST(self) -> None:
        self.send_json(
            {
                "mode": "PUBLIC_SAFE",
                "read_only": True,
                "error": "write_operations_disabled",
            },
            405,
        )

    def do_PUT(self) -> None:
        self.do_POST()

    def do_DELETE(self) -> None:
        self.do_POST()

    def log_message(self, fmt: str, *args: object) -> None:
        print("[PUBLIC]", fmt % args)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PublicHandler)
    print(f"ANTMUX/BRUTUS PUBLIC SAFE: http://{HOST}:{PORT}")
    print("Lecture seule. Le flux interne reste sur 127.0.0.1:8872.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
