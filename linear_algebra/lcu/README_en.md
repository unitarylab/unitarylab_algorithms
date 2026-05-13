# Linear Combination of Unitaries (LCU) Explained

## Parameter Settings

- `alphas`: The list of non-negative coefficients in front of the unitary terms. Its length must match `paulis`.
- `paulis`: The list of Pauli operators participating in the linear combination, where each element is a `Pauli`.
- `n`: The number of system-register qubits, which specifies the size of the data register acted on by the unitaries.

> **Summary**: The LCU algorithm represents a non-unitary operator as a linear combination of unitary operators, then uses ancilla-state preparation, a controlled selection operator, and uncomputation to realize the corresponding branch. The final calculated result includes the success probability of measuring the all-zero ancilla state, the corresponding result-state component, the simulation time, and the generated circuit files.

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

1. **Parameter Parsing and Validation**: Check that `alphas` and `paulis` have the same length, then compute the number of LCU terms `m`, the system-register size `n`, and the normalization constant `s = \sum_j \alpha_j`.
2. **System-State and Coefficient-State Preparation**: If `initial_state` is provided, load it onto the system register first; then build the `V` operator to prepare an ancilla superposition whose amplitudes are proportional to the square roots of the coefficients.
3. **SELECT(U) Construction**: Conditionally apply the corresponding unitary `U_j` to the system register based on the ancilla control state.
4. **Uncomputation and Quantum Simulation**: Append `V^\dagger`, complete the standard LCU circuit, and execute the simulation.
5. **Post-processing and Output**: Extract the probability that all ancilla qubits are measured in the zero state, treat it as the LCU success probability, and output the associated result state together with the circuit and text files.

---

## Core Idea

The central idea of LCU is to embed a non-unitary operator
$$
M = \sum_j \alpha_j U_j
$$
into a larger unitary process. The algorithm first encodes the coefficients into an ancilla register, then uses a controlled-selection structure to call different unitaries on the system register, and finally uncomputes the ancilla preparation so that the target linear combination appears in the branch associated with a specific ancilla measurement outcome.

---

## Mathematical Principles

Let
$$
M = \sum_{j=0}^{m-1} \alpha_j U_j, \quad \alpha_j \ge 0
$$
and define the normalization constant
$$
s = \sum_{j=0}^{m-1} \alpha_j.
$$
LCU first prepares the ancilla state
$$
V|0\rangle = \sum_{j=0}^{m-1} \sqrt{\alpha_j / s}\, |j\rangle.
$$
It then builds the selection operator
$$
\mathrm{SELECT}(U) = \sum_{j=0}^{m-1} |j\rangle\langle j| \otimes U_j.
$$
Applying
$$
(V^\dagger \otimes I)\, \mathrm{SELECT}(U)\, (V \otimes I)
$$
to the joint ancilla-system state produces an effective system action proportional to $M/s$ when the ancilla register is projected onto the all-zero state. Therefore, the probability of the zero ancilla outcome quantifies the success rate of isolating the desired linear-combination branch. This implementation estimates that probability directly from the simulated final state.

---

## Algorithm Steps

1. Determine the ancilla-register size from the number of LCU terms and compute the coefficient sum `s`.
2. Use the `V` operator to prepare the coefficient superposition state on the ancilla register.
3. Build `SELECT(U)` so that different unitary operators are applied under different ancilla control states.
4. Apply `V^\dagger` to complete the standard LCU circuit structure and run the simulation.
5. Extract the all-zero ancilla probability and the corresponding system result state.

---

## Quantum Advantage

| Task | Direct Realization | LCU Advantage |
|------|--------------------|---------------|
| Embedding non-unitary operators into quantum circuits | Non-unitary maps cannot be executed directly as quantum gates | Uses ancilla registers and post-selection to convert a linear combination into an executable unitary extension |

---

## Complexity Analysis

The main resource costs of this implementation come from three parts: the ancilla-register size `n_anc = \lceil \log_2 m \rceil`, the cost of preparing the `V` state, and the controlled calls inside `SELECT(U)`. As the number of LCU terms `m` grows, the ancilla size increases only logarithmically, but the selection structure and total circuit depth still grow with the number of terms. As a result, LCU provides a uniform construction framework, while the practical efficiency depends on whether coefficient-state preparation and controlled-unitary application can both be implemented efficiently.

---

## Applications and Impact

- It is a core building block for Hamiltonian simulation, Taylor-series methods, and segmented linear-combination constructions.
- It is one of the foundational tools behind block encoding and quantum singular value transformation (QSVT).
- It is widely used to embed linear operators, matrix polynomials, and approximate inverses into quantum circuits.
