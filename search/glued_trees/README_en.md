# Glued Trees Quantum Walk Algorithm Explained

## Parameter Settings

- `qubits`: Register size from 4 to 8; default 6, with $n=qubits-2$.
- `seed`: Random seed for glued edges and sampling; default 0.
- `shots`: Samples per time point; default 8192.
- `repetitions`: Suzuki–Trotter steps per time point; default 10, matching the source notebook.
- `order`: Product-formula order 1 or 2; default 1.
- `max_terms`: Optional Pauli-term limit; empty keeps the full expansion.
- `backend`: `numpy` or `torch`; default `numpy`.
- `times`: Comma-separated times; empty uses $2n+\{-12,-10,\ldots,12\}$.

> **Summary**: The algorithm maps randomly glued binary trees to a coupled-oscillator Hamiltonian and estimates entrance-to-exit transport with Pauli evolution and Suzuki–Trotter steps.

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

1. Build two balanced binary trees and randomly glue their leaves.
2. Form the stiffness matrix and block Hamiltonian.
3. Decompose the Hamiltonian into Pauli strings.
4. Generate `time_points = 2*n + np.arange(-12, 13, 2)` by default.
5. Independently evolve and sample the entrance state at every time point.
6. Export the exit-probability curve, representative circuit, and report.

---

## Core Idea

The left root is the entrance and the right root is the exit. Random leaf connections obscure local directional information, while coherent propagation can exploit interference. This implementation interprets the graph as coupled oscillators and converts their second-order dynamics into first-order quantum evolution.

---

## Mathematical Principles

For adjacency matrix $A$,

$$K=3I-A=BB^\dagger,$$

and the Hermitian embedding is

$$H=-\begin{bmatrix}0&B\\B^\dagger&0\end{bmatrix}=\sum_jc_jP_j.$$

With $r=repetitions$ and $\Delta t=t/r$,

$$e^{-iHt}\approx\left(\prod_j e^{-ic_jP_j\Delta t}\right)^r.$$

Second order uses a symmetric half/full/half sequence. The source notebook fixes $r=10$ for every time, so $\Delta t=t/10$ changes with $t$. `times` controls physical duration; `repetitions` controls its internal discretization.

---

## Algorithm Steps

1. Compute tree depth and vertex count.
2. Construct the seeded glued graph.
3. Calculate $A$, $K$, $B$, and $H$.
4. Decompose and sort all Pauli terms.
5. Optionally crop with `max_terms`.
6. Evolve for $r$ steps at every time and sample the exit state.
7. Aggregate and export the results.

---

## Quantum Advantage

| Task | Classical local exploration | Glued-trees quantum walk |
|---|---|---|
| Cross random glued leaves | Explore many indistinguishable branches | Exploit coherent propagation and interference |

The theoretical oracle problem shows an exponential separation from classical randomized algorithms. This state-vector implementation demonstrates that structure but does not provide wall-clock speedup on classical hardware.

---

## Complexity Analysis

- $N=2^{n+1}-2$ graph vertices.
- $O(4^q)$ dense-Hamiltonian storage.
- Up to $4^q$ Pauli terms in a complete expansion.
- About $O(Lrm)$ first-order term blocks for $L$ times and $m$ terms.
- Cropping changes $H$; more Trotter steps cannot remove truncation error.

---

## Applications and Impact

Applications include quantum walks, Hamiltonian simulation, coupled-oscillator embeddings, product-formula error studies, and teaching the distinct roles of time, Trotter steps, shots, and Pauli truncation.
