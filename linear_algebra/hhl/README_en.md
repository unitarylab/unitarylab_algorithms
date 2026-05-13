# HHL Algorithm for Linear Systems Explained

## Parameter Settings

- `A`: The Hermitian matrix to be solved. It must be square, and its dimension must be a power of 2.
- `b`: The right-hand-side vector used to prepare the initial state $|b\rangle$. Its length must match the dimension of `A`, and it cannot be the zero vector.
- `d`: The number of phase-register qubits used in quantum phase estimation, which controls eigenvalue resolution. The default value is `11`.

> **Summary**: The HHL algorithm takes the matrix `A`, the vector `b`, and the phase-register size `d`, then builds a quantum linear-system solver through QPE, controlled reciprocal rotation, and inverse QPE. The final calculated result includes the quantum-estimated solution vector, the exact classical solution, the L2 error between them, the post-selection success probability, and the generated quantum circuit files.

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

1. **Matrix Preprocessing and Adaptive Parameter Analysis**: Validate that `A` is Hermitian and power-of-2 sized, verify the shape and norm of `b`, then analyze the eigenvalue spectrum to determine the evolution time `t`, the phase starting point `k_start`, and the scaling factor `scale_factor`.
2. **Quantum Circuit Construction**: Normalize and initialize `b` on the system register, construct the unitary circuit for $e^{iAt}$, then append QPE, the controlled reciprocal-rotation module, and inverse QPE.
3. **Quantum Simulation**: Execute the full HHL circuit and obtain the final quantum state.
4. **Classical Post-processing**: Post-select the branch with ancilla=1 and zero phase register, extract the system solution vector, and compare it with the classical solution `np.linalg.solve(A, b)` to compute the L2 error.
5. **Result Output**: Save the quantum-estimated solution, the classical exact solution, the post-selection probability, the error, the circuit diagram, and the text report, then return the unified result dictionary.

---

## Core Idea

The key idea of HHL is to transform the linear system
$$
A\mathbf{x} = \mathbf{b}
$$
into a spectral transformation problem. If $|b\rangle$ is expanded in the eigenbasis of $A$, then applying a mapping proportional to $1/\lambda_j$ on each eigencomponent produces a quantum state proportional to the solution vector $|x\rangle$. In the code, QPE extracts the eigenphase information, the controlled rotation implements the reciprocal mapping, and inverse QPE removes the entanglement so that post-selection can isolate the desired solution state.

---

## Mathematical Principles

Let the Hermitian matrix $A$ satisfy
$$
A|u_j\rangle = \lambda_j |u_j\rangle
$$
and suppose the right-hand side is expanded as
$$
|b\rangle = \sum_j \beta_j |u_j\rangle.
$$
Then the linear-system solution is proportional to
$$
|x\rangle \propto \sum_j \frac{\beta_j}{\lambda_j} |u_j\rangle.
$$
HHL uses quantum phase estimation to write eigenvalue information into a phase register, followed by a controlled rotation of the form
$$
|\lambda_j\rangle |0\rangle \mapsto |\lambda_j\rangle \left(\sqrt{1-C^2/\lambda_j^2}|0\rangle + C/\lambda_j |1\rangle\right)
$$
so that the reciprocal factor is encoded into the amplitude of an ancilla qubit. In this implementation, the evolution time `t` is chosen adaptively from the spectrum so that the phase grid can resolve the relevant eigenvalues, and a signed-phase mode is enabled when negative eigenvalues are present. After inverse QPE, the code post-selects ancilla=1 and a zero phase register, then rescales the extracted state to obtain the quantum approximate solution.

---

## Algorithm Steps

1. Validate the matrix `A` and vector `b`, and normalize `b` into the initial quantum state.
2. Build the unitary circuit for $e^{iAt}$ and use QPE to encode eigenphase information.
3. Apply the controlled reciprocal rotation to encode $1/\lambda_j$ into the ancilla amplitudes.
4. Run inverse QPE to disentangle the phase register from the system register.
5. Post-select the ancilla and phase registers, reconstruct the approximate quantum solution, and compare it with the classical one.

---

## Quantum Advantage

| Task | Classical Methods | HHL Advantage |
|------|-------------------|---------------|
| Linear-system solving | High-dimensional dense systems usually require polynomial or worse cost | Under sparsity, condition-number, and readout assumptions, HHL can offer more favorable scaling in problem size |

---

## Complexity Analysis

The theoretical complexity of HHL depends on matrix sparsity, condition number, eigenvalue gap structure, and the requested precision. In this implementation, the main cost comes from the phase-register size `d`, the controlled reciprocal-rotation module, and the classical simulation of the full quantum state. Therefore, while HHL has strong theoretical advantages for suitable problem families, matrix-level simulation overhead remains the main practical bottleneck in this repository implementation.

---

## Applications and Impact

- It can be used in subroutines for quantum machine learning, discretized PDE systems, and scientific computing.
- It is one of the most representative foundational algorithms in quantum numerical linear algebra.
- It provides the conceptual basis for later quantum linear solvers, QSVT-based linear algebra, and quantum data-processing methods.
