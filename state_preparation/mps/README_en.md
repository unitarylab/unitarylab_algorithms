# MPS State Preparation Explained

## Parameter Settings

- `Psi`: Target quantum state vector. It must be non-zero and one-dimensional, with length no larger than $2^{\text{target\_qubits}}$.
- `target_qubits`: Number of system qubits in the target state.
- `target_error`: Allowed numerical preparation error.
- `mps`: Optional precomputed Matrix Product State tensors.
- `work_wires`: Optional auxiliary wires used to encode bond indices.
- `mps_max_bond_dim`: Optional maximum bond dimension when converting from a state vector.

> **Summary**: The MPS state-preparation algorithm uses a Matrix Product State representation to synthesize a quantum circuit. Each MPS tensor is embedded into a local unitary by QR completion, and auxiliary work qubits carry the bond index information between neighboring sites.

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
   - Use a supplied MPS or decompose the state vector into MPS tensors.
2. **MPS Validation**:
   - Check tensor shapes and adjacent bond dimensions.
   - Ensure bond dimensions can be encoded by the available work qubits.
3. **Canonicalization and Local Unitaries**:
   - Optionally convert the MPS to right-canonical form.
   - Embed each tensor into an isometry.
   - Complete each isometry into a full unitary using QR decomposition.
4. **Circuit Construction**:
   - Apply site unitaries over the current system qubit and shared work register.
   - Extract the system state from the work-zero subspace.
5. **Result Output**:
   - Return the circuit, full evolution matrix, extracted system unitary, and preparation error.

---

## Core Idea

An $n$-qubit state can be represented as
$$
\psi_{s_0s_1\cdots s_{n-1}}
=
\sum_{\alpha_0,\ldots,\alpha_{n-2}}
A^{(0)}_{s_0,\alpha_0}
A^{(1)}_{\alpha_0,s_1,\alpha_1}
\cdots
A^{(n-1)}_{\alpha_{n-2},s_{n-1}}.
$$
Instead of synthesizing a circuit directly from all $2^n$ amplitudes, the algorithm turns each local tensor $A^{(j)}$ into a local unitary. The work register stores the intermediate bond index $\alpha_j$.

---

## Mathematical Principles

### Bond Dimension and Work Qubits

If the maximum bond dimension is $\chi_{\max}$, the work register must satisfy
$$
2^{n_{\text{work}}}\ge \chi_{\max}.
$$
Thus at least $\lceil\log_2\chi_{\max}\rceil$ work qubits are required.

### Right-Canonical Isometry

For a right-canonical MPS tensor,
$$
\sum_{s,r}A_{\ell,s,r}A^*_{\ell',s,r}
=\delta_{\ell,\ell'}.
$$
This means that each fixed left-bond slice defines an orthonormal column vector:
$$
|v_\ell\rangle=\sum_{s,r}A_{\ell,s,r}|s\rangle|r\rangle.
$$

### QR Completion

The orthonormal tensor columns form an isometry. QR completion extends this isometry into a full unitary acting on one system qubit and the work register:
$$
U_j\in\mathbb{C}^{2^{1+n_{\text{work}}}\times 2^{1+n_{\text{work}}}}.
$$

---

## Algorithm Steps

1. Normalize the target state and determine the number of system qubits.
2. Convert the state vector to MPS tensors if no MPS is supplied.
3. Validate tensor shapes and bond dimensions.
4. Determine the required number of work qubits.
5. Optionally right-canonicalize the MPS.
6. Convert each tensor into a local unitary through QR completion.
7. Apply the local unitaries sequentially.
8. Extract the prepared system state from the work-zero subspace.
9. Compute the preparation error up to global phase.

---

## Quantum Advantage

| Task | Generic State Preparation | MPS State Preparation |
|------|---------------------------|-----------------------|
| Low-entanglement states | Often exponential gate count | Can exploit small bond dimension |
| Tensor-network states | Flattened into $2^n$ amplitudes | Uses local tensor structure |

The method is most useful when the target state has compact MPS structure. For highly entangled arbitrary states, the bond dimension can still grow exponentially.

---

## Complexity Analysis

- **System Qubits**: $n$.
- **Work Qubits**: $\lceil\log_2\chi_{\max}\rceil$.
- **Local Unitary Size**: $2^{1+n_{\text{work}}}\times 2^{1+n_{\text{work}}}$ per site.
- **Best Case**: Efficient for small bond dimension.
- **Worst Case**: Exponential if $\chi_{\max}$ grows exponentially with system size.

---

## Applications and Impact

- Preparing low-entanglement quantum states.
- Loading tensor-network states into quantum circuits.
- Comparing tensor-network preparation with general arbitrary-state methods.
- Studying truncation error from bounded bond dimension.
- Building structured state-preparation blocks for quantum simulation and QML.
