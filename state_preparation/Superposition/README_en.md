# Sparse Superposition State Preparation Explained

## Parameter Settings

- `Psi`: Sparse target state vector. It must be non-zero and one-dimensional, with length no larger than $2^{\text{target\_qubits}}$.
- `target_qubits`: Number of target qubits used to represent the full computational basis.
- `target_error`: Allowed numerical preparation error.

> **Summary**: Sparse superposition state preparation exploits the case where only a small number of computational basis states have nonzero amplitudes. It first prepares a compact coefficient state over the active support size, then applies a permutation that maps compact indices to the true basis states.

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

1. **Parameter Preparation**:
   - Normalize and pad `Psi`.
   - Find the nonzero support set of the target state.
2. **Compact Coefficient Preparation**:
   - Collect the nonzero amplitudes into a compact vector.
   - Prepare this coefficient vector on the first $m$ logical indices.
3. **Support Permutation**:
   - Build a mapping from compact indices $|j\rangle$ to true support basis states $|x_j\rangle$.
   - Apply the corresponding permutation.
4. **Circuit and Matrix Construction**:
   - Combine the coefficient stage and permutation stage.
   - Produce the final circuit and dense evolution matrix.
5. **Result Output**:
   - Return the circuit, matrix, support information, and preparation error.

---

## Core Idea

If the target state is sparse,
$$
|\psi\rangle=\sum_{j=0}^{m-1}c_j|x_j\rangle,\qquad m\ll 2^n,
$$
there is no need to synthesize a full arbitrary state over all $2^n$ amplitudes. Instead, the algorithm prepares
$$
\sum_{j=0}^{m-1}c_j|j\rangle
$$
and then applies a permutation $P_S$ such that
$$
P_S|j\rangle=|x_j\rangle.
$$
The complete operation is
$$
U_{\text{superposition}}=P_SU_c.
$$

---

## Mathematical Principles

### Sparse Support

The support set is
$$
S=\{x:\psi_x\ne 0\}.
$$
If $|S|=m$, the coefficient stage only needs
$$
r=\lceil\log_2 m\rceil
$$
logical qubits to encode compact indices.

### Coefficient State

The nonzero coefficients are padded to dimension $2^r$:
$$
\tilde{c}=(c_0,\ldots,c_{m-1},0,\ldots,0).
$$
The coefficient unitary satisfies
$$
U_c|0\rangle=\tilde{c}.
$$

### Support Permutation

The support permutation is a unitary permutation matrix:
$$
P_S|j\rangle=|x_j\rangle.
$$
It moves the prepared compact amplitudes onto the requested computational basis states while preserving their coefficients.

---

## Algorithm Steps

1. Normalize and pad the target state.
2. Detect all basis indices with nonzero amplitudes.
3. Build the compact coefficient vector.
4. Pad the coefficient vector to the nearest power-of-two dimension.
5. Construct a coefficient-preparation unitary.
6. Construct the support permutation from compact indices to target basis states.
7. Compose the two stages and compute the preparation error.

---

## Quantum Advantage

| Task | Dense State Preparation | Sparse Superposition Preparation |
|------|-------------------------|----------------------------------|
| Nonzero amplitudes | Treats all $2^n$ entries | Uses only support size $m$ |
| State structure | Generic | Exploits sparse support |
| Preparation focus | Full vector | Compact coefficients plus permutation |

The method is advantageous when the target state has small support compared with the full Hilbert-space dimension.

---

## Complexity Analysis

- **Target Qubits**: $n$.
- **Support Size**: $m$ nonzero amplitudes.
- **Coefficient Register**: $\lceil\log_2 m\rceil$ logical indices before embedding.
- **Best Case**: Efficient when $m\ll 2^n$.
- **Worst Case**: Approaches generic state-preparation complexity when the state is dense.

---

## Applications and Impact

- Preparing sparse quantum states.
- Loading selected computational basis patterns.
- Creating benchmark states with controlled support size.
- Reducing state-preparation overhead for sparse amplitude-encoding tasks.
- Building structured initial states for search and combinatorial algorithms.
