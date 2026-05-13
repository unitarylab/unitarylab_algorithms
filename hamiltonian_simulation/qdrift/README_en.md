# qDrift Algorithm Explained

## Parameter Settings

- `H`: The input Hamiltonian matrix. It must be square and Hermitian. If its dimension is not a power of 2, the code pads it with zeros to the next power-of-2 dimension.
- `t`: The total evolution time used to scale the evolution angle of each randomly sampled Pauli term.
- `steps`: The total number of random samples, which determines the length of the qDrift sequence. Default is `5000`.

> **Summary**: The qDrift algorithm decomposes the Hamiltonian matrix into Pauli terms, randomly samples them according to coefficient magnitudes, and builds a random product formula approximation of $e^{-iHt}$. The final calculated result includes the approximate evolution matrix, the exact evolution matrix, the Frobenius-norm error between them, and the generated circuit files.

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

1. **Input Formatting and Validation**: Check the validity of `t` and `error`, convert `H` into a complex matrix, verify that it is square and Hermitian, and pad it to the next power-of-2 dimension when needed.
2. **Pauli Decomposition**: Call `pauli_string_decomposition(H)` to express the Hamiltonian as a linear combination of Pauli strings and coefficients.
3. **Random Sequence Construction**: Randomly sample Pauli terms according to the absolute-value distribution of their coefficients and build a qDrift sequence of length `steps`.
4. **Quantum Circuit Construction**: Convert each sampled term into a Pauli-evolution gate via `pauli_string_evolution` and append them one by one to the circuit.
5. **Error Estimation and Output**: Compute the approximate evolution matrix, the exact evolution matrix, and the Frobenius-norm error, then save the circuit diagram and text report and return the unified result dictionary.

---

## Core Idea

The key idea of qDrift is not to apply Hamiltonian terms in a fixed deterministic order. Instead, it treats the Hamiltonian as a weighted collection of Pauli terms and samples terms randomly according to their weights. This replaces deterministic product formulas with a randomized one, often yielding a simpler circuit structure while still approximating the target evolution effectively.

---

## Mathematical Principles

Let the Hamiltonian be decomposed as
$$
H = \sum_j c_j P_j
$$
where $P_j$ are Pauli strings and $c_j$ are their coefficients. Define
$$
\lambda = \sum_j |c_j|
$$
Then qDrift samples the $j$-th term with probability
$$
p_j = \frac{|c_j|}{\lambda}
$$
and applies an evolution with angle
$$
a_j = \operatorname{sign}(c_j) \frac{\lambda t}{N}
$$
where $N$ is the total number of samples, namely `steps`. This produces the randomized product approximation
$$
U_{\text{approx}} \approx \prod_{k=1}^{N} e^{-i a_{j_k} P_{j_k}}
$$
The code also computes the exact matrix
$$
U_{\text{exact}} = e^{-iHt}
$$
and evaluates the error through the Frobenius norm
$$
\|U_{\text{approx}} - U_{\text{exact}}\|_F
$$
as its main accuracy indicator.

---

## Algorithm Steps

1. Normalize the input Hamiltonian into a Hermitian matrix compatible with a qubit-register dimension.
2. Decompose the Hamiltonian onto the Pauli basis and obtain all Pauli terms with coefficients.
3. Build a probability distribution from coefficient magnitudes and sample terms randomly.
4. Apply the corresponding Pauli-evolution gate for each sampled term to form the randomized circuit.
5. Compare the approximate result with the exact matrix exponential and report the error.

---

## Quantum Advantage

| Task | Fixed Product-Formula Methods | qDrift Advantage |
|------|-------------------------------|------------------|
| Hamiltonian simulation | Often requires repeatedly applying all terms in a fixed order | Focuses random effort on high-weight terms and offers a more flexible circuit construction |

---

## Complexity Analysis

The main cost of this implementation is determined by `steps`: the circuit appends one Pauli-evolution gate per sampled term, so the circuit length scales linearly with the sample count. In addition, both the Pauli decomposition and the exact matrix exponential $e^{-iHt}$ introduce classical overhead, meaning that matrix-level error estimation can itself become a dominant cost in higher-dimensional systems.

---

## Applications and Impact

- It is suitable for Hamiltonian-simulation tasks where the Hamiltonian is sparse or can be efficiently decomposed into the Pauli basis.
- It provides a randomized alternative to Trotter-style product-formula methods.
- It is practically useful in variational algorithms, quantum dynamics simulation, and circuit design under resource constraints.
