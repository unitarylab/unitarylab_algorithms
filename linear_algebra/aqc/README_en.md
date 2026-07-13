# Discrete Adiabatic Quantum Linear Solver (AQC)

## Parameters

- `n`: Number of system qubits (1–6), determining the matrix dimension N = 2^n.
- `T`: Number of discrete adiabatic evolution steps (0 = auto-select based on condition number, T ≈ 10·κ).
- `p`: Adiabatic schedule parameter (> 1), defaults to 1.4, controlling the adiabatic evolution rate.

> **Summary**: This algorithm solves the linear system Ax = b via a Trotterized discrete adiabatic evolution on a quantum circuit, extracting the approximate solution by post-selecting the ancillary register on state |10000⟩.

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

1. **Problem Generation**: Generate a random well-conditioned Hermitian matrix A and right-hand side vector b based on the given system qubit count n, and normalize the inputs.
2. **Quantum Circuit Construction**: Create a circuit with n system qubits and 5 ancillary qubits. For each adiabatic step, apply 11 elementary operations sequentially: Hadamard gates, controlled rotations, block encodings, and reflections.
3. **Quantum Simulation Execution**: Simulate the quantum circuit execution on a classical computer to obtain the final state.
4. **Post-processing and Solution Extraction**: Extract the approximate solution x from the system register by post-selecting the ancillary register on state |10000⟩, then rescale to recover the original problem's solution.

---

## Core Idea

The core strategy of the discrete adiabatic quantum linear solver is to transform the problem of solving a linear system into an **adiabatic evolution process**. By encoding the target solution as a quantum ground state and starting from an easily prepared initial state, the system evolves slowly along a carefully designed discretized adiabatic path, remaining in its instantaneous ground state, ultimately reaching the quantum state that encodes the solution of Ax = b.

Key technical aspects:
- Embed the matrix inversion operation of A into a larger unitary matrix via **block encoding**
- Leverage the discrete (Trotterized) adiabatic theorem to discretize the continuous adiabatic evolution into T Trotter steps
- Each step consists of 11 sub-operations, symmetrically handling block encoding, state preparation, and reflection operations
- Dynamically adjust rotation angles during evolution via a scheduling function f(s) to balance adiabatic error and evolution speed

---

## Mathematical Principles

### Problem Setup

Solve the linear system $$Ax = b$$, where:
- $$A \in \mathbb{C}^{N \times N}$$ is a Hermitian matrix, $$\|A\|_2 = 1$$
- $$b \in \mathbb{C}^N$$ is a normalized right-hand side vector, $$\|b\| = 1$$
- $$N = 2^n$$ is a power of 2

### Adiabatic Evolution Framework

Construct a parameterized Hamiltonian path $$H(s)$$ satisfying:
- The ground state of $$H(0)$$ is the easily prepared initial state (encoding vector b)
- The ground state of $$H(1)$$ contains information about the target solution x

By slowly (adiabatically) varying the parameter s from 0 to 1, the system remains in the instantaneous ground state of $$H(s)$$.

### Discretization (Trotterization)

Discretize the continuous evolution $$[0, 1]$$ into T steps, with time parameter $$s = k/T$$ at step k. At the k-th step, apply the scheduled rotation angle:

$$\theta = 2 \arctan\left(\frac{f(s)}{1 - f(s)}\right)$$

where the scheduling function is defined as:

$$f(s) = \frac{\kappa}{\kappa - 1} \left(1 - \left(1 + s(\kappa^{p-1} - 1)\right)^{\frac{1}{1-p}}\right)$$

Here $$\kappa$$ is the condition number of matrix A, and p is the schedule parameter.

### Block Encoding

Construct the block encoding unitary of A via SVD:

$$\begin{bmatrix} A & \sqrt{I - A^2} \\ \sqrt{I - A^2} & -A \end{bmatrix}$$

This block encoding embeds A into the top-left block, providing quantum access to matrix A for the adiabatic evolution.

### Qubit Layout

Using little-endian layout:
- System register: qubits 0 to n-1 (n = log₂N)
- Ancillary register: qubits n to n+4 (5 ancillary qubits)

### Solution Extraction

The final state is post-selected on the ancillary register being in |10000⟩ (i.e., ancillary qubit 4 = |1⟩, the rest = |0⟩) to extract the solution vector from the system register.

---

## Algorithm Steps

1. **Input Validation and Preprocessing**: Check Hermiticity of A, that N is a power of 2, dimension matching, etc., and normalize A and b.
2. **Parameter Calculation**: Compute the condition number κ; if T is not specified, auto-set T = ceil(10·κ) and make it even.
3. **State Preparation**: Prepare the normalized |b⟩ state on the system register using a Householder reflection to construct $$U_b$$.
4. **Discrete Adiabatic Evolution**: For k = 1, 2, ..., T, sequentially apply 11 sub-operations:
   - Step 1: Hadamard gate on ancillary qubit 2
   - Step 2: CUQb1 module ($$U_b^\dagger$$-controlled NOT flip)
   - Step 3: Scheduled rotation (CZ + CRY)
   - Step 4: Controlled Hadamard gate
   - Step 5: Controlled block encoding of A
   - Step 6: X gate on ancillary qubit 1
   - Step 7: Controlled Hadamard gate
   - Step 8: Scheduled rotation (symmetric with step 3)
   - Step 9: CUQb1 module (symmetric with step 2)
   - Step 10: Hadamard gate on ancillary qubit 2
   - Step 11: Reflection operation
5. **Post-selection**: Post-select the ancillary register on |10000⟩ state, extract the quantum state of the system register.
6. **Rescaling**: Multiply by the internal scaling factor and recover the original problem's solution.

---

## Quantum Advantage

| Task | Classical Method | Quantum Advantage |
|---|---|---|
| Solving linear system Ax = b | Conjugate gradient O(N κ log(1/ε)) | For well-conditioned sparse matrices, quantum algorithms may achieve exponential speedup in condition number κ and precision ε |
| Matrix inversion | Gaussian elimination O(N³) | Under certain conditions (e.g., small κ), quantum algorithms can achieve O(poly(log N, κ)) complexity |

---

## Complexity Analysis

- **Qubit Count**: n_sys + 5, where n_sys = log₂(N)
- **Gate Complexity**: Each adiabatic step contains 11 sub-operations, each with complexity O(poly(n_sys))
- **Total Gate Depth**: O(T × poly(n_sys)), where T ≈ 10·κ
- **Practical Limitations**: When n_sys > 6 (i.e., N > 64), multi-controlled gates make the circuit depth impractically large
- **Schedule Parameter p**: p → 1⁺ minimizes the adiabatic error but slows down evolution; larger p values accelerate evolution but may increase non-adiabatic transitions

---

## Applications and Impact

- **Scientific Computing**: Provides a theoretical foundation for quantum-accelerated solutions of large-scale linear systems, with potential applications in computational fluid dynamics, structural mechanics, and other computationally intensive fields.
- **Quantum Machine Learning**: Linear system solving is a core subroutine in many machine learning algorithms, such as least squares regression and support vector machines.
- **Quantum Chemistry**: In quantum chemistry simulations, solving linear systems such as the Hartree-Fock equations is a critical step in computing molecular properties.
- **Theoretical Research**: The discrete adiabatic method offers an alternative perspective and toolkit for understanding and designing more general quantum linear algebra algorithms (such as HHL and its variants).
