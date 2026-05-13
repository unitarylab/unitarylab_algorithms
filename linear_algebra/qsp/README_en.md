# Quantum Signal Processing (QSP) Explained

## Parameter Settings

- `t`: The target evolution-time parameter used to define the function `cos(t x)` to be approximated.
- `d`: The QSP polynomial degree, which is also one less than the length of the optimized phase sequence.
- `x`: The test eigenvalue point. The default value is `0.1`, and it should lie in `[-1, 1]`.

> **Summary**: This implementation uses quantum signal processing on a single-qubit circuit to approximate the target function `cos(t x)`, first by numerically optimizing a phase sequence and then by building the alternating signal-and-phase circuit. The final calculated result includes the QSP estimated value, the theoretical value `cos(t x)`, the absolute error, and the generated quantum circuit files.

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

1. **Target-Function Analysis and Phase Optimization**: For the given `t` and `d`, sample `2d+1` points on `[-1,1]` and use `L-BFGS-B` to minimize the mean squared error between the QSP polynomial response and `cos(t x)`, producing the phase sequence.
2. **QSP Circuit Construction**: Build a single-qubit circuit, apply the initial `Rz` phase rotation, and then alternate the signal operator and phase rotations, where `a = arccos(x)` determines the `Rx(2a)` angle.
3. **Quantum Simulation**: Execute the constructed single-qubit QSP circuit and obtain the final quantum state.
4. **Accuracy Comparison and Post-processing**: Read the first amplitude of the final state as the estimated QSP value, compare it with the theoretical value `cos(t x)`, and compute the absolute error.
5. **Result Output**: Save the estimated value, the theoretical value, the absolute error, the runtime, and the circuit and text output files.

---

## Core Idea

The core idea of QSP is to use a carefully designed sequence of phase rotations so that the spectrum of a signal operator is transformed into a target polynomial function. For a given eigenvalue `x`, the signal operator and the phase sequence jointly determine the functional form of a matrix element of the final unitary. Once the phase sequence is chosen correctly, that matrix element approximates the desired target function.

---

## Mathematical Principles

In this implementation, the target function is
$$
f(x) = \cos(t x).
$$
For each sample point `x`, the code defines
$$
a = \arccos(x)
$$
and constructs the signal operator
$$
W(x) = \begin{pmatrix}
x & i\sqrt{1-x^2} \\
i\sqrt{1-x^2} & x
\end{pmatrix}.
$$
If the phase sequence is written as $\phi_0, \phi_1, \ldots, \phi_d$, then the associated QSP transform is
$$
U_\phi(x) = R_z(\phi_0) \prod_{k=1}^{d} \left[ W(x) R_z(\phi_k) \right].
$$
The code numerically optimizes the phase sequence by minimizing
$$
\frac{1}{2d+1} \sum_x |(U_\phi(x))_{00} - \cos(t x)|^2
$$
over the sampled points. In the circuit implementation, `W(x)` is represented by a single-qubit `Rx(2a)` rotation, and each phase factor is implemented by `Rz(2 phi_k)`.

---

## Algorithm Steps

1. Optimize a phase sequence over sampled points so that the QSP matrix element approximates `cos(t x)`.
2. Compute `a = arccos(x)` for the requested test point.
3. Construct the single-qubit QSP circuit from alternating `Rz` and `Rx` operations.
4. Run the quantum simulation and read out the estimated value from the output amplitude.
5. Compare the estimate with the theoretical value and report the absolute error.

---

## Quantum Advantage

| Task | Direct Realization | QSP Advantage |
|------|--------------------|---------------|
| Spectral-function or polynomial transformation | Target functions generally cannot be applied directly as quantum gates on spectra | Encodes the target polynomial into a unitary circuit element through a phase sequence, giving a unified framework for matrix functions, block encoding, and QSVT |

---

## Complexity Analysis

The main cost of this implementation has two parts. The first is the classical phase optimization, whose cost grows with the polynomial degree `d` and the `2d+1` sample points. The second is the quantum circuit itself, whose depth grows linearly with the phase-sequence length and therefore contains about `d` signal-operator calls and `d+1` `Rz` rotations. Increasing `d` can improve approximation quality, but it also makes the phase search harder and lengthens the circuit.

---

## Applications and Impact

- It is a key building block for quantum singular value transformation, block-encoded matrix functions, and related linear-algebra algorithms.
- It can be used to construct Hamiltonian functions, matrix polynomials, and filtering-style quantum transforms.
- It also serves as an important bridge between single-qubit phase design and higher-dimensional quantum linear-algebra methods.
