# Z-STEREO NINEFOLD — candidate architecture

Status: **OBSERVATION / CANDIDATE ARCHITECTURE**

This document defines the topology discussed for Brutus Control Plane. It is an orchestration contract, not a claim that the underlying formulas are mathematically validated.

## Core topology

```text
1 input
  |
  v
Z fanout
1 -> 3
  |
  v
Z fanout x3
3 -> 9
  |
  +--> x1 -> F1 --+
  +--> x2 -> F2 --+
  +--> ...        +--> 9 major results
  +--> x9 -> F9 --+
                    |
                    v
          mirror Z on each result
              9 x (1 -> 4)
                    |
                    v
                36 channels
                    |
         G_ij secondary calculations
                    |
             local recombination
                9 x (4 -> 1)
                    |
                    v
              9 checkpoints
                    |
               9 -> 3 -> 1
                    |
                    v
                final output
```

Compact form:

[
1 \rightarrow 3 \rightarrow 9
\rightarrow F_{1..9}
\rightarrow 36
\rightarrow G_{1..36}
\rightarrow 9
\rightarrow 3
\rightarrow 1
]

## Control Plane mapping

**PRIMARY** owns the deterministic forward fanout and the nine major formula slots (F_1..F_9).

**MIRROR** decomposes each major result into four mirror channels. Nine major results therefore produce 36 mirror channels.

**COUNTERTEST** compares the baseline identity routing with explicitly declared cross-routing matrices (P_i). No invisible or implicit cross-link is allowed.

**PRECISION** runs the secondary calculation family on the 36 channels. Candidate families include precision checks, residuals, invariants and the proposed Neo-constant calculations. Their exact definitions remain external and must be pinned by repository, commit, formula identifier and parameters.

**ARBITER** verifies the nine local checkpoints and the complete trace before allowing the global recombination (9\rightarrow3\rightarrow1). ARBITER does not recalculate the scientific result.

## Local checkpoint

For major channel (i):

[
x_i \xrightarrow{F_i} y_i
]

Mirror decomposition:

[
y_i \xrightarrow{Z_{mirror}}
(y_{i1},y_{i2},y_{i3},y_{i4})
]

Optional controlled routing:

[
q_i=P_i y_i
]

Secondary checks:

[
g_{ij}=G_{ij}(q_{ij})
]

Local recombination:

[
\hat y_i=R_i(g_{i1},g_{i2},g_{i3},g_{i4})
]

Checkpoint:

[
e_i=\hat y_i-y_i
]

Exact equality is required only when the declared transformation is intended to be exactly reversible. Otherwise the manifest must declare the expected invariant or tolerance.

## Trace rule

Every edge records at minimum:

- source channel and destination channel;
- input and output hashes;
- formula identifier and pinned source commit;
- parameters and numerical precision;
- routing matrix (P_i), including identity routing;
- sequence/tick;
- local error or expected invariant.

The governing rule remains:

> **NO PROMOTION WITHOUT TRACE.**

## First experimental sequence

1. Run the topology with identity routing only.
2. Use simple, explicitly defined test formulas before the complex formula bank.
3. Verify all nine local (4\rightarrow1) checkpoints.
4. Verify the global (9\rightarrow3\rightarrow1) recombination.
5. Only then pin the nine major formulas and 36 secondary checks.
6. Cross-routing experiments come after a clean baseline.

This preserves the existing Brutus Control Plane principle: the control plane coordinates evidence and reproducibility; the scientific engines remain external.
