from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

SOURCE_URL = os.environ.get("ANTMUX_ZEL_SOURCE_URL", "http://127.0.0.1:8873/api/state")
INGEST_URL = os.environ.get(
    "ANTMUX_ZEL_INGEST_URL",
    "https://antmux.com/laboratoire/embryon-x72/api/zelstereos/ingest",
)
TOKEN = os.environ.get("ANTMUX_ZEL_INGEST_TOKEN", "").strip()
INTERVAL = float(os.environ.get("ANTMUX_ZEL_INTERVAL", "0.25"))
DRY_RUN = os.environ.get("ANTMUX_ZEL_DRY_RUN", "") == "1"


def canonical_payload(raw: dict) -> dict:
    if raw.get("mode") != "PUBLIC_SAFE" or raw.get("read_only") is not True:
        raise ValueError("source is not PUBLIC_SAFE read-only")
    allowed = {
        "mode": "PUBLIC_SAFE",
        "read_only": True,
        "status": raw.get("status"),
        "stage_index": raw.get("stage_index"),
        "stage": raw.get("stage"),
        "channels": raw.get("channels"),
        "trace_points": raw.get("trace_points"),
        "trace_total": raw.get("trace_total"),
        "public_values": raw.get("public_values", []),
        "public_values_total": raw.get("public_values_total", 0),
        "global_error": raw.get("global_error", {}),
        "f1": raw.get("f1", {}),
        "event_seq": raw.get("event_seq", 0),
    }
    return allowed


def fetch_source() -> dict:
    with urllib.request.urlopen(SOURCE_URL, timeout=3) as response:
        raw = json.loads(response.read().decode("utf-8"))
    return canonical_payload(raw)


def fingerprint(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def publish(payload: dict) -> int:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(INGEST_URL, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=5) as response:
        response.read()
        return response.status


def main() -> int:
    if not DRY_RUN and not TOKEN:
        print("ERROR: ANTMUX_ZEL_INGEST_TOKEN is required", file=sys.stderr)
        return 2

    last_hash = None
    failures = 0
    print(f"ZEL_PUBLISHER source={SOURCE_URL} interval={INTERVAL:.3f}s dry_run={DRY_RUN}")

    while True:
        try:
            payload = fetch_source()
            current_hash = fingerprint(payload)
            if current_hash != last_hash:
                if DRY_RUN:
                    print(
                        "DRY_RUN",
                        f"stage={payload.get('stage')}",
                        f"trace={payload.get('trace_points')}/{payload.get('trace_total')}",
                    )
                else:
                    status = publish(payload)
                    print(
                        "PUBLISHED",
                        f"http={status}",
                        f"stage={payload.get('stage')}",
                        f"trace={payload.get('trace_points')}/{payload.get('trace_total')}",
                    )
                last_hash = current_hash
            failures = 0
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            return 0
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            failures += 1
            wait = min(10.0, max(INTERVAL, 0.5 * (2 ** min(failures - 1, 4))))
            print(f"WARN: publish cycle failed ({type(exc).__name__}); retry in {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)


if __name__ == "__main__":
    raise SystemExit(main())
