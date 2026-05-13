# QSVT-Based Linear-System Solver Explained

## Parameter Settings

- `A`: The coefficient matrix of the linear system.
- `b`: The right-hand-side vector.
- `epsilon`: The target approximation accuracy passed to the underlying QSVT linear solver.

> **Summary**: This algorithm takes the matrix `A`, the vector `b`, and the target precision `epsilon`, then calls the repository implementation `QSVTSolver(A, b, epsilon)` to execute the QSVT-based linear-solver workflow. The final calculated result includes the solution vector, the scaling factor returned by the solver, the runtime, and the generated quantum circuit files.

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

1. **Input Recording and Parameter Passing**: Receive `A`, `b`, and `epsilon`, then register them in the algorithm input summary.
2. **Underlying QSVT Solver Call**: Invoke `QSVTSolver(A, b, epsilon)` to run the actual QSVT-based linear-solver routine, which returns a quantum circuit, a solution vector, and a scaling factor.
3. **Runtime Measurement**: Record the total time spent in the solver call.
4. **Result Assembly**: Store the solution vector, scaling factor, and simulation time in the output structure and generate the execution summary.
5. **File Export**: Save the quantum circuit diagram and the text result file, then return the unified result dictionary.

---

## Core Idea

The core idea of QSVT linear solving is to transform matrix inversion into a singular-value transformation problem. If a matrix `A` can be embedded into a unitary through block encoding, then quantum singular value transformation can approximately apply an inverse-like map of the form `1/x` to its singular values, thereby producing a quantum effect proportional to `A^{-1}` on the relevant state. In this repository, the current `algorithm.py` file does not implement those gate-level details directly; instead, it delegates the actual construction to `unitarylab.library.linear_solver.QSVTSolver`.

---

## Mathematical Principles

Let the singular value decomposition of the matrix be
$$
A = U \Sigma V^{\dagger}.
$$
The main idea of QSVT is that, if a unitary block encoding represents the matrix `A`, then alternating phase rotations can be used to apply a polynomial transformation to the singular-value matrix `\Sigma`, thereby approximating a desired matrix function. For the linear system
$$
A x = b,
$$
the key goal is to approximate a transformation corresponding to
$$
f(x) = \frac{1}{x}.
$$
This maps the singular values of `A` to their reciprocals and, after suitable normalization and post-processing, yields a quantum state proportional to the solution vector.

In the current repository implementation, the concrete block encoding, polynomial design, phase-sequence generation, and circuit synthesis are all encapsulated inside `QSVTSolver`; the present `algorithm.py` file is therefore a thin orchestration layer that passes inputs, receives the returned circuit and solution, and saves the outputs.

---

## Algorithm Steps

1. Read the matrix `A`, the vector `b`, and the error parameter `epsilon`.
2. Call the underlying `QSVTSolver` to construct and execute the QSVT linear-solver workflow.
3. Receive the resulting quantum circuit, solution vector, and scaling factor.
4. Measure the runtime and write the outputs into the result structure.
5. Export the circuit diagram and the text result file.

---

## Quantum Advantage

| Task | Classical Solving Strategy | QSVT Quantum Advantage |
|------|----------------------------|-------------------------|
| Linear-system solving | Usually relies on matrix factorizations or iterative inverse-related methods | Recasts inversion as a singular-value transformation problem and provides a unified quantum framework for high-precision linear-algebra subroutines |

---

## Complexity Analysis

From this file alone, the directly visible cost is dominated by a single call to the underlying `QSVTSolver` plus circuit-export overhead. Finer-grained complexity depends on the lower-level QSVT implementation, including the block-encoding strategy, polynomial degree, target accuracy `epsilon`, and the condition properties of the matrix. In other words, this file is a lightweight wrapper, while the true circuit depth and resource cost are determined by the library solver.

---

## Applications and Impact

- It can serve as a linear-solver subroutine in quantum linear algebra and quantum machine-learning workflows.
- It is a representative interface for applying the QSVT framework to linear-system solving.
- It provides an entry point for further study of block encoding, matrix-function approximation, and advanced quantum numerical algorithms.
