# Quantum Backtracking Search Explained

## Parameter Settings

- `problem_json`: A `binary_cnf` or `prefix_constraints` JSON object; empty uses a depth-two example.
- `phase_bits`: QPE phase-register size; default 3.
- `shots`: Phase samples per subtree detection; default 128.
- `seed`: Sampling seed; default 7.
- `threshold`: Zero-phase frequency threshold; default $3/8$.
- `backend/device/dtype`: Forwarded to predicate and QPE execution, defaulting to `numpy/cpu/complex128` to preserve the source configuration. CLI/Web dtype strings are converted by the entry points. Other configurations remain unvalidated.

## API and limits

```python
from unitarylab_algorithms import QuantumBacktrackingAlgorithm

algorithm = QuantumBacktrackingAlgorithm(algo_dir="results/search/quantum_backtracking")
result = algorithm.run()  # Built-in depth-two example; not executed in this task
print(result["exists"], result["solution_path"])
```

`status='ok'` means execution completed. Inspect `exists` for detection: finite phase precision and sampling can miss solutions, so `exists=False` is not an unsatisfiability proof. Input accepts JSON strings or dictionaries without mutating the caller's data. CNF literals use signed one-based variable indices. Path bits follow variable order; the phase register occupies the low bits. Accepted prefixes can produce partial assignments.

Return fields are `problem`, `exists`, `solution_path`, `solution_assignment`, `evidence`, `resource_report`, `artifacts`, `Elapsed time (s)` plus base fields `status/circuit_path/plot/circuit`. Standard run saves SVG/TXT and leaves `artifacts` empty. The retained research `main()` and `Solver.solve(output_dir, full_artifacts=...)` have separate PNG/QASM/report behavior. `main()` is not invoked automatically; its default example_problem.json is absent in the supplied source folder, so pass an explicit problem file when calling it.

With depth d, reject work count r, and phase bits p, walk uses `2d+3+r` qubits, QPE `2d+3+r+p`, and child oracle `3d+7+r`. Here r is the CNF clause count or rejected-prefix count. The resource report also builds the child oracle. Dense simulation grows exponentially. Only static inspection was performed; no performance claims are validated.

> **Summary**: The algorithm partitions a backtracking tree into alternating reflections, forms $W=R_BR_A$, and uses QPE to detect solution-bearing subtrees and recover an accepted path.

---

## Table of Contents

- [Execution Flow](#execution-flow)
- [Core Idea](#core-idea)
- [Mathematical Principles](#mathematical-principles)
- [Algorithm Steps](#algorithm-steps)
- [Quantum Advantage](#quantum-advantage)
- [Complexity Analysis](#complexity-analysis)
- [Applications and Impact](#applications-and-impact)

---

## Execution Flow

Parse constraints, construct reversible predicates and node encoding, build alternating reflections and their walk, perform controlled-walk QPE at each candidate subtree, descend through positive detections, and export the representative circuit and resource report.

---

## Core Idea

Local parent-child diffusion operators become reflections over alternating tree levels. A solution-bearing subtree gives its root state detectable weight in the zero-phase subspace of the walk, so QPE acts as a quantum subtree-existence test.

---

## Mathematical Principles

$$R_A=\bigoplus_{x\in A}D_x,\qquad R_B=\bigoplus_{x\in B}D_x,\qquad W=R_BR_A.$$

For $W=\sum_j e^{i\theta_j}|u_j\rangle\langle u_j|$, the all-zero QPE outcome estimates the root state's weight in the $\theta_j=0$ spectral subspace. Finite sampling compares that frequency with `threshold`.

---

## Algorithm Steps

Validate constraints, encode nodes, build reversible predicates, synthesize local reflections, compose the walk, detect the root subtree with QPE, descend through positive child tests, and verify the recovered path.

---

## Quantum Advantage

Under the assumptions of the Montanaro framework, a tree of size $T$ and depth $n$ can be explored with approximately $\widetilde O(\sqrt{Tn})$ quantum detection work instead of classical $O(T)$ node exploration. Oracle cost, spectral gap, precision, and error bounds determine practical behavior.

---

## Complexity Analysis

With $p$ phase qubits, QPE uses about $2^p-1$ controlled-walk applications. Tree depth, predicate work qubits, and phase precision rapidly increase classical state-vector cost, so the default example is intentionally small.

---

## Applications and Impact

Applications include SAT/CSP, scheduling, constrained path search, and studies combining quantum walks, phase estimation, and classical backtracking.
