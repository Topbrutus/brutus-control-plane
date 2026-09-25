from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ('OBSERVATION', 'CANDIDATE', 'VERIFIED', 'PROVEN', 'RELEASED')
REQUIRED = ('run_id', 'family', 'status', 'source', 'compute', 'verification')

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))

def canonical_bytes(value: Any) -> bytes:
    text = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return text.encode('utf-8')

def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED:
        if key not in data:
            errors.append(f'missing:{key}')
    if data.get('status') not in STATUSES:
        errors.append('invalid:status')
    source = data.get('source', {})
    if not source.get('repo'):
        errors.append('missing:source.repo')
    if len(str(source.get('commit', ''))) < 7:
        errors.append('invalid:source.commit')
    compute = data.get('compute', {})
    if compute.get('deterministic') is not True:
        errors.append('invalid:compute.deterministic')
    verification = data.get('verification', {})
    for key in ('primary', 'mirror', 'countertest'):
        if verification.get(key) is not True:
            errors.append(f'missing:verification.{key}')
    if not str(data.get('run_id', '')).startswith('BRUTUS-RUN://'):
        errors.append('invalid:run_id')
    return errors

def transition_requirements(current: str, target: str) -> list[str]:
    policy = load_json(ROOT / 'policies' / 'promotion.json')
    return list(policy['transitions'].get(f'{current}->{target}', []))

def check_transition(data: dict[str, Any], target: str) -> tuple[bool, list[str]]:
    current = data.get('status')
    if current not in STATUSES or target not in STATUSES:
        return False, ['invalid_status']
    if STATUSES.index(target) != STATUSES.index(current) + 1:
        return False, ['status_skip_forbidden']
    evidence = data.get('evidence', {})
    missing = [k for k in transition_requirements(current, target) if not evidence.get(k)]
    return not missing, missing

def append_event(event: dict[str, Any], log_path: Path) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if log_path.exists():
        lines = [x for x in log_path.read_text(encoding='utf-8').splitlines() if x.strip()]
        if lines:
            previous = json.loads(lines[-1]).get('event_hash')
    payload = dict(event)
    payload.setdefault('timestamp', datetime.now(timezone.utc).isoformat())
    payload['previous_event_hash'] = previous
    payload.pop('event_hash', None)
    payload['event_hash'] = fingerprint(payload)
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + '\n')
    return payload

def cmd_validate(path: str) -> int:
    data = load_json(Path(path))
    errors = validate_manifest(data)
    print(json.dumps({'valid': not errors, 'errors': errors}, ensure_ascii=False))
    return 0 if not errors else 2

def cmd_fingerprint(path: str) -> int:
    data = load_json(Path(path))
    print(fingerprint(data))
    return 0

def cmd_transition(path: str, target: str) -> int:
    data = load_json(Path(path))
    allowed, missing = check_transition(data, target)
    print(json.dumps({'allowed': allowed, 'missing': missing}, ensure_ascii=False))
    return 0 if allowed else 3

def cmd_event(path: str) -> int:
    event = load_json(Path(path))
    required = {'event', 'run_id', 'source_commit'}
    missing = sorted(required - set(event))
    if missing:
        print(json.dumps({'written': False, 'missing': missing}))
        return 4
    result = append_event(event, ROOT / 'runs' / 'events.jsonl')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(prog='brutus-control-plane')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('validate'); p.add_argument('manifest')
    p = sub.add_parser('fingerprint'); p.add_argument('manifest')
    p = sub.add_parser('check-transition'); p.add_argument('manifest'); p.add_argument('target')
    p = sub.add_parser('event'); p.add_argument('event_file')
    args = parser.parse_args()
    if args.command == 'validate': return cmd_validate(args.manifest)
    if args.command == 'fingerprint': return cmd_fingerprint(args.manifest)
    if args.command == 'check-transition': return cmd_transition(args.manifest, args.target)
    if args.command == 'event': return cmd_event(args.event_file)
    return 1

if __name__ == '__main__':
    raise SystemExit(main())
