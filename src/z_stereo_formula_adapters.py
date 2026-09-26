from __future__ import annotations

from dataclasses import dataclass


F1_SOURCE_REPO = "Topbrutus/brutus-pell-square-rank-relation"
F1_SOURCE_COMMIT = "aa08bd336662dea0b6c836c273cf7f7d59f4a672"
F1_SOURCE_PATH = "README.md"


@dataclass(frozen=True)
class TypedValue:
    kind: str
    value: int
    channel: str
    formula_id: str
    source_repo: str
    source_commit: str
    source_path: str


def f1_pell_rank_21_power(k: int, *, channel: str = "F1") -> TypedValue:
    """
    Execute the pinned F1 relation only.

    Contract:
        input  : integer k >= 2
        output : integer z_P(21^k) = 4*21^(k-1)

    This adapter does not normalize the result into the global 9->3->1
    recombination space. That remains intentionally disabled.
    """
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("F1 requires integer k")
    if k < 2:
        raise ValueError("F1 requires k >= 2")

    result = 4 * (21 ** (k - 1))
    return TypedValue(
        kind="pell_rank_integer",
        value=result,
        channel=channel,
        formula_id="F1",
        source_repo=F1_SOURCE_REPO,
        source_commit=F1_SOURCE_COMMIT,
        source_path=F1_SOURCE_PATH,
    )
