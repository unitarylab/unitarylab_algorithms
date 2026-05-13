# Quantum Signal Processing (QSP) Hamiltonian Simulation Explained

## Parameter Settings

- `H`: The input Hamiltonian matrix. It must be square and Hermitian. If its dimension is not a power of 2, the code pads it to the next power-of-2 dimension.
- `t`: The total evolution time that defines the target evolution scale of $e^{-iHt}$.
- `degree`: The allowed upper bound on the QSP polynomial degree. Default is `15`.

> **Summary**: This algorithm first block-encodes the Hamiltonian, then separately approximates the cosine and sine components through QSP, and finally combines them by linear combination of unitaries to build a time-slice evolution circuit. The final calculated result includes the approximate evolution matrix, the exact evolution matrix, the Frobenius-norm error between them, and the generated quantum circuit files.

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

1. **Input Formatting and Block-Encoding Setup**: Validate `H`, `t`, and `error`, normalize `H` into a Hermitian matrix, pad it if needed, and obtain a block encoding through `block_encode(H, method="nagy")`, including the scaling factor `alpha` and the total qubit count.
2. **Degree and Time-Slice Estimation**: Estimate the required QSP degree from `alpha`, `t`, and `error`, and automatically increase the number of time slices when the requested precision cannot be achieved within the given `degree`.
3. **Single-Slice QSP Construction**: Build QSP block encodings for $\beta\cos(tH)$ and $\beta\sin(tH)$ separately, then combine them via an LCU construction into a single-slice evolution circuit.
4. **Global Evolution and Error Computation**: If multiple slices are used, compose the slice matrix by matrix powers; at the same time, compute the exact matrix exponential $e^{-iHt}$ and evaluate the Frobenius-norm error.
5. **Result Output**: Save the approximate matrix, exact matrix, error, circuit diagram, and text report, then return the unified result dictionary.

---

## Core Idea

The key idea of QSP-based Hamiltonian simulation is to convert the target spectral action of $e^{-iHt}$ into a polynomial transformation problem on the eigenvalues of the Hamiltonian. After constructing a block encoding of the Hamiltonian, the algorithm uses a carefully designed sequence of single-qubit rotations and controlled unitaries so that the circuit implements a high-precision approximation of the target evolution, without explicitly expanding every Hamiltonian term as in Trotterization.

---

## Mathematical Principles

Let the block encoding scale the Hamiltonian as
$$
\frac{H}{\alpha}
$$
where $\alpha$ is the scaling factor returned by the encoding. For each time slice, the code uses the dimensionless parameter
$$
s = \alpha \cdot t_{\text{slice}}
$$
and constructs QSP polynomials that approximate
$$
\beta \cos(sx), \qquad \beta \sin(sx)
$$
where $x$ denotes the spectral variable of the scaled Hamiltonian. In the implementation, Bessel functions are used to generate Chebyshev coefficients; for example, the cosine block starts from
$$
c_0 = \beta J_0(s)
$$
and the remaining even or odd coefficients are filled accordingly for cosine and sine blocks. These two blocks are then combined through LCU to approximate
$$
U_{\text{approx}} \approx e^{-iHt}
$$
which is compared against the exact matrix
$$
U_{\text{exact}} = e^{-iHt}
$$
using the error metric
$$
\|U_{\text{approx}} - U_{\text{exact}}\|_F
$$
.

---

## Algorithm Steps

1. Convert the input Hamiltonian into a Hermitian matrix compatible with a qubit-register representation and build its block encoding.
2. Estimate the polynomial degree and the number of time slices required to meet the target error.
3. Construct QSP approximation circuits for the cosine and sine components separately.
4. Merge the real and imaginary parts with an LCU structure to obtain a single-slice approximate evolution operator.
5. If multiple slices are required, compose them into the full approximation and compare the result with the exact evolution matrix.

---

## Quantum Advantage

| Task | Traditional Decomposition Strategy | QSP Advantage |
|------|-----------------------------------|---------------|
| High-precision Hamiltonian simulation | High precision often requires deeper Trotter expansions | Polynomial spectral approximation can achieve high precision with more efficient circuit structure |

---

## Complexity Analysis

The resource cost of this implementation is determined mainly by three parts: the cost of the block-encoding circuit, the QSP polynomial degree `degree`, and the automatically selected number of time slices `time_slices`. Higher single-slice precision generally requires a higher polynomial degree; when the requested degree is insufficient, the code compensates by increasing the slice count. Therefore, the overall complexity grows jointly with the block-encoding cost and the product `degree × time_slices`.

---

## Applications and Impact

- It is suitable for Hamiltonian-simulation tasks that require high precision.
- It provides a direct Hamiltonian-simulation route built on modern block-encoding, QSP, and QSVT toolchains.
- It is especially relevant for long-time evolution, high-accuracy spectral transformations, and resource-optimized quantum circuit design.
