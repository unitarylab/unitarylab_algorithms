# Variational Quantum Linear Solver (VQLS)

## Parameter Settings

- `coefficients`: Linear combination coefficients `[c_0, c_1, c_2]`. The default value is `[1.0, 0.2, 0.2]` to build the matrix `A = c_0 A_0 + c_1 A_1 + c_2 A_2`.
- `max_iterations`: Maximum number of COBYLA optimization iterations. The default value is `200`.
- `tolerance`: Optimization convergence tolerance. The default value is `1e-6`.

> **Summary**: This algorithm uses a variational quantum circuit to solve a structured linear system, first constructing the problem matrix and right-hand-side state, then defining a local Hadamard-test cost and optimizing a parameterized ansatz with COBYLA. The final calculated result includes the fidelity between the quantum and classical solutions, the relative error, the residual norm, both solution states, and the generated quantum circuit files.

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

1. **Parameter Preparation and Problem Initialization**: Validate `n_qubits`, set the system and ancilla qubits, define the linear-combination coefficients, and construct the problem matrix `A_num`.
2. **Variational Circuit Construction**: Build the `|b>` preparation circuit `U_b`, the parameterized ansatz, and an example local Hadamard-test circuit used for visualization.
3. **Variational Optimization**: Start from random initial parameters and use COBYLA to minimize the local cost function `_cost_loc`, obtaining the optimized parameters and final loss value.
4. **Classical Post-processing and Accuracy Analysis**: Extract the quantum solution state from the optimized ansatz, compute the exact classical solution, and evaluate fidelity, relative error, and residual norm.
5. **Result Export**: Save the example circuit diagram, the text result file, and the unified result dictionary.

---

## Core Idea

The core idea of VQLS is to represent a candidate solution state `|x(theta)>` with a parameterized quantum circuit and then use a specially designed cost function to measure how closely `A|x(theta)>` matches the target state `|b>`. Once that cost becomes sufficiently small, the optimized quantum state approximates the solution of the linear system. Instead of explicitly constructing a matrix inverse, VQLS turns the problem into a hybrid quantum-classical optimization task.

---

## Mathematical Principles
VQLS solves the linear system `Ax = b` with a variational quantum algorithm. In the current implementation, the problem matrix is explicitly built as
$$
A = c_0 A_0 + c_1 A_1 + c_2 A_2,
$$
where `A_0` is the identity matrix and `A_1`, `A_2` are Pauli-structured matrices chosen according to `n_qubits`; the right-hand-side state `|b>` is prepared by applying Hadamard gates on all system qubits.

The key ingredient is a local cost function. The code uses local Hadamard tests to estimate complex coefficients
$$
\mu_{l,l',j},
$$
then combines them into the norm term
$$
\langle \psi | \psi \rangle
$$
and the local loss
$$
C_L = \frac{1}{2} - \frac{1}{2} \cdot \frac{|\sum_{l,l',j} c_l c_{l'}^* \mu_{l,l',j}|}{n\, \langle \psi | \psi \rangle}.
$$
When this loss approaches zero, the variational state better satisfies `A|x> ≈ |b>`. The implementation optimizes the parameters with COBYLA and then compares the resulting quantum state with the classical reference solution `np.linalg.solve(A_num, b_state)`.

---

## Algorithm Steps

1. Build the problem matrix and target state `|b>` from `n_qubits` and `coefficients`.
2. Construct the ansatz, controlled `A_l` operations, and local Hadamard-test circuits.
3. Optimize the variational parameters with COBYLA to minimize the local loss.
4. Extract the quantum solution state and compute the classical reference solution.
5. Report fidelity, relative error, residual norm, and circuit outputs.

---

## Quantum Advantage

| Task | Classical Methods | VQLS Advantage |
|---|---|---|
| Linear-system solving | Direct inversion or matrix factorization typically requires a full classical representation | Recasts solving into a variational state-preparation and hybrid optimization problem suitable for NISQ-style quantum workflows |

---

## Complexity Analysis

The cost of this implementation is mainly determined by three factors: the number of local Hadamard-test evaluations, the simulation cost of each quantum circuit, and the optimization iteration budget `max_iterations`. Because the cost function evaluates many combinations of `l`, `l'`, and `j` at each iteration, the total number of circuit evaluations grows with the number of system qubits and operator terms. As a result, VQLS trades exact direct solving for a variational approximation strategy that requires repeated measurements and classical optimization rounds.

---

## Applications and Impact

- It is useful for studying hybrid quantum-classical linear solvers in the NISQ setting.
- It serves as a concrete example of variational algorithms, local Hadamard tests, and quantum linear algebra.
- It provides a foundation for extending the solver to more general problem Hamiltonians and ansatz designs.
