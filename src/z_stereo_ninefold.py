from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from typing import Iterable, Sequence

Q = Fraction


@dataclass(frozen=True)
class TracePoint:
    stage: str
    channel: str
    value: Fraction

    def canonical(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "channel": self.channel,
            "numerator": self.value.numerator,
            "denominator": self.value.denominator,
        }


def trace_hash(points: Iterable[TracePoint]) -> str:
    payload = [point.canonical() for point in points]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def fanout3(x: Fraction, delta: Fraction) -> tuple[Fraction, Fraction, Fraction]:
    """Exact 1->3 test transform with an exact arithmetic inverse-by-recombination."""
    return (x, x + delta, x - delta)


def recombine3(values: Sequence[Fraction]) -> Fraction:
    if len(values) != 3:
        raise ValueError("recombine3 requires exactly 3 channels")
    return sum(values, Q(0)) / 3


def mirror4(x: Fraction, delta: Fraction) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    """Four distinct mirror channels whose signed recombination recovers x exactly."""
    return (x + delta, x - delta, -x + delta, -x - delta)


def recombine4(values: Sequence[Fraction]) -> Fraction:
    if len(values) != 4:
        raise ValueError("recombine4 requires exactly 4 channels")
    a, b, c, d = values
    return (a + b - c - d) / 4


def route4(values: Sequence[Fraction], permutation: Sequence[int]) -> tuple[Fraction, ...]:
    if len(values) != 4 or sorted(permutation) != [0, 1, 2, 3]:
        raise ValueError("route4 requires a four-channel permutation")
    return tuple(values[i] for i in permutation)


def run_topology(
    x: Fraction,
    *,
    route: Sequence[int] = (0, 1, 2, 3),
) -> dict[str, object]:
    """
    Deterministic topology-only test:
    1 -> 3 -> 9 -> 36 -> 9 -> 3 -> 1.

    F1..F9 and G1..G36 are identity transforms here on purpose.
    This proves routing/recombination mechanics only; it does not validate
    the scientific formula bank.
    """
    traces: list[TracePoint] = [TracePoint("INPUT", "x0", x)]

    level1 = fanout3(x, Q(2, 7))
    traces += [TracePoint("Z1_1_TO_3", f"a{i+1}", v) for i, v in enumerate(level1)]

    groups9: list[tuple[Fraction, Fraction, Fraction]] = []
    majors: list[Fraction] = []
    for i, parent in enumerate(level1):
        group = fanout3(parent, Q(i + 1, 11))
        groups9.append(group)
        for j, value in enumerate(group):
            channel = i * 3 + j + 1
            majors.append(value)  # topology baseline: F_i = identity
            traces.append(TracePoint("F_MAJOR_IDENTITY", f"F{channel}", value))

    local_returns: list[Fraction] = []
    for i, major in enumerate(majors):
        mirror = mirror4(major, Q(i + 1, 37))
        routed = route4(mirror, route)
        for j, value in enumerate(routed):
            traces.append(TracePoint("G_SECONDARY_IDENTITY", f"G{i+1}.{j+1}", value))
        local_returns.append(recombine4(routed))
        traces.append(TracePoint("LOCAL_4_TO_1", f"R{i+1}", local_returns[-1]))

    level3: list[Fraction] = []
    for i in range(3):
        value = recombine3(local_returns[i * 3 : (i + 1) * 3])
        level3.append(value)
        traces.append(TracePoint("GLOBAL_9_TO_3", f"b{i+1}", value))

    output = recombine3(level3)
    traces.append(TracePoint("GLOBAL_3_TO_1", "y", output))

    local_errors = tuple(local_returns[i] - majors[i] for i in range(9))
    return {
        "input": x,
        "output": output,
        "global_error": output - x,
        "local_errors": local_errors,
        "identity_route": tuple(route) == (0, 1, 2, 3),
        "trace_points": len(traces),
        "trace_hash": trace_hash(traces),
    }
