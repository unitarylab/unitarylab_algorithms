# Multiplexer State Preparation Explained

## Parameter Settings

- `Psi`: Target quantum state vector. It must be non-zero and one-dimensional, with length no larger than $2^{\text{target\_qubits}}$.
- `target_qubits`: Number of target qubits used to prepare the state.
- `target_error`: Allowed numerical preparation error.

> **Summary**: The multiplexer state-preparation algorithm prepares an arbitrary target state by recursively splitting probability mass with controlled $R_Y$ rotations, then adding basis-state phases. It treats amplitudes as leaves of a binary tree and uses multiplexed rotations to distribute probability from the root to each computational basis state.

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
   - Normalize and pad `Psi` to dimension $2^n$.
   - Split each target amplitude into magnitude and phase.
2. **Probability Tree Construction**:
   - Build a binary tree over computational basis amplitudes.
   - For each node, calculate the probability mass of its left and right children.
3. **Controlled Rotation Synthesis**:
   - Apply an $R_Y$ rotation at the root.
   - Apply controlled or multi-controlled $R_Y$ rotations in deeper tree levels.
4. **Phase Compensation**:
   - Add a basis-state selective phase for every nonzero target phase.
5. **Result Output**:
   - Return the circuit, dense matrix, and preparation error.

---

## Core Idea

For
$$
|\psi\rangle=\sum_{j=0}^{2^n-1}a_j|j\rangle
=\sum_j r_je^{i\phi_j}|j\rangle,
$$
the algorithm first prepares
$$
|\psi_r\rangle=\sum_j r_j|j\rangle
$$
using recursive controlled $R_Y$ rotations. It then applies the diagonal phase operation
$$
D=\sum_j e^{i\phi_j}|j\rangle\langle j|
$$
to obtain the final complex target state.

---

## Mathematical Principles

### Binary Probability Splitting

At each tree node, let
$$
P_L=\sum_{j\in L}r_j^2,\qquad P_R=\sum_{j\in R}r_j^2.
$$
Define
$$
L=\sqrt{P_L},\qquad R=\sqrt{P_R}.
$$
The rotation angle is
$$
\theta=2\arctan2(R,L).
$$
Then
$$
R_Y(\theta)|0\rangle
=\cos(\theta/2)|0\rangle+\sin(\theta/2)|1\rangle
$$
distributes the current probability mass in the same ratio as the target node split.

### Multiplexed Control

At level $\ell$, the previous $\ell$ bits specify a tree branch. The algorithm applies an $R_Y$ rotation only when the control prefix matches that branch. This implements a different rotation angle for each subtree.

### Phase Diagonal

The amplitude stage preserves nonnegative magnitudes. A final diagonal operation adds the target phase to each computational basis state without changing probabilities.

---

## Algorithm Steps

1. Normalize and pad the target vector.
2. Compute magnitudes $r_j$ and phases $\phi_j$.
3. Recursively compute probability splits over the binary tree.
4. Emit root, controlled, and multi-controlled $R_Y$ rotations.
5. Apply selective phase gates for basis states with nonzero phase.
6. Build the final circuit and matrix.
7. Compare the prepared state with the target state.

---

## Quantum Advantage

| Task | Direct Construction | Multiplexer Construction |
|------|---------------------|--------------------------|
| Probability loading | Dense state-vector update | Recursive controlled rotations |
| Phase loading | Full diagonal matrix | Basis-state selective phases |

The algorithm provides a transparent circuit synthesis method for arbitrary state preparation. It is especially useful as an exact baseline for small and medium state-loading experiments.

---

## Complexity Analysis

- **Qubit Cost**: $n$ target qubits.
- **Gate Cost**: Exponential for arbitrary dense states because the binary tree has $O(2^n)$ leaves.
- **Controlled Operations**: Multi-controlled rotations appear at deeper tree levels and may require additional decomposition by the backend.

---

## Applications and Impact

- Exact arbitrary state preparation on small systems.
- Benchmarking against Mottönen and MPS-based state preparation.
- Testing controlled-rotation decomposition and compiler behavior.
- Loading probability distributions for amplitude-encoding demonstrations.
